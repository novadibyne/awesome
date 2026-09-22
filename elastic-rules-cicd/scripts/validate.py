#!/usr/bin/env python3
"""Validate every rule and every tenant overlay. Runs on pull requests.

Needs no credentials and touches no Elastic stack, so it is safe to run in
any CI, on any branch, from a fork.
"""

import sys

from common import OWNERSHIP_TAG, REQUIRED_FIELDS, load_customers, load_rules, render_for_customer

VALID_SEVERITIES = {"low", "medium", "high", "critical"}


def main():
    errors = []
    rules = load_rules()

    if not rules:
        print("no rules found in rules/")
        return 1

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

        index = rule.get("index") or []
        if any(pattern.strip() in ("*", "*:*") for pattern in index):
            errors.append(f"{name}: index pattern '*' is too broad")

        if not isinstance(rule.get("version"), int):
            errors.append(f"{name}: version must be an int, and must be bumped on every change")

    # Every tenant overlay must still produce a usable rule set.
    for customer in load_customers():
        rendered = render_for_customer(rules, customer)
        if not rendered:
            errors.append(f"customer '{customer['id']}': overlay excludes every rule")
        for key in ("id", "ring", "kibana_url", "space", "api_key_env"):
            if key not in customer:
                errors.append(f"customer '{customer.get('id', '?')}': missing '{key}'")

    if errors:
        print(f"FAILED - {len(errors)} problem(s):\n")
        for err in errors:
            print(f"  - {err}")
        return 1

    print(f"OK - {len(rules)} rule(s) valid across {len(load_customers())} tenant(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
