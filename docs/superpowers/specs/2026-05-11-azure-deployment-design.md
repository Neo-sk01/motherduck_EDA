# Azure Deployment Design — NeoLore Queue Analytics

**Date:** 2026-05-11
**Status:** Approved design, ready for implementation planning
**Scope:** Deploy the existing Python batch pipeline and React/Vite static dashboard to Azure.

## Goal

Run the existing batch analytics pipeline on a monthly schedule (with manual override) and serve the existing static dashboard publicly, with both pieces deployable independently and minimal changes to the existing code.

## Non-Goals

- Changing the pipeline's existing CLI contract or its supported flags.
- Replacing MotherDuck with another store.
- Adding a backend/API layer in front of the dashboard's read path.
- Multi-region, multi-environment (staging/prod), or VNet-isolated deployments.
- Authentication on the dashboard (it is fully public, read-only).
- Persisting the pipeline's API extract cache across container runs.

## Architecture

```
                            ┌─────────────────────────┐
                            │  Versature API          │
                            │  (CDRs + queue stats)   │
                            └────────────┬────────────┘
                                         │ HTTPS (pulled by pipeline)
                                         ▼
┌───────────────────────────────────────────────────────────────────┐
│                       Azure Container Apps Job                    │
│  Image: neolore-queue-pipeline:<sha>  (built from Dockerfile)     │
│                                                                   │
│  Triggers:                                                        │
│   1. Schedule  →  cron `0 3 1 * *` (monthly, 03:00 UTC)           │
│   2. Manual    →  Azure REST API call from Function (§ Components)│
└────────┬────────────────────────────────────────────┬─────────────┘
         │ writes durable analytics tables             │ writes report JSON
         ▼                                             ▼
┌────────────────────────┐               ┌────────────────────────────┐
│   MotherDuck           │               │  Azure Blob Storage        │
│   csh_analytics_v2     │               │  container: reports        │
│   (unchanged)          │               │  - manifest.json           │
│                        │               │  - month_YYYY-MM-DD_*/...  │
└────────────────────────┘               │  Public-read GET, CORS on  │
                                         └────────────┬───────────────┘
                                                      │ HTTPS fetch
                                                      ▼
                            ┌─────────────────────────────────────┐
                            │  Azure Static Web Apps              │
                            │  Dashboard (React/Vite build)       │
                            │  Free tier, GitHub Actions CI       │
                            └─────────────────────────────────────┘
                                          ▲
                                          │ public read
                                       end users
```

Five Azure resources plus existing MotherDuck:

- Resource Group (`rg-neolore-queue-analytics`, region `canadacentral`)
- Storage Account (blob)
- Azure Container Registry
- Container Apps Environment + Container Apps Job (pipeline)
- Function App (manual-trigger HTTP endpoint)
- Static Web App (dashboard)
- Key Vault (secrets)
- Log Analytics workspace (logs/alerting)

## Components

### 1. Pipeline image (new `Dockerfile` at repo root)

- Base: `python:3.12-slim`
- Installs project via `pip install -e .` using existing `pyproject.toml`
- ENTRYPOINT: `python -m pipeline.main` — same flags the CLI already supports
- Reads existing env vars (`MOTHERDUCK_TOKEN_RW`, `VERSATURE_*`, `DATA_DIR`, queue/DNIS settings)
- One new env var: `REPORTS_BLOB_CONN` (or Managed Identity) used by the new uploader step

### 2. Container Apps Job (`neolore-pipeline-job`)

- **Schedule trigger:** cron `0 3 1 * *` (1st of each month, 03:00 UTC). Default args run the previous calendar month against `--source api --write-store`.
- **Manual trigger:** invoked via Azure REST API by the Function. Accepts arbitrary period args.
- Replica timeout: 60 minutes.
- Secrets pulled from Key Vault references in the Container App's secret store.
- Logs to Log Analytics workspace.

### 3. Manual-trigger Function (`functions/run-pipeline/`)

- Single HTTP-triggered Python function: `POST /api/run-pipeline`
- Auth: `x-admin-key` header compared against a Key Vault-backed app setting. 401 on missing/mismatch.
- Request body: `{ "period": "month", "start": "YYYY-MM-DD", "end": "YYYY-MM-DD", "api_cache_mode": "auto" }`
- Action: calls Azure REST API (`POST /subscriptions/.../jobs/<job>/start`) with those args, returns the execution name. Uses the Function's system-assigned Managed Identity for auth.
- Stays on Consumption tier.

### 4. Static Web App (`neolore-dashboard`)

- Source: `dashboard/` folder, build command `npm run build`, output `dist/`.
- SPA fallback to `/index.html` via `staticwebapp.config.json`.
- Build-time env `VITE_REPORTS_BASE_URL` points at the blob container's public URL.
- GitHub Actions workflow auto-generated on first deploy.

### 5. Existing code changes

- **`pipeline/blob_upload.py` (new, ~30 lines):** walks `DATA_DIR/reports/`, uploads new/changed files to the `reports` container, writes `manifest.json` last. Skipped if `REPORTS_BLOB_CONN` is unset and no Managed Identity is available (so local CLI runs are unaffected).
- **`pipeline/main.py`:** call `blob_upload.upload_reports()` after `report.write_*` succeeds.
- **`dashboard/src/...`:** wherever the report base path is built, replace hardcoded `/data/reports` with `import.meta.env.VITE_REPORTS_BASE_URL ?? '/data/reports'` so local dev keeps working.
- **`.env.example`:** add `REPORTS_BLOB_CONN` and `ADMIN_API_KEY` placeholders, marked optional for local dev.
- **`README.md`:** append a "Deploying to Azure" section.

## Data Flow & Storage

| Data | Stored in | Notes |
|---|---|---|
| Raw call records, queue tables, anomalies | MotherDuck `csh_analytics_v2` | Unchanged. |
| Report JSON (`manifest.json`, `metrics.json`) | Blob `reports` container | Public-read GET only. |
| API extract cache (`api_extracts/...`) | Ephemeral container disk | Not persisted across runs in v1. |
| CSV uploads | Out of scope for prod | API is the primary source; CSV remains a local-dev path. |

**Blob layout** (mirrors current `dashboard/public/data/reports/` exactly):

```
reports/
  manifest.json
  month_2026-04-01_2026-04-30/
    metrics.json
  month_2026-03-01_2026-03-31/
    metrics.json
  ...
```

**Scheduled run sequence:**

1. Container starts at 03:00 UTC on the 1st of the month.
2. Period = previous calendar month.
3. `--source api` pulls Versature CDRs + queue stats to ephemeral disk.
4. Transforms; writes MotherDuck tables (`--write-store`).
5. Writes report JSON to local `DATA_DIR`.
6. Uploader copies report files to the `reports` blob container, writes `manifest.json` last.
7. Container exits 0.

**Manual run:** same flow, triggered via Function with explicit `start`/`end`. Suitable for backfills.

**Idempotency:** pipeline already replaces the matching period in MotherDuck on `--write-store`; blob uploads are full overwrites by path. Manifest-last ordering means the dashboard never references a missing report.

**CORS:** storage account allows `GET` from the SWA domain and `https://*.azurestaticapps.net`.

## Secrets & Security

| Secret | Stored in | Read by | Preferred access |
|---|---|---|---|
| `MOTHERDUCK_TOKEN_RW` | Key Vault → Container App secret ref | Pipeline container | Container App secret ref |
| `VERSATURE_CLIENT_ID` / `VERSATURE_CLIENT_SECRET` | Key Vault → Container App secret ref | Pipeline container | Container App secret ref |
| Blob write access | n/a (Managed Identity) | Pipeline container | Container App system-assigned MI with `Storage Blob Data Contributor` on the storage account |
| Job-start permission | n/a (Managed Identity) | Function | Function system-assigned MI with `Container Apps Jobs Contributor` on the Job |
| `ADMIN_API_KEY` | Key Vault → Function app setting ref | Function | App setting ref |

Connection strings are a fallback only if Managed Identity setup proves blocking.

Non-secret config (queue IDs, DNIS numbers, timezone) lives in plain Container App env vars with the same names as `.env.example`.

**Public surface:**

| Endpoint | Auth |
|---|---|
| `https://<swa-domain>/*` | None (public dashboard) |
| `https://<storage>.blob.core.windows.net/reports/*` | None (public read, GET only) |
| `https://<function>.azurewebsites.net/api/run-pipeline` | `x-admin-key` header |
| Container Apps Job | Not publicly reachable; Azure-internal only |

**Network posture:** all egress over public internet (TLS). No VNet, no private endpoints in v1.

## Error Handling

1. **API pull fails partway** → container exits non-zero, no blob upload, dashboard keeps showing the prior period. Operator re-runs manually.
2. **MotherDuck write fails after a successful API pull** → same — non-zero exit, no upload, re-run.
3. **Blob upload fails after MotherDuck write succeeded** → MotherDuck is ahead of the dashboard; operator re-runs uploader. Manifest-last ordering prevents half-state from being visible.
4. **Function fails to start the Job** → returns 5xx with the underlying Azure error; caller retries.
5. **Logging:** Job stdout/stderr and Function logs all flow to one Log Analytics workspace.
6. **Alerting (v1):** one alert rule — "Container Apps Job execution failed" → email to a configurable address.

**Explicitly NOT in v1:**

- Retry/backoff logic inside the Function (caller retries).
- Webhook from Job completion.
- Audit log of who hit the manual trigger (Function logs that admin key was valid; nothing more).
- Rate-limiting on the trigger endpoint.

## Build, Deploy, Costs

### New files

```
Dockerfile
.dockerignore
pipeline/blob_upload.py
infra/main.bicep
infra/parameters.json
functions/run-pipeline/__init__.py
functions/run-pipeline/function.json
functions/host.json
functions/requirements.txt
.github/workflows/dashboard.yml
.github/workflows/pipeline-image.yml
.github/workflows/function.yml
```

### Edited files

- `pipeline/main.py`
- `dashboard/src/...` (report-base-URL plumbing)
- `.env.example`
- `README.md`

### CI/CD

- **Dashboard:** push to `main` with changes under `dashboard/**` → SWA GitHub Action builds and deploys. `VITE_REPORTS_BASE_URL` passed via repo secret.
- **Pipeline image:** push to `main` with changes under `pipeline/**`, `Dockerfile`, or `pyproject.toml` → builds image, pushes to ACR tagged `:<sha>` and `:latest`, updates the Container Apps Job.
- **Function:** push to `main` with changes under `functions/**` → `Azure/functions-action@v1`.

All workflows authenticate to Azure via OIDC federated credentials — no long-lived secrets in GitHub.

### Estimated cost

| Resource | SKU | Approx. monthly |
|---|---|---|
| Storage Account | Standard LRS | <$1 |
| Container Registry | Basic | ~$5 |
| Container Apps Environment | Consumption | $0 fixed |
| Container Apps Job | Consumption per-run | ~$0.50 for one ~10 min run/month |
| Function App | Consumption | $0 (free tier) |
| Static Web App | Free | $0 |
| Key Vault | Standard | <$1 |
| Log Analytics | Pay-as-you-go | <$2 |

**Ballpark <$10/month.**

### First-time deploy order

1. `az login` → `az group create` → `az deployment group create -f infra/main.bicep`.
2. Set GitHub repo secrets: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `SWA_DEPLOYMENT_TOKEN`, `VITE_REPORTS_BASE_URL`.
3. Push to `main`; all three workflows run.
4. Manually trigger the Job once via `az containerapp job start` to seed a first report; verify the dashboard shows it.

### Rollback

- **Dashboard:** revert the commit → SWA redeploys, or use SWA environment swap.
- **Pipeline:** Container Apps Job's image is tagged `:<sha>` — `az containerapp job update --image <prev-sha>` rolls it back. ACR retains history.
- **Function:** redeploy a prior commit.

## Open Items (deferred from v1)

- Persisting API extract cache across container runs (mount Azure Files) — only if Versature extracts get expensive enough that mid-run retries become important.
- Staging environment — single prod environment for now.
- VNet / private endpoints — add if compliance requires.
- SAS-token access to the blob container — public-read is sufficient while the dashboard is public.
