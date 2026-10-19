"""Load rules, expand the registry into (deployment, space) targets, render."""

import json
import pathlib

import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
RULES_DIR = REPO_ROOT / "rules"
REGISTRY = REPO_ROOT / "deployments.yml"

# Fields every rule must carry before we are willing to ship it anywhere.
REQUIRED_FIELDS = [
    "rule_id",
    "name",
    "description",
    "type",
    "query",
    "language",
    "index",
    "severity",
    "risk_score",
    "interval",
    "from",
    "version",
    "tags",
]

OWNERSHIP_TAG = "managed-by:soc-cicd"

# Overlay keys and how a lower level combines with the one above it.
OVERLAY_REPLACE = ("index", "include_tags", "enabled")
OVERLAY_UNION = ("exclude",)


def load_rules():
    """Return [(path, rule_dict), ...] for every rule in rules/."""
    rules = []
    for path in sorted(RULES_DIR.glob("*.json")):
        with path.open() as fh:
            rules.append((path, json.load(fh)))
    return rules


def _merge_overlay(base, incoming):
    merged = dict(base)
    for key in OVERLAY_REPLACE:
        if key in incoming:
            merged[key] = incoming[key]
    for key in OVERLAY_UNION:
        if key in incoming:
            merged[key] = sorted(set(merged.get(key, [])) | set(incoming[key]))
    return merged


def load_targets():
    """Expand the registry into one flat target per (deployment, space) pair.

    Each target carries its fully merged overlay, so callers never have to
    think about the three levels again.
    """
    with REGISTRY.open() as fh:
        registry = yaml.safe_load(fh)

    defaults = registry.get("defaults") or {}
    targets = []

    for deployment in registry.get("deployments") or []:
        deployment_overlay = _merge_overlay(defaults, deployment)

        for space in deployment.get("spaces") or []:
            overlay = _merge_overlay(deployment_overlay, space)
            targets.append(
                {
                    "deployment_id": deployment["id"],
                    "space_id": space["id"],
                    "id": f"{deployment['id']}/{space['id']}",
                    "ring": deployment["ring"],
                    "kibana_url": deployment["kibana_url"],
                    "api_key_env": deployment.get("api_key_env"),
                    "key_vault_secret": deployment.get("key_vault_secret"),
                    "overlay": {
                        "index": overlay.get("index"),
                        "exclude": overlay.get("exclude", []),
                        "include_tags": overlay.get("include_tags"),
                        "enabled": overlay.get("enabled"),
                    },
                }
            )

    return targets


def render_for_target(rules, target):
    """Apply the target's merged overlay and return the rules it should get."""
    overlay = target["overlay"]
    excluded = set(overlay.get("exclude") or [])
    include_tags = set(overlay.get("include_tags") or [])

    rendered = []
    for _path, rule in rules:
        if rule["rule_id"] in excluded:
            continue
        if include_tags and not include_tags & set(rule.get("tags", [])):
            continue

        copy = json.loads(json.dumps(rule))  # cheap deep copy
        if overlay.get("index"):
            copy["index"] = overlay["index"]
        if overlay.get("enabled") is not None:
            copy["enabled"] = overlay["enabled"]
        rendered.append(copy)

    return rendered


def to_ndjson(rules):
    """Kibana's import endpoint wants newline-delimited JSON, one rule per line."""
    return "\n".join(json.dumps(r, separators=(",", ":")) for r in rules) + "\n"


def import_url(target):
    """Space-aware import endpoint. The default space has no /s/ prefix."""
    base = target["kibana_url"].rstrip("/")
    space = target["space_id"]
    prefix = "" if space == "default" else f"/s/{space}"
    return f"{base}{prefix}/api/detection_engine/rules/_import"


def filter_targets(targets, ring=None, deployment=None, space=None):
    if ring is not None:
        targets = [t for t in targets if t["ring"] == ring]
    if deployment:
        targets = [t for t in targets if t["deployment_id"] == deployment]
    if space:
        targets = [t for t in targets if t["space_id"] == space]
    return targets
