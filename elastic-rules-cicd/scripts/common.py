"""Shared helpers: load rules from disk, load the tenant registry, render per tenant."""

import json
import pathlib

import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
RULES_DIR = REPO_ROOT / "rules"
REGISTRY = REPO_ROOT / "customers.yml"

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


def load_rules():
    """Return [(path, rule_dict), ...] for every rule in rules/."""
    rules = []
    for path in sorted(RULES_DIR.glob("*.json")):
        with path.open() as fh:
            rules.append((path, json.load(fh)))
    return rules


def load_customers():
    with REGISTRY.open() as fh:
        return yaml.safe_load(fh)["customers"]


def render_for_customer(rules, customer):
    """Apply the customer's overlay and return the rules that tenant should get."""
    excluded = set(customer.get("exclude", []))
    rendered = []
    for _path, rule in rules:
        if rule["rule_id"] in excluded:
            continue
        copy = json.loads(json.dumps(rule))  # cheap deep copy
        if customer.get("index"):
            copy["index"] = customer["index"]
        rendered.append(copy)
    return rendered


def to_ndjson(rules):
    """Kibana's import endpoint wants newline-delimited JSON, one rule per line."""
    return "\n".join(json.dumps(r, separators=(",", ":")) for r in rules) + "\n"
