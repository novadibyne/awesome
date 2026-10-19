#!/usr/bin/env python3
"""Validate every rule and every replication target. Runs on pull requests.

Needs no credentials and touches no Elastic stack, so it is safe to run in
any CI, on any branch.
"""

import sys

from common import OWNERSHIP_TAG, REQUIRED_FIELDS, load_rules, load_targets, render_for_target

VALID_SEVERITIES = {"low", "medium", "high", "critical"}


def validate_rules(rules):
    errors = []
    seen_ids = {}

    for path, rule in rules:
        name = path.name

        for field in REQUIRED_FIELDS:
            if field not in rule:
                errors.append(f"{name}: missing required field '{field}'")

        rule_id = rule.get("rule_id")
        if rule_id in seen_ids:
            errors.append(f"{name}: duplicate rule_id, already used by {seen_ids[rule_id]}")
        elif rule_id:
            seen_ids[rule_id] = name

        if rule.get("severity") not in VALID_SEVERITIES:
            errors.append(f"{name}: severity must be one of {sorted(VALID_SEVERITIES)}")

        score = rule.get("risk_score")
        if not isinstance(score, int) or not 0 <= score <= 100:
            errors.append(f"{name}: risk_score must be an int between 0 and 100")

        if OWNERSHIP_TAG not in rule.get("tags", []):
            errors.append(f"{name}: must carry the '{OWNERSHIP_TAG}' tag so drift cleanup can find it")

        if any(p.strip() in ("*", "*:*") for p in rule.get("index") or []):
            errors.append(f"{name}: index pattern '*' is too broad")

        if not isinstance(rule.get("version"), int):
            errors.append(f"{name}: version must be an int, and must be bumped on every change")

    return errors


def validate_targets(rules, targets):
    errors = []
    seen = set()

    if not targets:
        errors.append("deployments.yml expands to no targets")

    for target in targets:
        label = target["id"]

        if label in seen:
            errors.append(f"target '{label}': duplicate deployment/space pair")
        seen.add(label)

        if not target["kibana_url"].startswith("https://"):
            errors.append(f"target '{label}': kibana_url must be https")
        if not target.get("api_key_env") and not target.get("key_vault_secret"):
            errors.append(f"target '{label}': needs api_key_env or key_vault_secret on its deployment")
        if target.get("key_vault_secret") and "_" in target["key_vault_secret"]:
            errors.append(
                f"target '{label}': Key Vault secret names cannot contain underscores "
                f"('{target['key_vault_secret']}')"
            )
        if target["ring"] not in (0, 1, 2):
            errors.append(f"target '{label}': ring must be 0, 1 or 2")

        # A target that renders nothing is almost always a mistake in the
        # overlay, not an intentional empty space.
        if not render_for_target(rules, target):
            errors.append(f"target '{label}': overlay leaves zero rules - check exclude/include_tags")

    return errors


def main():
    rules = load_rules()
    if not rules:
        print("no rules found in rules/")
        return 1

    targets = load_targets()
    errors = validate_rules(rules) + validate_targets(rules, targets)

    if errors:
        print(f"FAILED - {len(errors)} problem(s):\n")
        for err in errors:
            print(f"  - {err}")
        return 1

    deployments = {t["deployment_id"] for t in targets}
    print(
        f"OK - {len(rules)} rule(s) valid across {len(targets)} target(s) "
        f"in {len(deployments)} deployment(s)"
    )
    for target in targets:
        count = len(render_for_target(rules, target))
        print(f"     ring {target['ring']}  {target['id']:32} {count} rule(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
