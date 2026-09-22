# Elastic Detection Rules - starter CI/CD

The smallest thing that actually works: rules in Git, validated on every PR,
pushed to each customer's Kibana on merge.

Copy the **contents** of this folder into the root of a new Bitbucket repo
(`bitbucket-pipelines.yml` has to sit at the repo root to be picked up).

```
bitbucket-pipelines.yml   CI/CD definition
customers.yml             tenant registry + per-tenant overlay
rules/*.json              one detection rule per file
scripts/validate.py       PR checks, no credentials needed
scripts/deploy.py         pushes rules to a tenant's Kibana
```

## How it works

Rules are stored one-per-file in Kibana's own rule JSON format. At deploy time
each rule is merged with the target customer's overlay from `customers.yml`
(index pattern override, rule exclusions), concatenated into NDJSON, and POSTed
to that tenant's `/api/detection_engine/rules/_import`.

Deploys go out in rings: ring 0 is your internal canary and runs automatically,
rings 1 and 2 are manual-trigger steps so a human decides when customers get it.

Two import flags matter and are set in `scripts/deploy.py`:
`overwrite_exceptions=false` and `overwrite_action_connectors=false`. They stop a
deploy from wiping exception lists and alert connectors that customers own.

## Setup

1. **Create an API key per tenant.** In each customer's Kibana: Stack Management
   -> API keys. Restrict the key to a role with `securitySolution: all` in that
   tenant's space and nothing else.

2. **Store the keys.** Repository settings -> Deployments. Create environments
   `ring-0`, `ring-1`, `ring-2`. Add each tenant's key as a **Secured** variable
   under its ring, using the exact name from that tenant's `api_key_env`.

3. **Register the tenants.** Edit `customers.yml` - one block per customer
   environment. `kibana_url`, `space`, `ring`, `api_key_env` are required.

4. **Protect `main`.** Branch restrictions -> require a PR and at least one
   approval before merge. The pipeline is only as good as the review in front
   of it.

## Daily use

Add or change a rule in `rules/`, **bump its `version` integer**, open a PR.
Kibana silently ignores an import whose `version` did not increase - this is the
single most common reason a deploy looks green but nothing changed.

Run it locally before pushing:

```bash
pip install -r requirements.txt
python scripts/validate.py
python scripts/deploy.py --dry-run
python scripts/deploy.py --customer acme     # needs KIBANA_APIKEY_ACME set
```

## What validate.py enforces

Required fields present, `rule_id` unique across the repo, valid severity,
`risk_score` 0-100, integer `version`, the `managed-by:soc-cicd` ownership tag
on every rule, no `index: "*"`, and that every tenant overlay still renders a
non-empty rule set.

## Deliberately not here yet

Query syntax validation against a live stack, the rule preview call for alert
volume, drift detection, automatic version bumping, deleting rules removed from
the repo, and Azure DevOps. Add them once this loop is running.
