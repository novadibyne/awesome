#!/usr/bin/env python3
"""Push rules to tenant Kibanas via the detection-engine import API.

  python scripts/deploy.py --ring 0
  python scripts/deploy.py --customer acme
  python scripts/deploy.py --ring 2 --dry-run
  python scripts/deploy.py --ring 2 --key-source keyvault --key-vault-url https://kv.vault.azure.net/

Two ways to get each tenant's Kibana API key:

  env       (default) read the env var named by that tenant's api_key_env.
            Simple, but in Azure DevOps every secret has to be mapped into
            the step's env: block by hand, one line per tenant.

  keyvault  read the secret named by that tenant's key_vault_secret straight
            out of Azure Key Vault. No per-tenant YAML. Authenticates with
            DefaultAzureCredential, which picks up the az login session that
            the AzureCLI@2 task establishes from the service connection.
            Needs: pip install -r requirements-azure.txt
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


def key_from_env(customer):
    var = customer["api_key_env"]
    key = os.environ.get(var)
    if not key:
        raise RuntimeError(f"env var {var} is not set")
    return key


def key_from_keyvault(customer, client):
    name = customer.get("key_vault_secret")
    if not name:
        raise RuntimeError("no key_vault_secret set for this tenant in customers.yml")
    return client.get_secret(name).value


def make_keyvault_client(vault_url):
    # Imported lazily so the default env path needs no Azure dependencies.
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient

    return SecretClient(vault_url=vault_url, credential=DefaultAzureCredential())


def import_url(customer):
    base = customer["kibana_url"].rstrip("/")
    space = customer.get("space", "default")
    prefix = "" if space == "default" else f"/s/{space}"
    return f"{base}{prefix}/api/detection_engine/rules/_import"


def deploy(customer, rules, dry_run, kv_client=None):
    rendered = render_for_customer(rules, customer)
    ndjson = to_ndjson(rendered)
    label = f"{customer['id']} (ring {customer['ring']})"

    if dry_run:
        print(f"  DRY RUN {label}: would import {len(rendered)} rule(s) to {import_url(customer)}")
        return True

    try:
        api_key = key_from_keyvault(customer, kv_client) if kv_client else key_from_env(customer)
    except Exception as exc:  # noqa: BLE001 - any credential failure is a tenant failure
        print(f"  FAIL    {label}: could not read API key: {exc}")
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
    parser.add_argument(
        "--key-source",
        choices=["env", "keyvault"],
        default="env",
        help="where to read tenant API keys from (default: env)",
    )
    parser.add_argument("--key-vault-url", help="https://<vault>.vault.azure.net/, required for --key-source keyvault")
    args = parser.parse_args()

    if args.key_source == "keyvault" and not args.dry_run and not args.key_vault_url:
        parser.error("--key-vault-url is required when --key-source is keyvault")

    rules = load_rules()
    targets = load_customers()
    if args.ring is not None:
        targets = [c for c in targets if c["ring"] == args.ring]
    if args.customer:
        targets = [c for c in targets if c["id"] == args.customer]

    if not targets:
        print("no tenants matched the given filters")
        return 1

    kv_client = None
    if args.key_source == "keyvault" and not args.dry_run:
        kv_client = make_keyvault_client(args.key_vault_url)

    print(f"Deploying {len(rules)} rule(s) to {len(targets)} tenant(s)")
    results = [deploy(c, rules, args.dry_run, kv_client) for c in targets]

    failed = results.count(False)
    print(f"\n{results.count(True)} succeeded, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
