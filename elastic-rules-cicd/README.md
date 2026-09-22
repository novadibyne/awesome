# Elastic Detection Rules - CI/CD on Azure DevOps

Rules in Azure Repos, validated on every PR, pushed to every customer's Kibana
in rings on merge to `main`.

Copy the **contents** of this folder into the root of your Azure Repos repo -
`azure-pipelines.yml` is easiest to find there.

```
azure-pipelines.yml        stages: validate -> ring 0 -> ring 1 -> ring 2
pipelines/deploy-ring.yml  reusable deployment job for one ring
customers.yml              tenant registry + per-tenant overlay
rules/*.json               one detection rule per file
scripts/validate.py        PR checks, no credentials needed
scripts/deploy.py          pushes rules to a tenant's Kibana
requirements.txt           base deps
requirements-azure.txt     adds Key Vault deps
```

## How it works

Rules are stored one-per-file in Kibana's own rule JSON format. At deploy time
each rule is merged with the target customer's overlay from `customers.yml`
(index pattern override, rule exclusions), concatenated into NDJSON, and POSTed
to that tenant's `/api/detection_engine/rules/_import`.

Deploys go out in rings. Ring 0 is your internal canary and runs automatically
on merge. Rings 1 and 2 are gated by approvals on their ADO Environment, so a
human decides when customers get the change.

Two import flags matter and are set in `scripts/deploy.py`:
`overwrite_exceptions=false` and `overwrite_action_connectors=false`. They stop
a deploy from wiping exception lists and alert connectors that customers own.

## Azure DevOps setup

### 1. Create an API key per tenant

In each customer's Kibana: Stack Management -> API keys. Restrict the key to a
role with `securitySolution: all` in that tenant's space and nothing else.

### 2. Put the keys in Key Vault

Create one vault (e.g. `kv-soc-rules`) and add one secret per tenant, named to
match `key_vault_secret` in `customers.yml`:

```bash
az keyvault secret set --vault-name kv-soc-rules \
  --name kibana-apikey-acme --value '<the api key>'
```

Key Vault secret names allow only letters, digits and dashes. No underscores.

### 3. Create the service connection

Project settings -> Service connections -> New -> Azure Resource Manager ->
**Workload Identity federation (automatic)**. Name it `elastic-rules-kv` and
match `azureSubscription` in `azure-pipelines.yml`.

Then grant its identity read access on the vault:

```bash
az role assignment create \
  --role "Key Vault Secrets User" \
  --assignee <service-connection-app-id> \
  --scope /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.KeyVault/vaults/kv-soc-rules
```

(If the vault still uses access policies rather than RBAC, grant `get` and
`list` on secrets instead.)

### 4. Create the Environments

Pipelines -> Environments -> New environment, three of them:

| Environment | Approvals |
|---|---|
| `elastic-rules-ring-0` | none - auto-deploys the canary |
| `elastic-rules-ring-1` | Approvals check, detection engineering lead |
| `elastic-rules-ring-2` | Approvals check, lead + service delivery |

Add the check under the environment's **Approvals and checks** tab. This is the
gate - nothing in the YAML enforces it.

### 5. Create the pipeline

Pipelines -> New pipeline -> Azure Repos Git -> your repo -> Existing Azure
Pipelines YAML file -> `/azure-pipelines.yml`. Save, don't run yet.

### 6. Set the variables

Edit `azure-pipelines.yml` and set `azureSubscription` and `keyVaultUrl` to your
real values. Edit `customers.yml` for your real tenants.

### 7. Protect `main`

Repos -> Branches -> `main` -> Branch policies:

- Require a minimum number of reviewers (at least 1)
- Check for linked work items, if you track that way
- **Build validation**: add this pipeline so the Validate stage runs on every PR

The pipeline is only as good as the review in front of it.

### 8. First run

Merge a trivial rule change. Watch ring 0 deploy, confirm the rules landed in
your internal Kibana, then approve ring 1.

## Daily use

Add or change a rule in `rules/`, **bump its `version` integer**, open a PR.
Kibana silently ignores an import whose `version` did not increase - this is the
single most common reason a deploy looks green but nothing changed.

Run it locally before pushing:

```bash
pip install -r requirements.txt
python scripts/validate.py
python scripts/deploy.py --dry-run
python scripts/deploy.py --customer acme        # needs KIBANA_APIKEY_ACME set
```

Against Key Vault locally, after `az login`:

```bash
pip install -r requirements-azure.txt
python scripts/deploy.py --ring 1 \
  --key-source keyvault --key-vault-url https://kv-soc-rules.vault.azure.net/
```

## Why Key Vault instead of a variable group

Azure DevOps does not expose secret variables to scripts automatically - each
one has to be mapped into the step's `env:` block by name. That is one line of
YAML per tenant, edited every time you onboard a customer.

`--key-source keyvault` skips that: `deploy.py` looks up each tenant's secret by
the name in `customers.yml`, authenticating with the session the `AzureCLI@2`
task already established. Onboarding a customer becomes one Key Vault secret
plus one block in `customers.yml`, with no pipeline edit.

The variable-group path is still wired up in `pipelines/deploy-ring.yml` if you
want it - set `keySource: 'env'` and create a group called `elastic-rules-keys`
linked to the vault.

## Gotchas worth knowing

- **Deployment jobs do not check out your repo by default.** The template has an
  explicit `- checkout: self` for exactly this reason. Remove it and you get a
  confusing "no such file" on `scripts/deploy.py`.
- **`condition:` on ring 0** keeps deploys off PR builds. PR validation runs the
  Validate stage only.
- **Elastic Cloud IP allowlists.** If tenant Kibanas restrict inbound IPs,
  Microsoft-hosted agents will not reach them. Move to a self-hosted agent pool
  in a VNet with a stable egress IP.

## What validate.py enforces

Required fields present, `rule_id` unique across the repo, valid severity,
`risk_score` 0-100, integer `version`, the `managed-by:soc-cicd` ownership tag
on every rule, no `index: "*"`, and that every tenant overlay still renders a
non-empty rule set.

## Deliberately not here yet

Query syntax validation against a live stack, the rule preview call for alert
volume, drift detection, automatic version bumping, publishing an immutable rule
pack as a pipeline artifact, and deleting rules removed from the repo. Add them
once this loop is running against one real tenant.
