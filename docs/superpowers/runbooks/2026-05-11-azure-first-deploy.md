# Azure First-Deploy Runbook

> Pasteable commands for Tasks 18, 23, 24 of [`docs/superpowers/plans/2026-05-11-azure-deployment-implementation.md`](../plans/2026-05-11-azure-deployment-implementation.md). Code on `main` is at the merge commit `ba57b19` or later. Run from the repository root.
>
> **Do not run any of these in CI.** Local terminal with an interactive `az login` and `gh` already authenticated.

## 0. Set your shell variables

Fill these in once, top of the runbook. Every later step expands them.

```bash
# --- Identity / subscription ---
export AZURE_SUBSCRIPTION_ID="<sub-uuid>"                 # az account show --query id -o tsv
export AZURE_TENANT_ID="<tenant-uuid>"                    # az account show --query tenantId -o tsv

# --- Naming / location ---
export RG_NAME="rg-neolore-queue-analytics"
export LOCATION="canadacentral"

# --- GitHub repo (owner/repo) ---
export GH_REPO="<owner>/<repo>"                           # e.g. neolore/MOTHERDUCK-EDA-CSH

# --- Secrets (NEVER commit) ---
export MOTHERDUCK_TOKEN_RW="<real token>"
export VERSATURE_CLIENT_ID="<real client id>"
export VERSATURE_CLIENT_SECRET="<real secret>"
export ADMIN_API_KEY="$(openssl rand -hex 32)"            # generate once; save somewhere safe
echo "ADMIN_API_KEY=$ADMIN_API_KEY   # SAVE THIS"
```

## 1. Sanity-check preconditions

```bash
az account show --query '{sub:id,tenant:tenantId,user:user.name}' -o table
gh auth status 2>&1 | head -5
gh repo view "$GH_REPO" --json name -q .name
git rev-parse HEAD                                        # should be at ba57b19 or a descendant
```

If any of these fail, fix that first — every step below assumes `az login` is current, `gh` is logged in to the right account, and you're standing in this repo's root.

## 2. Task 18 — OIDC service principal for GitHub Actions

This creates an Azure AD app + service principal that GitHub Actions can impersonate via OIDC (no long-lived secrets in the repo except `SWA_DEPLOYMENT_TOKEN`).

```bash
# 2.1. Create the AAD application
export APP_ID=$(az ad app create \
  --display-name "neolore-queue-github-actions" \
  --query appId -o tsv)
echo "APP_ID=$APP_ID"

# 2.2. Create the service principal for that app
az ad sp create --id "$APP_ID" --query id -o tsv
# → save as $SP_OBJECT_ID if you want it
```

Make sure the resource group exists *before* the role assignment, because the role is scoped to it:

```bash
az group create --name "$RG_NAME" --location "$LOCATION" -o none
```

```bash
# 2.3. Grant the SP Contributor on the resource group
az role assignment create \
  --assignee "$APP_ID" \
  --role Contributor \
  --scope "/subscriptions/$AZURE_SUBSCRIPTION_ID/resourceGroups/$RG_NAME"
```

```bash
# 2.4. Create one federated credential for pushes to main
az ad app federated-credential create --id "$APP_ID" --parameters "$(cat <<EOF
{
  "name": "github-main",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:${GH_REPO}:ref:refs/heads/main",
  "audiences": ["api://AzureADTokenExchange"]
}
EOF
)"
```

## 3. Task 23 — First-time Bicep deploy

### 3.1 Prepare the gitignored secrets parameter file

```bash
cat > infra/parameters.local.json <<EOF
{
  "\$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "motherduckTokenRw":     { "value": "$MOTHERDUCK_TOKEN_RW" },
    "versatureClientId":     { "value": "$VERSATURE_CLIENT_ID" },
    "versatureClientSecret": { "value": "$VERSATURE_CLIENT_SECRET" },
    "adminApiKey":           { "value": "$ADMIN_API_KEY" }
  }
}
EOF

# Confirm it's ignored:
git check-ignore -v infra/parameters.local.json
# Expected: prints the matching .gitignore rule.
# If it says "::", STOP — fix .gitignore first.
```

### 3.2 What-if (dry run) before the real apply

```bash
az deployment group what-if \
  --resource-group "$RG_NAME" \
  --template-file infra/main.bicep \
  --parameters infra/parameters.json \
  --parameters @infra/parameters.local.json
```

Read the diff. It should be 100% Create, no Modify or Delete. If anything looks like Modify or Delete, stop and investigate.

### 3.3 Actual deploy

```bash
az deployment group create \
  --name "neolore-first-deploy-$(date +%Y%m%d-%H%M)" \
  --resource-group "$RG_NAME" \
  --template-file infra/main.bicep \
  --parameters infra/parameters.json \
  --parameters @infra/parameters.local.json
```

Takes 5–10 minutes. On success, capture the outputs:

```bash
export DEPLOY_NAME=$(az deployment group list \
  --resource-group "$RG_NAME" \
  --query "sort_by([?contains(name, 'neolore-first-deploy')], &properties.timestamp)[-1].name" \
  -o tsv)

az deployment group show \
  --resource-group "$RG_NAME" --name "$DEPLOY_NAME" \
  --query 'properties.outputs' -o json | tee /tmp/neolore-outputs.json

# Pluck out the values we'll feed back into GitHub
export ACR_LOGIN_SERVER=$(jq -r '.acrLoginServer.value'        /tmp/neolore-outputs.json)
export JOB_NAME=$(        jq -r '.containerAppJobName.value'   /tmp/neolore-outputs.json)
export REPORTS_BASE_URL=$(jq -r '.reportsBaseUrl.value'        /tmp/neolore-outputs.json)
export FUNCTION_HOSTNAME=$(jq -r '.functionAppHostname.value'  /tmp/neolore-outputs.json)
export SWA_HOSTNAME=$(    jq -r '.swaHostname.value'           /tmp/neolore-outputs.json)
export FUNCTION_NAME=$(   jq -r '.functionAppName.value'       /tmp/neolore-outputs.json)
export STORAGE_NAME=$(    jq -r '.storageAccountName.value'    /tmp/neolore-outputs.json)
echo "ACR_LOGIN_SERVER=$ACR_LOGIN_SERVER"
echo "JOB_NAME=$JOB_NAME"
echo "REPORTS_BASE_URL=$REPORTS_BASE_URL"
echo "FUNCTION_HOSTNAME=$FUNCTION_HOSTNAME"
echo "SWA_HOSTNAME=$SWA_HOSTNAME"
```

### 3.4 Fetch the SWA deployment token

```bash
export SWA_DEPLOYMENT_TOKEN=$(az staticwebapp secrets list \
  --name "$(jq -r '.swaName.value' /tmp/neolore-outputs.json)" \
  --resource-group "$RG_NAME" \
  --query 'properties.apiKey' -o tsv)
echo "SWA_DEPLOYMENT_TOKEN (first 8 chars): ${SWA_DEPLOYMENT_TOKEN:0:8}…"
```

### 3.5 Set all GitHub repo secrets in one batch

```bash
gh secret set AZURE_CLIENT_ID        --body "$APP_ID"              --repo "$GH_REPO"
gh secret set AZURE_TENANT_ID        --body "$AZURE_TENANT_ID"     --repo "$GH_REPO"
gh secret set AZURE_SUBSCRIPTION_ID  --body "$AZURE_SUBSCRIPTION_ID" --repo "$GH_REPO"
gh secret set AZURE_RESOURCE_GROUP   --body "$RG_NAME"             --repo "$GH_REPO"
gh secret set ACR_NAME               --body "${ACR_LOGIN_SERVER%%.*}" --repo "$GH_REPO"
gh secret set CONTAINER_APP_JOB_NAME --body "$JOB_NAME"            --repo "$GH_REPO"
gh secret set VITE_REPORTS_BASE_URL  --body "$REPORTS_BASE_URL"    --repo "$GH_REPO"
gh secret set SWA_DEPLOYMENT_TOKEN   --body "$SWA_DEPLOYMENT_TOKEN" --repo "$GH_REPO"

gh secret list --repo "$GH_REPO"
```

### 3.6 Trigger the workflows by pushing main

Main already has the code (merge `ba57b19`); pushing triggers all three workflows.

```bash
git push origin main
```

Watch the three runs:

```bash
gh run watch --repo "$GH_REPO"
# Or, list them:
gh run list --repo "$GH_REPO" --limit 5
```

Wait for all three to go green. The pipeline-image workflow replaces the Job's placeholder image with the real one — confirm:

```bash
az containerapp job show \
  --name "$JOB_NAME" --resource-group "$RG_NAME" \
  --query 'properties.template.containers[0].image' -o tsv
# Expected: <acr>.azurecr.io/neolore-pipeline:<sha>
# If it still shows mcr.microsoft.com/k8se/quickstart-jobs:latest, the pipeline-image workflow hasn't finished.
```

## 4. Task 24 — Seed run + acceptance

### 4.1 Pick a period (most recent fully-closed month)

```bash
# Defaults to the calendar month that ended before today
export PERIOD_START=$(date -u -v-1m +%Y-%m-01)             # macOS BSD date
# If on Linux, use:  PERIOD_START=$(date -u -d "$(date -u +%Y-%m-01) -1 month" +%Y-%m-01)
export PERIOD_END=$(date -u -v1d -v-1m -v+1m -v-1d +%Y-%m-%d)
# Linux:  PERIOD_END=$(date -u -d "$(date -u +%Y-%m-01) -1 day" +%Y-%m-%d)
echo "Seeding $PERIOD_START → $PERIOD_END"
```

(Adjust manually if you want a specific month.)

### 4.2 Kick off the run via the Function

```bash
curl -i -X POST "https://$FUNCTION_HOSTNAME/api/run-pipeline" \
  -H "x-admin-key: $ADMIN_API_KEY" \
  -H "content-type: application/json" \
  -d "$(jq -n --arg s "$PERIOD_START" --arg e "$PERIOD_END" \
      '{period:"month", start:$s, end:$e, api_cache_mode:"auto"}')"
```

Expected: `HTTP/1.1 202 Accepted` with body `{"execution_name":"..."}`. Save the execution name.

### 4.3 Wait for completion

```bash
export EXEC_NAME="<paste from 4.2 response>"

# Tail logs while it runs (Ctrl-C to stop tailing)
az containerapp job logs show \
  --name "$JOB_NAME" --resource-group "$RG_NAME" \
  --execution "$EXEC_NAME" --follow

# Or poll status:
watch -n 5 "az containerapp job execution show \
  --name '$JOB_NAME' --resource-group '$RG_NAME' \
  --job-execution-name '$EXEC_NAME' \
  --query 'properties.status' -o tsv"
```

Expected status path: `Running` → `Succeeded`. If `Failed`, read the logs and re-run after fixing.

### 4.4 Verify the artifacts landed

```bash
# Manifest exists
az storage blob download \
  --account-name "$STORAGE_NAME" --container-name reports \
  --name manifest.json --auth-mode login --file /tmp/manifest.json
jq . /tmp/manifest.json
# Expected: contains an entry with key=YYYY-MM matching $PERIOD_START

# Period files exist
az storage blob list \
  --account-name "$STORAGE_NAME" --container-name reports --auth-mode login \
  --prefix "month_${PERIOD_START}_${PERIOD_END}/" --query '[].name' -o tsv
# Expected: metrics.json + metrics_8020.json + metrics_8021.json + metrics_8030.json + metrics_8031.json
```

### 4.5 Open the dashboard

```bash
open "https://$SWA_HOSTNAME"   # macOS
# xdg-open "https://$SWA_HOSTNAME"   # Linux
```

Confirm in the browser:
- Month selector lists the seeded month.
- Selecting it loads charts — open dev tools Network tab and verify fetches go to `https://*.blob.core.windows.net/reports/...`.
- No console errors.
- (Optional) In dev tools, block the manifest URL and reload — the UI should show an error state, **not** April 2026 fixture data. This proves the production fixture-fallback gate is correct.

### 4.6 Tag and (optionally) push the release tag

```bash
git tag -a v0.1.0-azure -m "First Azure deploy: pipeline + dashboard live"
git push origin v0.1.0-azure
```

## 5. Troubleshooting

### Lease collision on a re-run

`BLOB_LEASE_HELD: another execution is processing month_YYYY-MM-DD_YYYY-MM-DD` in the container logs means a previous execution is still in-flight. Wait for it, or — if you're sure it's hung — break the lease:

```bash
az storage blob lease break \
  --account-name "$STORAGE_NAME" --container-name reports \
  --blob-name ".locks/month_${PERIOD_START}_${PERIOD_END}.lock" \
  --auth-mode login
```

### Image still shows the placeholder

```bash
gh run list --repo "$GH_REPO" --workflow pipeline-image.yml --limit 3
```

If the pipeline-image workflow hasn't run yet, push an empty commit to retrigger:

```bash
git commit --allow-empty -m "ci: retrigger pipeline-image" && git push origin main
```

### Function 401 even with the right key

Confirm the Key Vault reference resolved at app start:

```bash
az functionapp config appsettings list \
  --name "$FUNCTION_NAME" --resource-group "$RG_NAME" \
  --query "[?name=='ADMIN_API_KEY'].value" -o tsv
# Expected: @Microsoft.KeyVault(...)
```

If it's the literal `@Microsoft.KeyVault(...)` string and the Function App's outbound identity is `id-neolore-function`, the role assignment is propagating. Wait 1-2 minutes and retry. Restart the Function App if it persists:

```bash
az functionapp restart --name "$FUNCTION_NAME" --resource-group "$RG_NAME"
```

### Rollback the pipeline image

```bash
az containerapp job update \
  --name "$JOB_NAME" --resource-group "$RG_NAME" \
  --image "$ACR_LOGIN_SERVER/neolore-pipeline:<previous-sha>"
```

(List available tags: `az acr repository show-tags --name "${ACR_LOGIN_SERVER%%.*}" --repository neolore-pipeline -o tsv`.)
