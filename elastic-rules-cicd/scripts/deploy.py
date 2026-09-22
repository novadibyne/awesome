#!/usr/bin/env python3
"""Push rules to tenant Kibanas via the detection-engine import API.

  python scripts/deploy.py --ring 0
  python scripts/deploy.py --customer acme
  python scripts/deploy.py --ring 2 --dry-run

Each tenant's API key is read from the env var named in customers.yml.
Keys live in the CI secret store, never in the repo.
"""

import argparse
import os
import sys

import requests

from common import load_customers, load_rules, render_for_customer, to_ndjson

TIMEOUT = 60

# overwrite=true          -> update rules we already manage
# overwrite_exceptions    -> false: never clobber a customer's own exception lists
# overwrite_action_...    -> false: never clobber a customer's own connectors
IMPORT_PARAMS = {
    "overwrite": "true",
    "overwrite_exceptions": "false",
    "overwrite_action_connectors": "false",
}


def import_url(customer):
    base = customer["kibana_url"].rstrip("/")
    space = customer.get("space", "default")
    prefix = "" if space == "default" else f"/s/{space}"
    return f"{base}{prefix}/api/detection_engine/rules/_import"


def deploy(customer, rules, dry_run):
    rendered = render_for_customer(rules, customer)
    ndjson = to_ndjson(rendered)
    label = f"{customer['id']} (ring {customer['ring']})"

    if dry_run:
        print(f"  DRY RUN {label}: would import {len(rendered)} rule(s) to {import_url(customer)}")
        return True

    api_key = os.environ.get(customer["api_key_env"])
    if not api_key:
        print(f"  FAIL    {label}: env var {customer['api_key_env']} is not set")
        return False

    response = requests.post(
        import_url(customer),
        params=IMPORT_PARAMS,
        headers={"kbn-xsrf": "true", "Authorization": f"ApiKey {api_key}"},
        files={"file": ("rules.ndjson", ndjson, "application/octet-stream")},
        timeout=TIMEOUT,
    )

    if response.status_code >= 400:
        print(f"  FAIL    {label}: HTTP {response.status_code} {response.text[:300]}")
        return False

    body = response.json()
    imported = body.get("success_count", 0)
    rule_errors = body.get("errors", [])

    if rule_errors:
        print(f"  FAIL    {label}: {imported} imported, {len(rule_errors)} rejected")
        for err in rule_errors[:5]:
            print(f"            {err.get('rule_id', '?')}: {err.get('error', {}).get('message', err)}")
        return False

    print(f"  OK      {label}: {imported} rule(s) imported")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ring", type=int, help="only deploy to tenants in this ring")
    parser.add_argument("--customer", help="only deploy to this tenant id")
    parser.add_argument("--dry-run", action="store_true", help="render and report, send nothing")
    args = parser.parse_args()

    rules = load_rules()
    targets = load_customers()
    if args.ring is not None:
        targets = [c for c in targets if c["ring"] == args.ring]
    if args.customer:
        targets = [c for c in targets if c["id"] == args.customer]

    if not targets:
        print("no tenants matched the given filters")
        return 1

    print(f"Deploying {len(rules)} rule(s) to {len(targets)} tenant(s)")
    results = [deploy(c, rules, args.dry_run) for c in targets]

    failed = results.count(False)
    print(f"\n{results.count(True)} succeeded, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
