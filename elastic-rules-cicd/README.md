# Elastic Detection Rules - CI/CD on Azure DevOps

Rules in Azure Repos, validated on every PR, replicated to every Elastic
deployment and Kibana space in rings on merge to `main`.

Copy the **contents** of this folder into the root of your Azure Repos repo -
`azure-pipelines.yml` is easiest to find there.

```
azure-pipelines.yml               stages: validate -> ring 0 -> ring 1 -> ring 2
pipelines/deploy-ring.yml         deployment job for one ring (default)
pipelines/deploy-ring-matrix.yml  optional: one parallel job per deployment
deployments.yml                   deployments, their spaces, and overlays
rules/*.json                      one detection rule per file
scripts/validate.py               PR checks, no credentials needed
scripts/common.py                 target expansion and overlay merge
scripts/deploy.py                 concurrent replication to every target
scripts/plan_matrix.py            emits the ADO matrix (matrix variant only)
requirements.txt                  base deps
requirements-azure.txt            adds Key Vault deps
```

## How it works

A **target** is one `(deployment, space)` pair. `deployments.yml` lists every
Elastic deployment and the Kibana spaces inside it that should receive rules,
so a single deployment with four spaces is four targets.

Rules are stored one-per-file in Kibana's own rule JSON format. At deploy time
each rule is merged with that target's overlay, concatenated into NDJSON, and
POSTed to the space-aware import endpoint - `/s/<space>/api/...` for every
space except `default`, which has no prefix.

Overlays merge top-down, later winning:

```
defaults  ->  deployment  ->  space
```

| Overlay key | Effect | Merge |
|---|---|---|
| `index` | replace the index patterns on every rule | replace |
| `exclude` | rule_ids this target must not receive | union |
| `include_tags` | only rules carrying at least one of these tags | replace |
| `enabled` | force rules enabled/disabled at this target | replace |

That covers the common cases: a PCI space that only gets Windows rules on a
narrow index, a customer that opts out of one rule across all their spaces, a
new deployment that lands everything disabled for a staged rollout.

Replication to all targets in a ring happens concurrently inside `deploy.py`
(`--max-parallel`, default 8), with one API key fetched per deployment and
reused across its spaces. Ring 0 is your internal canary and runs
automatically on merge. Rings 1 and 2 are gated by approvals on their ADO
Environment, so a human decides when customers get the change.

Two import flags matter and are set in `scripts/deploy.py`:
`overwrite_exceptions=false` and `overwrite_action_connectors=false`. They stop
a deploy from wiping exception lists and alert connectors that customers own.

## Azure DevOps setup

### 1. Create an API key per deployment

One key per **deployment**, not per space. In that deployment's Kibana:
Stack Management -> API keys. Restrict the key to a role granting
`securitySolution: all`, with the role's Kibana privileges scoped to exactly
the spaces that deployment's entry lists - and nothing else.

A key whose role does not cover a space will fail only on that space's target,
which is why the per-target result rows matter.

### 2. Put the keys in Key Vault

Create one vault (e.g. `kv-soc-rules`) and add one secret per deployment, named
to match `key_vault_secret` in `deployments.yml`:

```bash
az keyvault secret set --vault-name kv-soc-rules \
  --name kibana-apikey-acme-prod --value '<the api key>'
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
real values. Edit `deployments.yml` for your real deployments and spaces.

### 7. Protect `main`

Repos -> Branches -> `main` -> Branch policies:

- Require a minimum number of reviewers (at least 1)
- Check for linked work items, if you track that way
- **Build validation**: add this pipeline so the Validate stage runs on every PR

The pipeline is only as good as the review in front of it.

### 8. First run

Merge a trivial rule change. Watch ring 0 deploy, confirm the rules landed in
your internal Kibana, then approve ring 1. The stage's **Tests** tab shows one
row per deployment/space.

## Daily use

Add or change a rule in `rules/`, **bump its `version` integer**, open a PR.
Kibana silently ignores an import whose `version` did not increase - this is the
single most common reason a deploy looks green but nothing changed.

Run it locally before pushing:

```bash
pip install -r requirements.txt
python scripts/validate.py
python scripts/deploy.py --dry-run
python scripts/deploy.py --deployment acme-prod            # all its spaces
python scripts/deploy.py --deployment acme-prod --space acme-pci
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
YAML per deployment, edited every time you onboard a customer.

`--key-source keyvault` skips that: `deploy.py` looks up each deployment's
secret by the name in `deployments.yml`, authenticating with the session the
`AzureCLI@2` task already established. Onboarding a deployment becomes one Key
Vault secret plus one block in `deployments.yml`, with no pipeline edit.

The variable-group path is still wired up in `pipelines/deploy-ring.yml` if you
want it - set `keySource: 'env'` and create a group called `elastic-rules-keys`
linked to the vault.

## Per-deployment pipeline jobs

`deploy-ring.yml` runs one job per ring and fans out inside Python, which keeps
the approval gate and the ring's whole result in one place. Per-target rows
still appear in the **Tests** tab from the published JUnit file.

If you would rather see one parallel ADO job per deployment, swap the template
reference in `azure-pipelines.yml` to `pipelines/deploy-ring-matrix.yml`. ADO
matrix only works on plain jobs, not deployment jobs, so that variant adds a
tiny gate job in front to keep the Environment approval - three jobs per ring
instead of one. Worth it once you have enough deployments that per-leg
attribution beats reading the Tests tab.

## Failure budget

`failThreshold` is the fraction of targets allowed to fail without failing the
stage. Keep it at `0.0` for rings 0 and 1. Ring 2 ships with `0.05` so a single
unreachable tenant does not block the rest of the fleet - the stage still shows
the failed rows, and you chase them separately.

## Gotchas worth knowing

- **Deployment jobs do not check out your repo by default.** The template has an
  explicit `- checkout: self` for exactly this reason. Remove it and you get a
  confusing "no such file" on `scripts/deploy.py`.
- **`condition:` on ring 0** keeps deploys off PR builds. PR validation runs the
  Validate stage only.
- **Elastic Cloud IP allowlists.** If tenant Kibanas restrict inbound IPs,
  Microsoft-hosted agents will not reach them. Move to a self-hosted agent pool
  in a VNet with a stable egress IP.
- **The `default` space takes no `/s/` prefix.** `scripts/common.py` handles it;
  hardcoding `/s/default/` returns 404.
- **One API key, many spaces.** The key's role has to grant `securitySolution`
  in every space you list for that deployment, or individual space targets fail
  while others pass.

## What validate.py enforces

Required fields present, `rule_id` unique across the repo, valid severity,
`risk_score` 0-100, integer `version`, the `managed-by:soc-cicd` ownership tag
on every rule, and no `index: "*"`.

Per target: no duplicate deployment/space pair, `https` Kibana URL, a key
source present, no underscore in a Key Vault secret name, a valid ring, and
that the merged overlay still renders a non-empty rule set - an empty render is
nearly always an `exclude`/`include_tags` mistake rather than an intentionally
empty space.

## Deliberately not here yet

Query syntax validation against a live stack, the rule preview call for alert
volume, drift detection, automatic version bumping, publishing an immutable rule
pack as a pipeline artifact, and deleting rules removed from the repo. Add them
once this loop is running against one real tenant.
