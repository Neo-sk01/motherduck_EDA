# Azure Deployment Design — NeoLore Queue Analytics

**Date:** 2026-05-11
**Status:** Approved design (revised after code review), ready for implementation planning
**Scope:** Deploy the existing Python batch pipeline and React/Vite static dashboard to Azure.

## Goal

Run the existing batch analytics pipeline on a monthly schedule (with manual override) and serve the existing static dashboard publicly, with both pieces deployable independently and minimal changes to the existing code.

## Non-Goals

- Changing the pipeline's existing CLI contract for explicit `--start`/`--end` runs (we only add a new "previous-month" mode for the cron entrypoint).
- Replacing MotherDuck with another store.
- Adding a backend/API layer in front of the dashboard's read path.
- Multi-region, multi-environment (staging/prod), or VNet-isolated deployments.
- Authentication on the dashboard. The dashboard is fully public by explicit decision (see "Data classification" below).
- Sanitizing, hashing, or redacting PII fields in the published reports.
- Persisting the pipeline's API extract cache across container runs.

## Data classification (explicit decision)

The published JSON reports contain `caller_number_norm` (raw caller phone numbers) under `top_callers` and `crossqueue.callers`, and `agent_name` identifiers under `agent_leaderboard` and `crossqueue.agents`. The dashboard, the blob container holding these reports, and the manifest are **all served publicly without authentication**. This was raised in code review and is an accepted decision — the operator wants full data visibility with no fields hidden.

Mitigations applied that don't change the user-visible surface:
- `dashboard/public/robots.txt` set to `User-agent: * / Disallow: /` and a `<meta name="robots" content="noindex,nofollow">` tag in `index.html`, to reduce search-engine indexing.
- The SWA URL and blob container URL are not advertised in any public-facing place outside of this repository.

We do **not** rely on these mitigations as security — they only reduce passive discovery. Anyone with the URL can read the data.

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
│  Entrypoint: python -m pipeline.azure_run  (new thin wrapper)     │
│                                                                   │
│  Wrapper resolves period from env vars (set per execution):       │
│   - PERIOD_MODE = "previous-month" | "explicit"                   │
│   - PERIOD_START / PERIOD_END (used when mode = explicit)         │
│   - API_CACHE_MODE = auto | refresh | reuse                       │
│   - DATA_DIR, MOTHERDUCK_*, VERSATURE_*, REPORTS_*                │
│                                                                   │
│  Then calls run_api/run_csv with resolved dates. Uploads only     │
│  after the run function returns successfully (post-MotherDuck).   │
│                                                                   │
│  Triggers:                                                        │
│   1. Schedule  →  cron `0 9 1 * *` UTC (≈ 04:00–05:00 ET on 1st)  │
│                   with PERIOD_MODE=previous-month                 │
│   2. Manual    →  Function patches PERIOD_* env vars on a one-off │
│                   execution (no command-args override)            │
└────────┬────────────────────────────────────────────┬─────────────┘
         │ writes durable analytics tables             │ writes report JSON
         ▼                                             ▼
┌────────────────────────┐               ┌────────────────────────────┐
│   MotherDuck           │               │  Azure Blob Storage        │
│   csh_analytics_v2     │               │  account: anon-read enabled│
│   (unchanged)          │               │  container: reports        │
│                        │               │   - publicAccess = blob    │
│                        │               │   - CORS GET from SWA host │
│                        │               │  Lease lock per period     │
│                        │               │   (held during run)        │
└────────────────────────┘               │  Files:                    │
                                         │   - manifest.json (last)   │
                                         │   - month_YYYY-MM-DD_*/... │
                                         └────────────┬───────────────┘
                                                      │ HTTPS fetch
                                                      ▼
                            ┌─────────────────────────────────────┐
                            │  Azure Static Web Apps              │
                            │  Dashboard (React/Vite build)       │
                            │  Free tier, GitHub Actions CI       │
                            │  robots noindex + meta noindex      │
                            └─────────────────────────────────────┘
                                          ▲
                                          │ public read
                                       end users
```

**Nine Azure resources plus existing MotherDuck:**

1. Resource Group (`rg-neolore-queue-analytics`, region `canadacentral`)
2. Storage Account (blob)
3. Azure Container Registry (Basic)
4. Container Apps Environment
5. Container Apps Job (pipeline)
6. Function App (manual-trigger endpoint)
7. Static Web App (dashboard)
8. Key Vault (secrets)
9. Log Analytics workspace (shared logging)

Plus one supporting user-assigned Managed Identity (`id-neolore-pipeline`) attached to both the Container App and the Function App.

## Components

### 1. Pipeline image (new `Dockerfile` at repo root)

- Base: `python:3.12-slim`
- Installs project via `pip install -e .` using existing `pyproject.toml`
- ENTRYPOINT: `python -m pipeline.azure_run` — new thin wrapper module (see Component 5)
- Reads all existing env vars plus the new ones listed in Component 2 below.

### 2. Container Apps Job (`neolore-pipeline-job`)

- **Schedule trigger:** cron `0 9 1 * *` UTC = 04:00–05:00 America/Toronto on the 1st (covers both EDT and EST). Env vars set on the schedule template:
  - `PERIOD_MODE=previous-month`
  - `PERIOD_TYPE=month`
  - `API_CACHE_MODE=auto`
  - `WRITE_STORE=1`
- **Manual trigger:** invoked by the Function via Azure REST `Jobs - Start` with an `ExecutionTemplate` patch that overrides **env vars only** (`PERIOD_MODE=explicit`, `PERIOD_START`, `PERIOD_END`, `API_CACHE_MODE`). The container image, resources, secrets, and command stay inherited from the Job's template — we do not override `args`.
- Replica timeout: 60 minutes. ParallelExecutions: 1, ReplicaCompletionCount: 1 (so a manual + scheduled overlap on the same execution would queue).
- Secrets pulled from Key Vault via Container App secret refs.
- Logs to shared Log Analytics workspace.

### 3. Manual-trigger Function (`functions/run-pipeline/`)

- Single HTTP-triggered Python function: `POST /api/run-pipeline`
- Auth: `x-admin-key` header compared against a Key Vault-backed app setting. 401 on missing/mismatch.
- Request body: `{ "period": "month", "start": "YYYY-MM-DD", "end": "YYYY-MM-DD", "api_cache_mode": "auto" }`
- Validation rules (all enforced before the Azure REST call):
  - `start` and `end` parse as ISO dates; `start <= end`.
  - `end` is not in the future relative to UTC now.
  - `(end - start)` ≤ 92 days (covers any single calendar month with margin).
  - `api_cache_mode` ∈ {`auto`, `refresh`, `reuse`}; defaults to `auto` if absent.
  - `period` ∈ {`day`, `week`, `month`}; defaults to `month`.
- On success: calls Azure REST `POST /subscriptions/.../jobs/<job>/start` with an `ExecutionTemplate` that overrides only env vars (per Component 2). Returns `{ "execution_name": "..." }`.
- Logs (info level) for every request: timestamp, source IP, user-agent, requested period range, resolved execution name, and whether admin-key matched. No PII in logs.
- Uses the user-assigned Managed Identity for the REST call. Stays on Consumption tier.
- **Recommended hardening for production (not v1):** front with APIM IP-allowlist or replace `x-admin-key` with Entra (App Roles) auth. Documented in README but out of scope for first deploy.

### 4. Static Web App (`neolore-dashboard`)

- Source: `dashboard/` folder, build command `npm run build`, output `dist/`.
- SPA fallback to `/index.html` via `staticwebapp.config.json`.
- Build-time env `VITE_REPORTS_BASE_URL` points at the blob container's public URL (e.g. `https://<acct>.blob.core.windows.net/reports`).
- `dashboard/public/robots.txt`: `User-agent: * / Disallow: /`.
- `<meta name="robots" content="noindex,nofollow">` added to `index.html`.
- GitHub Actions workflow auto-generated on first deploy.

### 5. Existing code changes

**`pipeline/azure_run.py` (new, ~60 lines).** Thin entrypoint module used by the container:

1. Reads env vars: `PERIOD_MODE`, `PERIOD_TYPE`, `PERIOD_START`, `PERIOD_END`, `API_CACHE_MODE`, `WRITE_STORE`, `TIMEZONE`, `SOURCE` (default `api`).
2. If `PERIOD_MODE=previous-month`: computes `start`/`end` for the calendar month immediately preceding "now" in `TIMEZONE`. If `PERIOD_MODE=explicit`: reads `PERIOD_START` / `PERIOD_END` directly.
3. Acquires a blob lease on `reports/.locks/<period_key>.lock` (creates the blob if missing). On lease conflict: exit non-zero with a clear message. This guards against scheduled+manual overlap on the same period.
4. Calls `pipeline.main.run_api` / `run_csv` with resolved dates.
5. **Only on successful return** of the run function, calls `pipeline.blob_upload.upload_reports` to copy `DATA_DIR/reports/` to blob, manifest last.
6. Releases the lease in a `finally` block.

This wrapper keeps `pipeline/main.py` and its CLI contract unchanged. Local CLI usage is unaffected.

**`pipeline/blob_upload.py` (new, ~50 lines).** Uses `azure-identity.DefaultAzureCredential` + `azure-storage-blob.BlobServiceClient`. Walks `DATA_DIR/reports/`, uploads every file under `month_*/`, then writes `manifest.json` last. Skipped (no-op) if `REPORTS_STORAGE_ACCOUNT_URL` is unset, so local dev is unaffected.

**`pipeline/report.py`** — update `_update_manifest` so the `path` field is a relative path (`month_{start}_{end}/metrics.json`) instead of `/data/reports/month_*/metrics.json`. The dashboard resolver prepends a base URL.

**`dashboard/src/data/reportManifest.ts`:**
- Change `MANIFEST_PATH` and the body of `buildReportPath` so both pull from a single base resolver: `(import.meta.env.VITE_REPORTS_BASE_URL ?? "/data/reports").replace(/\/$/, "")`.
- After loading manifest entries, normalize: if an entry's `path` is relative (no leading `/` and not absolute URL), prepend the base. Backward compatible with existing absolute-path entries.

**`dashboard/src/data/reportLoader.ts`:** `DEFAULT_REPORT_PATH` derived from the same base resolver.

**`pyproject.toml`** — add to runtime `dependencies`:
- `azure-identity>=1.16.0`
- `azure-storage-blob>=12.20.0`

**`.env.example`** — add: `REPORTS_STORAGE_ACCOUNT_URL`, `REPORTS_CONTAINER` (default `reports`), `ADMIN_API_KEY`, `PERIOD_MODE`, `PERIOD_TYPE`, `PERIOD_START`, `PERIOD_END`, `API_CACHE_MODE`, `WRITE_STORE`. All marked optional for local dev.

**`README.md`** — append "Deploying to Azure" section with first-deploy steps and operator runbook.

## Data Flow & Storage

| Data | Stored in | Notes |
|---|---|---|
| Raw call records, queue tables, anomalies | MotherDuck `csh_analytics_v2` | Unchanged. |
| Report JSON (`manifest.json`, `metrics.json`, `metrics_<queue>.json`) | Blob `reports` container | Public-read GET; per-period lease lock during writes. |
| Period locks (`.locks/<period_key>.lock`) | Same container, `.locks/` prefix | Empty placeholder blobs used solely for lease coordination. |
| API extract cache (`api_extracts/...`) | Ephemeral container disk | Not persisted across runs in v1. |
| CSV uploads | Out of scope for prod | API is primary source; CSV remains a local-dev path. |

**Blob layout** (mirrors current `dashboard/public/data/reports/`, but with relative manifest paths):

```
reports/
  manifest.json                              ← written last
  month_2026-04-01_2026-04-30/
    metrics.json
    metrics_8020.json
    metrics_8021.json
    metrics_8030.json
    metrics_8031.json
  .locks/
    month_2026-04-01_2026-04-30.lock         ← lease target
```

Inside `manifest.json`, entries use **relative** `path` values:

```json
{ "key": "2026-04", "label": "April 2026", "start": "2026-04-01", "end": "2026-04-30",
  "path": "month_2026-04-01_2026-04-30/metrics.json", "source": "api",
  "validation_status": "success" }
```

The dashboard prepends `VITE_REPORTS_BASE_URL` at fetch time.

**Scheduled run sequence:**

1. Container starts at 09:00 UTC on the 1st of the month. Reads `PERIOD_MODE=previous-month`, `TIMEZONE=America/Toronto`.
2. Wrapper computes `start`/`end` = the calendar month that just ended in Toronto local time.
3. Acquires blob lease on `.locks/month_{start}_{end}.lock` (60-second renewable lease, renewed every 30s during the run).
4. `--source api` pulls Versature CDRs + queue stats to ephemeral disk.
5. Transforms; writes report JSON to local `DATA_DIR`.
6. Writes MotherDuck tables (existing in-function step at [pipeline/main.py:193](pipeline/main.py#L193)).
7. `run_api` returns successfully → wrapper now uploads all files under `month_*/`, then writes `manifest.json` last.
8. Lease released.

**Manual run:** same flow, with `PERIOD_MODE=explicit` and operator-supplied `PERIOD_START`/`PERIOD_END`. Lease acquisition will fail (non-zero exit, clear error) if a scheduled run is already in progress on the same period.

**Idempotency:** pipeline already replaces the matching period in MotherDuck on `--write-store`; blob uploads are full overwrites by path; the lease serializes concurrent runs on the same period; manifest-last ordering means partial uploads never appear in the dashboard's index.

**Failure model** (corrected from the prior spec to match actual code ordering):

| Failure point | State after failure | Operator action |
|---|---|---|
| API pull fails | Local JSON not written; no MotherDuck write; no upload. Dashboard unchanged. | Re-run manually (`auto` cache mode). |
| Report JSON write fails | No MotherDuck write; no upload. Dashboard unchanged. | Re-run. |
| MotherDuck write fails (after JSON write) | MotherDuck unchanged; **upload skipped** (wrapper only uploads on `run_*` success). Dashboard unchanged. | Re-run; existing retry logic in `_write_api_outputs_to_store` handles transient errors. |
| Blob upload fails after MotherDuck write succeeded | MotherDuck ahead of dashboard. Manifest unchanged (still pointing at prior period). | Re-run upload step manually, or re-run the full job — idempotent. |
| Lease acquisition fails | Run aborts before any writes. | Wait for in-flight run to complete; or release stale lease via Azure portal/CLI. |

**Storage account settings (Bicep-enforced):**

- `allowBlobPublicAccess: true` on the storage account.
- Container `publicAccess: 'Blob'` on `reports`.
- CORS rule: `GET, HEAD` from the SWA hostname and `https://*.azurestaticapps.net`. CORS is browser-side only and is not authorization — anyone outside a browser can still GET blobs directly. Acceptable per data classification decision.

## Secrets & Security

| Secret | Stored in | Read by | Mechanism |
|---|---|---|---|
| `MOTHERDUCK_TOKEN_RW` | Key Vault | Pipeline container | Container App secret ref via UAMI |
| `VERSATURE_CLIENT_ID` / `VERSATURE_CLIENT_SECRET` | Key Vault | Pipeline container | Container App secret ref via UAMI |
| Blob write access | n/a | Pipeline container | UAMI with `Storage Blob Data Contributor` on the storage account |
| Job-start permission | n/a | Function | UAMI with `Container Apps Jobs Contributor` on the Job |
| `ADMIN_API_KEY` | Key Vault | Function | App setting ref via UAMI |
| ACR pull | n/a | Container Apps Environment | UAMI with `AcrPull` on the registry |

A single user-assigned Managed Identity (`id-neolore-pipeline`) is attached to both the Container App and the Function App. This avoids the first-deploy ordering pain of system-assigned identities (which don't exist until the parent resource is created, blocking Key Vault role assignments and ACR pulls in the same Bicep deployment).

Non-secret config (queue IDs, DNIS numbers, timezone) lives in plain Container App env vars with the same names as `.env.example`.

**Public surface:**

| Endpoint | Auth |
|---|---|
| `https://<swa-domain>/*` | None (public dashboard — accepted) |
| `https://<storage>.blob.core.windows.net/reports/*` | None (public read GET; PUT requires Storage MI) |
| `https://<function>.azurewebsites.net/api/run-pipeline` | `x-admin-key` header + payload validation (max 92-day window, no future dates) |
| Container Apps Job | Not publicly reachable; only via Azure REST/CLI |

**Network posture:** all egress over public internet (TLS). No VNet, no private endpoints in v1. Documented as a follow-up if compliance ever requires it.

## Error Handling & Operations

1. **Pipeline failure** → container exits non-zero, lease auto-released after 60s, alert fires (see below).
2. **Function failure** (invalid request, REST call failure) → returns 4xx/5xx with body explaining why; caller retries.
3. **Concurrency collision** → lease acquisition fails with a clear `BLOB_LEASE_HELD` error; operator sees this in Log Analytics or in the Function response if they triggered it.
4. **Logging:** Container Apps Job stdout/stderr, Function logs, Storage logs all flow to one Log Analytics workspace.
5. **Alerting (v1):** one alert rule — "Container Apps Job execution failed in last 1h" → email to a configurable address. Plus one rule for "Function 5xx > 0 in 15m" as a low-priority canary.
6. **First-month seed:** after initial deploy, operator manually triggers a run for the most recent completed month (`api_cache_mode: auto`) to populate the dashboard with at least one report before users see it.

**Explicitly NOT in v1:**

- Retry/backoff logic in the Function (caller retries).
- Webhook from Job completion to anything else.
- Auditable user identity on manual triggers (only IP + admin-key-validity, see Component 3).
- Rate-limiting on the trigger endpoint (admin key + window validation is the v1 control).
- VNet / private endpoints.
- Dashboard authentication (data classification decision).

## Build, Deploy, Costs

### New files

```
Dockerfile
.dockerignore
pipeline/azure_run.py
pipeline/blob_upload.py
infra/main.bicep
infra/parameters.json
functions/run-pipeline/__init__.py
functions/run-pipeline/function.json
functions/host.json
functions/requirements.txt
dashboard/public/robots.txt
.github/workflows/dashboard.yml
.github/workflows/pipeline-image.yml
.github/workflows/function.yml
```

### Edited files

- `pipeline/main.py` (no behavior change; only consumed by `azure_run.py`)
- `pipeline/report.py` (relative manifest paths)
- `dashboard/src/data/reportManifest.ts` (base URL resolver)
- `dashboard/src/data/reportLoader.ts` (base URL resolver)
- `dashboard/index.html` (noindex meta)
- `pyproject.toml` (new deps)
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

1. `az login` → `az group create` → `az deployment group create -f infra/main.bicep`. Bicep creates: UAMI, Storage Account + `reports` container, ACR, Key Vault (with secrets pre-populated via `--parameters`), Log Analytics, Container Apps Env, Container Apps Job (image initially `mcr.microsoft.com/k8se/quickstart-jobs:latest`), Function App, SWA, and all role assignments.
2. Set GitHub repo secrets: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `SWA_DEPLOYMENT_TOKEN`, `VITE_REPORTS_BASE_URL`, `ACR_NAME`, `CONTAINER_APP_JOB_NAME`.
3. Push to `main`; all three workflows run. The pipeline-image workflow replaces the placeholder image with our actual one.
4. Manually trigger the Job for the most recent completed month via the Function endpoint to seed a first report; verify the dashboard shows it.

### Rollback

- **Dashboard:** revert the commit → SWA redeploys, or use SWA environment swap.
- **Pipeline:** image is tagged `:<sha>` — `az containerapp job update --image <prev-sha>` rolls it back. ACR retains history.
- **Function:** redeploy a prior commit.

## Open Items (deferred from v1)

- Persisting API extract cache across container runs (mount Azure Files) — only if Versature extracts get expensive enough that mid-run retries become important.
- Staging environment — single prod environment for now.
- VNet / private endpoints — add if compliance requires.
- APIM IP-allowlist or Entra-protected manual trigger — recommended before broad operator access; v1 uses admin key + payload validation.
- Auditable user identity on manual triggers.
