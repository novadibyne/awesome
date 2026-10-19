#!/usr/bin/env python3
"""Replicate rules to every Elastic deployment and space in the selected ring.

  python scripts/deploy.py --ring 0
  python scripts/deploy.py --deployment acme-prod
  python scripts/deploy.py --deployment acme-prod --space acme-pci
  python scripts/deploy.py --ring 2 --dry-run
  python scripts/deploy.py --ring 2 --key-source keyvault --key-vault-url https://kv.vault.azure.net/

Targets are (deployment, space) pairs expanded from deployments.yml. They are
deployed concurrently; one API key per deployment is fetched once and reused
across that deployment's spaces.

Two ways to get a deployment's Kibana API key:

  env       (default) read the env var named by that deployment's api_key_env.
            Simple, but in Azure DevOps every secret has to be mapped into
            the step's env: block by hand, one line per deployment.

  keyvault  read the secret named by key_vault_secret straight out of Azure
            Key Vault. No per-deployment YAML. Authenticates with
            DefaultAzureCredential, which picks up the az login session the
            AzureCLI@2 task establishes from the service connection.
            Needs: pip install -r requirements-azure.txt
"""

import argparse
import os
import sys
import threading
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

import requests

from common import filter_targets, import_url, load_rules, load_targets, render_for_target, to_ndjson

TIMEOUT = 60

# overwrite=true          -> update rules we already manage
# overwrite_exceptions    -> false: never clobber a tenant's own exception lists
# overwrite_action_...    -> false: never clobber a tenant's own connectors
IMPORT_PARAMS = {
    "overwrite": "true",
    "overwrite_exceptions": "false",
    "overwrite_action_connectors": "false",
}


class KeyCache:
    """One API key per deployment, fetched once, shared across its spaces."""

    def __init__(self, source, vault_url=None):
        self.source = source
        self.vault_url = vault_url
        self._keys = {}
        self._lock = threading.Lock()
        self._kv_client = None

    def _keyvault_client(self):
        if self._kv_client is None:
            # Imported lazily so the env path needs no Azure dependencies.
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient

            self._kv_client = SecretClient(
                vault_url=self.vault_url, credential=DefaultAzureCredential()
            )
        return self._kv_client

    def get(self, target):
        deployment = target["deployment_id"]
        with self._lock:
            if deployment in self._keys:
                return self._keys[deployment]

            if self.source == "keyvault":
                name = target.get("key_vault_secret")
                if not name:
                    raise RuntimeError(f"no key_vault_secret set for deployment '{deployment}'")
                key = self._keyvault_client().get_secret(name).value
            else:
                var = target.get("api_key_env")
                if not var:
                    raise RuntimeError(f"no api_key_env set for deployment '{deployment}'")
                key = os.environ.get(var)
                if not key:
                    raise RuntimeError(f"env var {var} is not set")

            self._keys[deployment] = key
            return key


def deploy_one(target, rules, dry_run, keys):
    """Returns (target_id, ok, message)."""
    rendered = render_for_target(rules, target)
    url = import_url(target)

    if not rendered:
        return target["id"], True, "0 rules after overlay, nothing to send"

    if dry_run:
        return target["id"], True, f"DRY RUN would import {len(rendered)} rule(s) to {url}"

    try:
        api_key = keys.get(target)
    except Exception as exc:  # noqa: BLE001 - any credential failure fails this target
        return target["id"], False, f"could not read API key: {exc}"

    try:
        response = requests.post(
            url,
            params=IMPORT_PARAMS,
            headers={"kbn-xsrf": "true", "Authorization": f"ApiKey {api_key}"},
            files={"file": ("rules.ndjson", to_ndjson(rendered), "application/octet-stream")},
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        return target["id"], False, f"request failed: {exc}"

    if response.status_code >= 400:
        return target["id"], False, f"HTTP {response.status_code} {response.text[:300]}"

    body = response.json()
    imported = body.get("success_count", 0)
    rule_errors = body.get("errors", [])

    if rule_errors:
        detail = "; ".join(
            f"{e.get('rule_id', '?')}: {e.get('error', {}).get('message', e)}" for e in rule_errors[:5]
        )
        return target["id"], False, f"{imported} imported, {len(rule_errors)} rejected - {detail}"

    return target["id"], True, f"{imported} rule(s) imported"


def write_junit(path, results):
    """So Azure DevOps shows one row per deployment/space instead of raw log."""
    suite = ET.Element(
        "testsuite",
        name="elastic-rule-replication",
        tests=str(len(results)),
        failures=str(sum(1 for _, ok, _ in results if not ok)),
    )
    for target_id, ok, message in results:
        deployment, space = target_id.split("/", 1)
        case = ET.SubElement(suite, "testcase", classname=deployment, name=space)
        if ok:
            ET.SubElement(case, "system-out").text = message
        else:
            ET.SubElement(case, "failure", message=message).text = message
    tree = ET.ElementTree(ET.Element("testsuites"))
    tree.getroot().append(suite)
    tree.write(path, encoding="utf-8", xml_declaration=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ring", type=int, help="only deploy to targets in this ring")
    parser.add_argument("--deployment", help="only deploy to this deployment id")
    parser.add_argument("--space", help="only deploy to this space id")
    parser.add_argument("--dry-run", action="store_true", help="render and report, send nothing")
    parser.add_argument(
        "--key-source",
        choices=["env", "keyvault"],
        default="env",
        help="where to read deployment API keys from (default: env)",
    )
    parser.add_argument("--key-vault-url", help="https://<vault>.vault.azure.net/, for --key-source keyvault")
    parser.add_argument("--max-parallel", type=int, default=8, help="concurrent targets (default 8)")
    parser.add_argument("--junit-out", help="write a JUnit XML result file for CI reporting")
    parser.add_argument(
        "--fail-threshold",
        type=float,
        default=0.0,
        help="tolerate this fraction of failed targets, 0.0 = fail on any (default)",
    )
    args = parser.parse_args()

    if args.key_source == "keyvault" and not args.dry_run and not args.key_vault_url:
        parser.error("--key-vault-url is required when --key-source is keyvault")

    rules = load_rules()
    targets = filter_targets(load_targets(), args.ring, args.deployment, args.space)

    if not targets:
        print("no targets matched the given filters")
        return 1

    deployments = sorted({t["deployment_id"] for t in targets})
    print(
        f"Replicating {len(rules)} rule(s) to {len(targets)} target(s) "
        f"across {len(deployments)} deployment(s), {args.max_parallel} at a time"
    )

    keys = KeyCache(args.key_source, args.key_vault_url)
    with ThreadPoolExecutor(max_workers=args.max_parallel) as pool:
        results = list(pool.map(lambda t: deploy_one(t, rules, args.dry_run, keys), targets))

    results.sort(key=lambda r: r[0])
    for target_id, ok, message in results:
        print(f"  {'OK  ' if ok else 'FAIL'}  {target_id:32} {message}")

    if args.junit_out:
        write_junit(args.junit_out, results)
        print(f"\nwrote {args.junit_out}")

    failed = sum(1 for _, ok, _ in results if not ok)
    rate = failed / len(results)
    print(f"\n{len(results) - failed} succeeded, {failed} failed ({rate:.0%})")

    if failed and rate > args.fail_threshold:
        print(f"failure rate {rate:.0%} exceeds threshold {args.fail_threshold:.0%}")
        return 1
    if failed:
        print(f"failure rate {rate:.0%} within threshold {args.fail_threshold:.0%}, not failing the stage")
    return 0


if __name__ == "__main__":
    sys.exit(main())
