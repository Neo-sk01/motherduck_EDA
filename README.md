# NeoLore Queue Analytics

Batch analytics pipeline and dashboard data foundation for four NeoLore CSR queues.

## Local Setup

Use Python 3.11 or newer. On this machine, `python3` is older than the project requirement, so `uv` is the easiest local setup path:

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"
cp .env.example .env
```

Put secrets only in `.env`. Do not commit secrets.

## CSV Run

Place the four SONAR Queue Detail CSV files in `data/csv-uploads/`, then run:

```bash
python -m pipeline.main --source csv --period month --start 2026-04-01 --end 2026-04-30
```

The default command writes report JSON only. To also replace the matching period in MotherDuck/DuckDB tables, set `MOTHERDUCK_TOKEN_RW` and opt in explicitly:

```bash
python -m pipeline.main --source csv --period month --start 2026-04-01 --end 2026-04-30 --write-store
```

Backfills support arbitrary `--start` and `--end` dates. If a CSV export contains a broader range, rows outside the requested period are filtered before deduplication and metric computation.

## API Backfill

API mode is staged and restartable. It first pulls Versature CDRs plus queue stats into a durable local extract under `DATA_DIR/api_extracts/{start}_{end}/`, then transforms that extract into report JSON and, when requested, MotherDuck tables. If a MotherDuck write fails, rerun with `--api-cache-mode reuse` to replay the saved extract without pulling the API again.

Use either `VERSATURE_ACCESS_TOKEN`, or `VERSATURE_CLIENT_ID` plus `VERSATURE_CLIENT_SECRET` so the pipeline can request a one-hour access token:

```bash
DATA_DIR=dashboard/public/data python -m pipeline.main --source api --period month --start 2026-03-01 --end 2026-03-31
```

Cache modes:

- `--api-cache-mode auto` is the default. Reuse a complete extract if one exists; otherwise pull from the API and save it.
- `--api-cache-mode refresh` always pulls from the API and replaces the local extract.
- `--api-cache-mode reuse` requires an existing complete extract and never calls the API.

For a clean historical pull, force a fresh extract:

```bash
DATA_DIR=dashboard/public/data python -m pipeline.main --source api --period month --start 2026-03-01 --end 2026-03-31 --api-cache-mode refresh
```

To replace the matching period in MotherDuck from that saved extract:

```bash
DATA_DIR=dashboard/public/data python -m pipeline.main --source api --period month --start 2026-03-01 --end 2026-03-31 --api-cache-mode reuse --write-store
```

For the approved first historical pass, run full calendar months from January through March 2026.

## Tests

```bash
pytest
```

## Dashboard

```bash
cd dashboard
npm install
npm run dev
```

The dashboard defaults to:

```text
/data/reports/month_2026-04-01_2026-04-30/metrics.json
```

For local static serving, copy a generated report bundle into:

```text
dashboard/public/data/reports/
```

To refresh the April report:

```bash
python -m pipeline.main --source csv --period month --start 2026-04-01 --end 2026-04-30
```

The dashboard reads `dashboard/public/data/reports/manifest.json` and exposes available months through the `Report month` selector.

## Deploying to Azure

Production runs in Azure using a Container Apps Job (pipeline), a Function App (manual trigger), Blob Storage (reports), and Static Web Apps (dashboard). Design is in `docs/superpowers/specs/2026-05-11-azure-deployment-design.md`; implementation steps are in `docs/superpowers/plans/2026-05-11-azure-deployment-implementation.md`.

Reports are served from a public blob container for the dashboard. Treat generated report JSON as public-facing data and avoid placing raw call records, caller PII, or secrets in the report bundle.

### First deploy

1. Create a local `infra/parameters.local.json` (gitignored) with real secret values:
   ```json
   {
     "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
     "contentVersion": "1.0.0.0",
     "parameters": {
       "motherduckTokenRw": { "value": "<real token>" },
       "versatureClientId": { "value": "<real client id>" },
       "versatureClientSecret": { "value": "<real secret>" },
       "adminApiKey": { "value": "<choose a long random string>" }
     }
   }
   ```
2. Create the resource group and deploy Bicep:
   ```bash
   az group create --name rg-neolore-queue-analytics --location canadacentral
   az deployment group create \
     --resource-group rg-neolore-queue-analytics \
     --template-file infra/main.bicep \
     --parameters infra/parameters.json \
     --parameters @infra/parameters.local.json
   ```
3. Collect outputs (`acrLoginServer`, `containerAppJobName`, `reportsBaseUrl`, `swaHostname`, `functionAppHostname`) and set them as GitHub repo secrets per Task 18.
4. Push to `main`. The three GitHub Actions workflows fire:
   - Dashboard builds and uploads to SWA.
   - Pipeline image builds, pushes to ACR, and updates the Job.
   - Function code deploys.
5. Seed a first report:
   ```bash
   curl -X POST "https://<function-hostname>/api/run-pipeline" \
     -H "x-admin-key: <admin-api-key>" \
     -H "content-type: application/json" \
     -d '{"period":"month","start":"2026-04-01","end":"2026-04-30","api_cache_mode":"auto"}'
   ```
   Response is `202` with `{"execution_name": "..."}`. Watch the execution in the Azure portal under the Container Apps Job; wait for status = Succeeded. Verify the dashboard loads the April 2026 report.

### Operator runbook

Manual run for any prior month:

```bash
curl -X POST "https://<function-hostname>/api/run-pipeline" \
  -H "x-admin-key: <admin-api-key>" \
  -H "content-type: application/json" \
  -d '{"period":"month","start":"YYYY-MM-01","end":"YYYY-MM-DD","api_cache_mode":"auto"}'
```

Force a fresh API pull (ignore cache):

```bash
curl -X POST "https://<function-hostname>/api/run-pipeline" \
  -H "x-admin-key: <admin-api-key>" \
  -H "content-type: application/json" \
  -d '{"period":"month","start":"YYYY-MM-01","end":"YYYY-MM-DD","api_cache_mode":"refresh"}'
```

Replay from saved extract without calling Versature:

```bash
curl -X POST "https://<function-hostname>/api/run-pipeline" \
  -H "x-admin-key: <admin-api-key>" \
  -H "content-type: application/json" \
  -d '{"period":"month","start":"YYYY-MM-01","end":"YYYY-MM-DD","api_cache_mode":"reuse"}'
```

Note: the `reuse` cache mode requires the extract to exist on the container's ephemeral disk; in practice this matches `auto` for a fresh container.

Watch execution status:

```bash
az containerapp job execution list \
  --name <container-app-job-name> \
  --resource-group rg-neolore-queue-analytics \
  --query '[].{name:name,status:properties.status,start:properties.startTime}' -o table
```

Tail container logs for a specific execution:

```bash
az containerapp job logs show \
  --name <container-app-job-name> \
  --resource-group rg-neolore-queue-analytics \
  --execution <execution-name> --follow
```

Rollback the pipeline image:

```bash
az containerapp job update \
  --name <container-app-job-name> \
  --resource-group rg-neolore-queue-analytics \
  --image <acr-name>.azurecr.io/neolore-pipeline:<previous-sha>
```
