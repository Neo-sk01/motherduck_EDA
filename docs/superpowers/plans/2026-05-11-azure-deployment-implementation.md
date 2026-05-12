# Azure Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy the NeoLore Queue Analytics pipeline + React dashboard to Azure per the approved design in `docs/superpowers/specs/2026-05-11-azure-deployment-design.md` (commit `e23e1ec`).

**Architecture:** Five-component split — pipeline image runs in a Container Apps Job (scheduled + manual via Function trigger), reports land in Blob Storage with ETag-CAS-protected manifest, dashboard reads them from a public blob URL via Static Web Apps. All infra in a single Bicep template, two user-assigned MIs for least privilege, three GitHub Actions workflows authenticate via OIDC.

**Tech Stack:** Python 3.12, `azure-identity`, `azure-storage-blob`, `httpx`, Azure Functions Python worker, Azure Container Apps, Azure Static Web Apps, Bicep, GitHub Actions OIDC.



## How To Read This Plan

The plan is grouped into **seven phases**:

1. **Pipeline code** (Tasks 1-6) — all local, TDD, no Azure.
2. **Dashboard code** (Tasks 7-9) — all local, TDD, no Azure.
3. **Function code** (Tasks 10-12) — local + TDD, no Azure runtime needed for unit tests.
4. **Container image** (Task 13) — local Docker build only.
5. **Bicep IaC** (Tasks 14-17) — creates Azure shell; deployed once by operator.
6. **CI/CD workflows** (Tasks 18-21) — depend on Azure resources existing.
7. **Docs + first deploy** (Tasks 22-24) — runbook execution.

**Order of merges to `main` (critical to avoid half-deployed state):**

- Phases 1-4 may merge in any order — all code is backward-compatible with local CLI/dev (blob upload is a no-op without env vars; dashboard falls back to `/data/reports`).
- Phase 5 (Bicep) merges only after the operator has done the **first manual Bicep deploy** (Task 23). Committing Bicep without deploying is fine; the workflows in Phase 6 will fail-soft.
- Phase 6 (workflows) merges only **after** Phase 5's first deploy has succeeded. Workflows immediately try to push images / call resources.
- Phase 7's seed run is the final acceptance step.

Each task ends with a commit. Don't squash across tasks.

---

## File Inventory

**New files:**

```
Dockerfile
.dockerignore
pipeline/azure_run.py
pipeline/blob_upload.py
tests/test_azure_run.py
tests/test_blob_upload.py
functions/host.json
functions/requirements.txt
functions/run-pipeline/__init__.py
functions/run-pipeline/function.json
functions/tests/test_run_pipeline.py
functions/tests/conftest.py
infra/main.bicep
infra/parameters.json
dashboard/public/robots.txt
.github/workflows/dashboard.yml
.github/workflows/pipeline-image.yml
.github/workflows/function.yml
```

**Modified files:**

```
pipeline/report.py                          # relative manifest paths
pipeline/main.py                            # no behavior change (see Task 6 note)
pyproject.toml                              # azure-identity, azure-storage-blob
tests/test_report.py                        # relative manifest path assertions
dashboard/src/data/reportManifest.ts        # base URL resolver, fixture gate
dashboard/src/data/reportLoader.ts          # base URL resolver, fixture gate
dashboard/src/data/reportManifest.test.ts
dashboard/src/data/reportLoader.test.ts
dashboard/index.html                        # noindex meta
.env.example
.gitignore                                  # add infra/parameters.local.json
README.md                                   # "Deploying to Azure" section
```

---

## Phase 1: Pipeline code (TDD, no Azure)

### Task 1: Add Azure SDK dependencies

**Files:**
- Modify: `pyproject.toml:9-16`

- [ ] **Step 1: Read current deps**

Run: `cat pyproject.toml | sed -n '5,20p'`
Expected: `dependencies = [` block with `duckdb`, `httpx`, `pandas`, `pyarrow`, `python-dotenv`, `tenacity`.

- [ ] **Step 2: Add the two new runtime deps**

Edit `pyproject.toml`, replacing the `dependencies` list:

```toml
dependencies = [
  "duckdb>=1.2.0",
  "httpx>=0.27.0",
  "pandas>=2.2.0",
  "pyarrow>=15.0.0",
  "python-dotenv>=1.0.0",
  "tenacity>=8.2.0",
  "azure-identity>=1.16.0",
  "azure-storage-blob>=12.20.0"
]
```

- [ ] **Step 3: Reinstall the project so new deps land in the venv**

Run: `uv pip install -e ".[dev]"`
Expected: installs `azure-identity` and `azure-storage-blob` plus their transitive deps (`azure-core`, `cryptography`, `msal`, etc.) without breaking existing packages.

- [ ] **Step 4: Verify imports**

Run: `python -c "import azure.identity, azure.storage.blob; print('ok')"`
Expected: `ok`

- [ ] **Step 5: Verify existing test suite still passes**

Run: `pytest -q`
Expected: same green result as before the dep changes (no new failures).

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml
git commit -m "build: add azure-identity and azure-storage-blob runtime deps"
```

---

### Task 2: report.py — relative manifest paths

**Files:**
- Modify: `pipeline/report.py:47-70` (`_update_manifest` function)
- Test: `tests/test_report.py`

The current `_update_manifest` writes `"path": f"/data/reports/month_{start}_{end}/metrics.json"` into manifest entries. We need it to write the **relative** form (`month_{start}_{end}/metrics.json`) so the dashboard can prepend a base URL.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_report.py`:

```python
def test_manifest_path_is_relative(tmp_path):
    write_report_bundle(
        data_dir=tmp_path,
        period="month",
        start="2026-04-01",
        end="2026-04-30",
        queue_metrics={"8020": {"queue_id": "8020"}},
        crossqueue={},
        anomalies=[],
    )
    manifest = json.loads((tmp_path / "reports" / "manifest.json").read_text())
    assert manifest["reports"][0]["path"] == "month_2026-04-01_2026-04-30/metrics.json"


def test_manifest_replaces_existing_entry_for_same_period(tmp_path):
    for source in ("csv", "api"):
        write_report_bundle(
            data_dir=tmp_path,
            period="month",
            start="2026-04-01",
            end="2026-04-30",
            queue_metrics={"8020": {"queue_id": "8020"}},
            crossqueue={},
            anomalies=[],
            source_mode=source,
        )
    manifest = json.loads((tmp_path / "reports" / "manifest.json").read_text())
    assert len(manifest["reports"]) == 1
    assert manifest["reports"][0]["source"] == "api"
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `pytest tests/test_report.py::test_manifest_path_is_relative tests/test_report.py::test_manifest_replaces_existing_entry_for_same_period -v`
Expected: first fails (path starts with `/data/reports/`); second already passes (existing dedupe logic).

- [ ] **Step 3: Update `_update_manifest`**

Edit `pipeline/report.py`, replacing the `path` line in `_update_manifest`:

```python
    entry = {
        "key": key,
        "label": _month_label(start),
        "start": start,
        "end": end,
        "path": f"month_{start}_{end}/metrics.json",
        "source": source_mode,
        "validation_status": str(validation.get("status", "success")),
    }
```

- [ ] **Step 4: Run the two new tests**

Run: `pytest tests/test_report.py::test_manifest_path_is_relative tests/test_report.py::test_manifest_replaces_existing_entry_for_same_period -v`
Expected: both PASS.

- [ ] **Step 5: Run full pipeline test suite to confirm no regressions**

Run: `pytest -q`
Expected: green. If any test asserts the old `/data/reports/...` absolute path, update the assertion to the new relative form — there are no callers of `_update_manifest` that depend on the absolute form (it was only consumed by the dashboard, which we update in Phase 2).

- [ ] **Step 6: Commit**

```bash
git add pipeline/report.py tests/test_report.py
git commit -m "feat(pipeline): write relative manifest paths

Dashboard will prepend a base URL (VITE_REPORTS_BASE_URL). Local dev
keeps working because the dashboard resolver still falls back to
/data/reports when the env var is unset."
```

---

### Task 3: blob_upload.py — manifest merge (pure logic, TDD)

**Files:**
- Create: `pipeline/blob_upload.py`
- Test: `tests/test_blob_upload.py`

Pure manifest-merge logic, no Azure SDK in this task. This is the function that fixes the round-2 P0 (single-month overwrite).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_blob_upload.py`:

```python
import pytest

from pipeline.blob_upload import compute_merged_manifest


def _entry(key, start, end, source="api", status="success"):
    return {
        "key": key,
        "label": f"{key} label",
        "start": start,
        "end": end,
        "path": f"month_{start}_{end}/metrics.json",
        "source": source,
        "validation_status": status,
    }


def test_compute_merged_manifest_seeds_empty():
    new = _entry("2026-04", "2026-04-01", "2026-04-30")
    merged = compute_merged_manifest(existing={"reports": []}, new_entry=new)
    assert merged == {"reports": [new]}


def test_compute_merged_manifest_appends_new_period():
    march = _entry("2026-03", "2026-03-01", "2026-03-31")
    april = _entry("2026-04", "2026-04-01", "2026-04-30")
    merged = compute_merged_manifest(existing={"reports": [march]}, new_entry=april)
    # Sorted by start descending: April first, March second
    assert [r["key"] for r in merged["reports"]] == ["2026-04", "2026-03"]


def test_compute_merged_manifest_replaces_same_key():
    april_csv = _entry("2026-04", "2026-04-01", "2026-04-30", source="csv")
    april_api = _entry("2026-04", "2026-04-01", "2026-04-30", source="api")
    merged = compute_merged_manifest(existing={"reports": [april_csv]}, new_entry=april_api)
    assert len(merged["reports"]) == 1
    assert merged["reports"][0]["source"] == "api"


def test_compute_merged_manifest_handles_none_existing():
    new = _entry("2026-04", "2026-04-01", "2026-04-30")
    merged = compute_merged_manifest(existing=None, new_entry=new)
    assert merged == {"reports": [new]}


def test_compute_merged_manifest_tolerates_malformed_existing():
    new = _entry("2026-04", "2026-04-01", "2026-04-30")
    merged = compute_merged_manifest(existing={"reports": "not-a-list"}, new_entry=new)
    assert merged == {"reports": [new]}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_blob_upload.py -v`
Expected: ImportError — `pipeline.blob_upload` does not exist.

- [ ] **Step 3: Create the module with the pure merge function**

Create `pipeline/blob_upload.py`:

```python
from __future__ import annotations

from typing import Any


def compute_merged_manifest(existing: dict[str, Any] | None, new_entry: dict[str, Any]) -> dict[str, Any]:
    reports: list[dict[str, Any]]
    if existing is None:
        reports = []
    else:
        raw = existing.get("reports")
        reports = list(raw) if isinstance(raw, list) else []
    key = new_entry["key"]
    reports = [row for row in reports if not (isinstance(row, dict) and row.get("key") == key)]
    reports.append(new_entry)
    reports.sort(key=lambda row: str(row.get("start", "")), reverse=True)
    return {"reports": reports}
```

- [ ] **Step 4: Run the tests, expect all PASS**

Run: `pytest tests/test_blob_upload.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add pipeline/blob_upload.py tests/test_blob_upload.py
git commit -m "feat(pipeline): pure manifest merge helper for blob uploader

Standalone function so the merge logic is testable without touching the
Azure SDK. ETag CAS retry loop in the next task uses this."
```

---

### Task 4: blob_upload.py — ETag CAS retry + period file upload

**Files:**
- Modify: `pipeline/blob_upload.py`
- Modify: `tests/test_blob_upload.py`

Implements the actual SDK-touching code. We test using a fake `BlobClient` that simulates ETag semantics.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_blob_upload.py`:

```python
import json
from pathlib import Path

from azure.core.exceptions import ResourceModifiedError, ResourceNotFoundError

from pipeline.blob_upload import upload_manifest_with_cas


class FakeManifestBlob:
    """In-memory fake of azure.storage.blob.BlobClient for manifest CAS testing."""

    def __init__(self, initial: bytes | None = None, etag: str = "etag-0"):
        self._body = initial
        self._etag = etag
        self.upload_calls: list[tuple[bytes, str | None]] = []
        self.fail_next_uploads: int = 0  # simulate N consecutive 412s

    def download_blob(self):
        if self._body is None:
            raise ResourceNotFoundError("not found")
        return _FakeDownload(self._body, self._etag)

    def upload_blob(self, data, overwrite=True, etag=None, match_condition=None):
        if self.fail_next_uploads > 0:
            self.fail_next_uploads -= 1
            # Pretend a concurrent writer changed the etag
            self._etag = f"{self._etag}-concurrent"
            raise ResourceModifiedError("If-Match precondition failed")
        body = data if isinstance(data, bytes) else data.encode("utf-8") if isinstance(data, str) else bytes(data)
        self._body = body
        self._etag = f"etag-{len(self.upload_calls) + 1}"
        self.upload_calls.append((body, etag))


class _FakeDownload:
    def __init__(self, body: bytes, etag: str):
        self._body = body
        self.properties = type("Props", (), {"etag": etag})()

    def readall(self) -> bytes:
        return self._body


def _new_entry():
    return {
        "key": "2026-04",
        "label": "April 2026",
        "start": "2026-04-01",
        "end": "2026-04-30",
        "path": "month_2026-04-01_2026-04-30/metrics.json",
        "source": "api",
        "validation_status": "success",
    }


def test_upload_manifest_with_cas_first_writer():
    blob = FakeManifestBlob(initial=None)
    upload_manifest_with_cas(blob, _new_entry())
    assert len(blob.upload_calls) == 1
    body, sent_etag = blob.upload_calls[0]
    payload = json.loads(body)
    assert payload["reports"][0]["key"] == "2026-04"
    # First write uses If-None-Match: * semantics (no etag)
    assert sent_etag is None


def test_upload_manifest_with_cas_merges_existing():
    existing = {"reports": [{
        "key": "2026-03", "label": "March 2026", "start": "2026-03-01", "end": "2026-03-31",
        "path": "month_2026-03-01_2026-03-31/metrics.json", "source": "api",
        "validation_status": "success"
    }]}
    blob = FakeManifestBlob(initial=json.dumps(existing).encode())
    upload_manifest_with_cas(blob, _new_entry())
    body, sent_etag = blob.upload_calls[0]
    payload = json.loads(body)
    keys = [r["key"] for r in payload["reports"]]
    assert keys == ["2026-04", "2026-03"]
    assert sent_etag == "etag-0"


def test_upload_manifest_with_cas_retries_on_412():
    blob = FakeManifestBlob(initial=b'{"reports": []}')
    blob.fail_next_uploads = 2  # Two collisions, third attempt succeeds
    upload_manifest_with_cas(blob, _new_entry(), max_attempts=5)
    assert len(blob.upload_calls) == 1  # Successful upload count
    # We re-downloaded between attempts, so the etag we send escalates each retry
    # (Detailed re-fetch is implicit; just confirm we eventually succeeded.)


def test_upload_manifest_with_cas_gives_up_after_max_attempts():
    blob = FakeManifestBlob(initial=b'{"reports": []}')
    blob.fail_next_uploads = 10  # Always collides
    with pytest.raises(RuntimeError, match="manifest"):
        upload_manifest_with_cas(blob, _new_entry(), max_attempts=3)
```

- [ ] **Step 2: Run the tests, expect ImportError on `upload_manifest_with_cas`**

Run: `pytest tests/test_blob_upload.py -v`
Expected: ImportError for `upload_manifest_with_cas` (other tests still pass).

- [ ] **Step 3: Implement `upload_manifest_with_cas`**

Edit `pipeline/blob_upload.py`, adding:

```python
import json
import logging
import time

from azure.core import MatchConditions
from azure.core.exceptions import ResourceModifiedError, ResourceNotFoundError

log = logging.getLogger(__name__)


def upload_manifest_with_cas(
    blob_client,
    new_entry: dict[str, Any],
    max_attempts: int = 5,
    backoff_seconds: float = 0.5,
) -> None:
    """Upload manifest.json with ETag compare-and-swap.

    Strategy:
    - GET current manifest + etag (404 => empty, no etag).
    - Merge in `new_entry`.
    - PUT with If-Match: <etag>, or If-None-Match: * when no etag.
    - On 412 Precondition Failed (ResourceModifiedError), retry up to max_attempts.
    """
    for attempt in range(1, max_attempts + 1):
        existing, etag = _download_existing(blob_client)
        merged = compute_merged_manifest(existing, new_entry)
        body = json.dumps(merged, indent=2, sort_keys=True).encode("utf-8")
        try:
            if etag is None:
                blob_client.upload_blob(body, overwrite=True, etag=None, match_condition=MatchConditions.IfMissing)
            else:
                blob_client.upload_blob(body, overwrite=True, etag=etag, match_condition=MatchConditions.IfNotModified)
            return
        except ResourceModifiedError:
            log.warning("manifest CAS collision on attempt %d/%d", attempt, max_attempts)
            time.sleep(backoff_seconds * attempt)
    raise RuntimeError(f"failed to update manifest after {max_attempts} attempts")


def _download_existing(blob_client) -> tuple[dict[str, Any] | None, str | None]:
    try:
        download = blob_client.download_blob()
    except ResourceNotFoundError:
        return None, None
    body = download.readall()
    payload = json.loads(body) if body else None
    etag = getattr(getattr(download, "properties", None), "etag", None)
    return payload, etag
```

- [ ] **Step 4: Run the tests**

Run: `pytest tests/test_blob_upload.py -v`
Expected: all PASS.

- [ ] **Step 5: Now add the period-files uploader**

Append to `pipeline/blob_upload.py`:

```python
import os
from pathlib import Path


def upload_period_files(container_client, data_dir: Path, period_dir_name: str) -> int:
    """Upload all files under data_dir/reports/<period_dir_name>/ to the container.

    Uses the directory name as the blob prefix (e.g. 'month_2026-04-01_2026-04-30').
    Returns the number of files uploaded.
    """
    source = Path(data_dir) / "reports" / period_dir_name
    if not source.is_dir():
        raise FileNotFoundError(f"period directory not found: {source}")
    count = 0
    for file in sorted(source.iterdir()):
        if not file.is_file():
            continue
        blob_name = f"{period_dir_name}/{file.name}"
        with file.open("rb") as fh:
            container_client.upload_blob(name=blob_name, data=fh, overwrite=True)
        count += 1
    return count
```

- [ ] **Step 6: Add a test for `upload_period_files`**

Append to `tests/test_blob_upload.py`:

```python
class FakeContainer:
    def __init__(self):
        self.uploads: list[tuple[str, bytes]] = []

    def upload_blob(self, name, data, overwrite=True):
        body = data.read() if hasattr(data, "read") else data
        self.uploads.append((name, body))


def test_upload_period_files_uploads_every_file(tmp_path):
    period = "month_2026-04-01_2026-04-30"
    period_dir = tmp_path / "reports" / period
    period_dir.mkdir(parents=True)
    (period_dir / "metrics.json").write_text('{"a": 1}')
    (period_dir / "metrics_8020.json").write_text('{"b": 2}')
    container = FakeContainer()
    count = upload_period_files(container, tmp_path, period)
    assert count == 2
    names = sorted(name for name, _ in container.uploads)
    assert names == [f"{period}/metrics.json", f"{period}/metrics_8020.json"]


def test_upload_period_files_errors_when_dir_missing(tmp_path):
    container = FakeContainer()
    with pytest.raises(FileNotFoundError):
        upload_period_files(container, tmp_path, "month_2026-04-01_2026-04-30")
```

Also add `from pipeline.blob_upload import upload_period_files` to the top of the test file.

- [ ] **Step 7: Run the tests**

Run: `pytest tests/test_blob_upload.py -v`
Expected: all PASS.

- [ ] **Step 8: Add the top-level `upload_reports` orchestrator**

Append to `pipeline/blob_upload.py`:

```python
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.storage.blob import BlobServiceClient


def upload_reports(data_dir: Path, period_dir_name: str, manifest_entry: dict[str, Any]) -> None:
    """Top-level uploader called by pipeline/azure_run.py after a successful run.

    Reads REPORTS_STORAGE_ACCOUNT_URL and REPORTS_CONTAINER from env. No-op when
    REPORTS_STORAGE_ACCOUNT_URL is unset (local dev / CLI usage).
    """
    account_url = os.environ.get("REPORTS_STORAGE_ACCOUNT_URL")
    if not account_url:
        log.info("REPORTS_STORAGE_ACCOUNT_URL unset; skipping blob upload")
        return
    container_name = os.environ.get("REPORTS_CONTAINER", "reports")
    credential = _build_credential()
    service = BlobServiceClient(account_url=account_url, credential=credential)
    container = service.get_container_client(container_name)

    files_uploaded = upload_period_files(container, data_dir, period_dir_name)
    log.info("uploaded %d period files under %s", files_uploaded, period_dir_name)

    manifest_blob = container.get_blob_client("manifest.json")
    upload_manifest_with_cas(manifest_blob, manifest_entry)
    log.info("manifest.json updated with entry %s", manifest_entry["key"])


def _build_credential():
    """Use ManagedIdentityCredential when AZURE_CLIENT_ID is set (inside Container Apps).

    Falls back to DefaultAzureCredential for local development.
    """
    client_id = os.environ.get("AZURE_CLIENT_ID")
    if client_id:
        return ManagedIdentityCredential(client_id=client_id)
    return DefaultAzureCredential()
```

- [ ] **Step 9: Smoke test `upload_reports` with REPORTS_STORAGE_ACCOUNT_URL unset**

Append to `tests/test_blob_upload.py`:

```python
def test_upload_reports_skips_when_env_unset(tmp_path, monkeypatch):
    monkeypatch.delenv("REPORTS_STORAGE_ACCOUNT_URL", raising=False)
    from pipeline.blob_upload import upload_reports
    # Should not raise even though nothing exists to upload — the no-op path
    upload_reports(tmp_path, "month_2026-04-01_2026-04-30", _new_entry())
```

- [ ] **Step 10: Run the full test file**

Run: `pytest tests/test_blob_upload.py -v`
Expected: all PASS.

- [ ] **Step 11: Commit**

```bash
git add pipeline/blob_upload.py tests/test_blob_upload.py
git commit -m "feat(pipeline): blob uploader with ETag CAS manifest merge

upload_reports() is no-op when REPORTS_STORAGE_ACCOUNT_URL is unset, so
local CLI runs are unaffected. Uses ManagedIdentityCredential when
AZURE_CLIENT_ID is set (the Container Apps case); otherwise
DefaultAzureCredential for local az-login auth."
```

---

### Task 5: azure_run.py — period resolution (pure logic, TDD)

**Files:**
- Create: `pipeline/azure_run.py`
- Create: `tests/test_azure_run.py`

The wrapper entrypoint. Tests target the pure period-resolution logic in this task; the integration with `run_api`/`run_csv` and blob upload comes in Task 6.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_azure_run.py`:

```python
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from pipeline.azure_run import resolve_period


def test_resolve_period_previous_month_from_toronto_perspective():
    # 2026-05-11 in Toronto -> previous month is April 2026
    now = datetime(2026, 5, 11, 14, 30, tzinfo=ZoneInfo("America/Toronto"))
    start, end = resolve_period(mode="previous-month", timezone="America/Toronto", now=now)
    assert start == "2026-04-01"
    assert end == "2026-04-30"


def test_resolve_period_previous_month_handles_january_boundary():
    # 2026-01-05 -> previous month is December 2025
    now = datetime(2026, 1, 5, 12, 0, tzinfo=ZoneInfo("America/Toronto"))
    start, end = resolve_period(mode="previous-month", timezone="America/Toronto", now=now)
    assert start == "2025-12-01"
    assert end == "2025-12-31"


def test_resolve_period_previous_month_handles_february_leap_year():
    # 2024 is a leap year; 2024-03-15 -> previous month is February 2024 with 29 days
    now = datetime(2024, 3, 15, 12, 0, tzinfo=ZoneInfo("America/Toronto"))
    start, end = resolve_period(mode="previous-month", timezone="America/Toronto", now=now)
    assert start == "2024-02-01"
    assert end == "2024-02-29"


def test_resolve_period_previous_month_runs_at_03_utc_on_first_uses_correct_local_month():
    # Cron fires 09:00 UTC on the 1st = 04:00/05:00 in Toronto. Same calendar day there.
    now = datetime(2026, 5, 1, 9, 0, tzinfo=ZoneInfo("UTC"))
    start, end = resolve_period(mode="previous-month", timezone="America/Toronto", now=now)
    assert start == "2026-04-01"
    assert end == "2026-04-30"


def test_resolve_period_explicit_passes_through():
    start, end = resolve_period(mode="explicit", explicit_start="2025-11-01", explicit_end="2025-11-30")
    assert start == "2025-11-01"
    assert end == "2025-11-30"


def test_resolve_period_explicit_requires_both_dates():
    with pytest.raises(ValueError, match="PERIOD_START"):
        resolve_period(mode="explicit", explicit_start=None, explicit_end="2025-11-30")
    with pytest.raises(ValueError, match="PERIOD_END"):
        resolve_period(mode="explicit", explicit_start="2025-11-01", explicit_end=None)


def test_resolve_period_unknown_mode_raises():
    with pytest.raises(ValueError, match="PERIOD_MODE"):
        resolve_period(mode="bogus")
```

- [ ] **Step 2: Run the tests; expect ImportError**

Run: `pytest tests/test_azure_run.py -v`
Expected: ImportError — module does not exist.

- [ ] **Step 3: Create the module with `resolve_period`**

Create `pipeline/azure_run.py`:

```python
from __future__ import annotations

import calendar
from datetime import datetime
from zoneinfo import ZoneInfo


def resolve_period(
    mode: str,
    *,
    timezone: str = "America/Toronto",
    now: datetime | None = None,
    explicit_start: str | None = None,
    explicit_end: str | None = None,
) -> tuple[str, str]:
    """Return (start, end) ISO-date strings for the requested period.

    mode="previous-month": calendar month that ended before `now` in `timezone`.
    mode="explicit": pass-through of explicit_start / explicit_end.
    """
    if mode == "previous-month":
        tz = ZoneInfo(timezone)
        anchor = (now or datetime.now(tz)).astimezone(tz)
        # First day of current local month
        first_of_this = anchor.replace(day=1)
        # Last day of previous month = day before first_of_this
        last_of_prev = (first_of_this.replace(hour=0, minute=0, second=0, microsecond=0) - _one_day())
        year = last_of_prev.year
        month = last_of_prev.month
        last_day = calendar.monthrange(year, month)[1]
        start = f"{year:04d}-{month:02d}-01"
        end = f"{year:04d}-{month:02d}-{last_day:02d}"
        return start, end

    if mode == "explicit":
        if not explicit_start:
            raise ValueError("PERIOD_START is required when PERIOD_MODE=explicit")
        if not explicit_end:
            raise ValueError("PERIOD_END is required when PERIOD_MODE=explicit")
        return explicit_start, explicit_end

    raise ValueError(f"PERIOD_MODE must be 'previous-month' or 'explicit', got: {mode!r}")


def _one_day():
    from datetime import timedelta
    return timedelta(days=1)
```

- [ ] **Step 4: Run the tests; expect all PASS**

Run: `pytest tests/test_azure_run.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add pipeline/azure_run.py tests/test_azure_run.py
git commit -m "feat(pipeline): azure_run.resolve_period — TZ-aware previous-month + explicit"
```

---

### Task 6: azure_run.py — orchestration (run + upload)

**Files:**
- Modify: `pipeline/azure_run.py`
- Modify: `tests/test_azure_run.py`

Wire `resolve_period` to the existing `run_api`/`run_csv` and the new `upload_reports`. No code changes to `pipeline/main.py` — `azure_run.py` calls into `run_api`/`run_csv` directly.

- [ ] **Step 1: Write the failing test for the integration `main()` entrypoint**

Append to `tests/test_azure_run.py`:

```python
import os
from unittest.mock import patch


def test_main_explicit_mode_invokes_run_api_then_upload(monkeypatch, tmp_path):
    monkeypatch.setenv("PERIOD_MODE", "explicit")
    monkeypatch.setenv("PERIOD_TYPE", "month")
    monkeypatch.setenv("PERIOD_START", "2026-04-01")
    monkeypatch.setenv("PERIOD_END", "2026-04-30")
    monkeypatch.setenv("API_CACHE_MODE", "auto")
    monkeypatch.setenv("WRITE_STORE", "1")
    monkeypatch.setenv("SOURCE", "api")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("MOTHERDUCK_TOKEN_RW", "fake-token")
    monkeypatch.delenv("REPORTS_STORAGE_ACCOUNT_URL", raising=False)

    calls: list[str] = []
    with patch("pipeline.azure_run.run_api") as mock_run_api, \
         patch("pipeline.azure_run.upload_reports") as mock_upload, \
         patch("pipeline.azure_run._acquire_period_lease") as mock_lease:
        mock_lease.return_value.__enter__ = lambda self: None
        mock_lease.return_value.__exit__ = lambda self, *a: None
        mock_run_api.side_effect = lambda *a, **kw: calls.append("run_api") or tmp_path
        mock_upload.side_effect = lambda *a, **kw: calls.append("upload")

        from pipeline.azure_run import main
        rc = main()

    assert rc == 0
    assert calls == ["run_api", "upload"]
    mock_run_api.assert_called_once()
    # Verify dates threaded through
    kwargs = mock_run_api.call_args.kwargs
    assert kwargs.get("start") == "2026-04-01"
    assert kwargs.get("end") == "2026-04-30"


def test_main_skips_upload_when_run_api_raises(monkeypatch, tmp_path):
    monkeypatch.setenv("PERIOD_MODE", "explicit")
    monkeypatch.setenv("PERIOD_TYPE", "month")
    monkeypatch.setenv("PERIOD_START", "2026-04-01")
    monkeypatch.setenv("PERIOD_END", "2026-04-30")
    monkeypatch.setenv("SOURCE", "api")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("MOTHERDUCK_TOKEN_RW", "fake-token")
    monkeypatch.setenv("WRITE_STORE", "1")

    with patch("pipeline.azure_run.run_api") as mock_run_api, \
         patch("pipeline.azure_run.upload_reports") as mock_upload, \
         patch("pipeline.azure_run._acquire_period_lease") as mock_lease:
        mock_lease.return_value.__enter__ = lambda self: None
        mock_lease.return_value.__exit__ = lambda self, *a: None
        mock_run_api.side_effect = RuntimeError("API blew up")

        from pipeline.azure_run import main
        with pytest.raises(RuntimeError, match="API blew up"):
            main()

    mock_upload.assert_not_called()
```

- [ ] **Step 2: Run the new tests; they should fail (no `main`)**

Run: `pytest tests/test_azure_run.py::test_main_explicit_mode_invokes_run_api_then_upload tests/test_azure_run.py::test_main_skips_upload_when_run_api_raises -v`
Expected: ImportError on `main`.

- [ ] **Step 3: Implement `main()` and the lease helper**

Append to `pipeline/azure_run.py`:

```python
import logging
import os
from contextlib import contextmanager
from pathlib import Path

from pipeline.blob_upload import upload_reports
from pipeline.config import AppConfig
from pipeline.main import build_versature_client_from_env, run_api, run_csv
from pipeline.storage import AnalyticsStore
from pipeline.report import _month_label

log = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    mode = os.environ.get("PERIOD_MODE", "previous-month")
    period_type = os.environ.get("PERIOD_TYPE", "month")
    source = os.environ.get("SOURCE", "api")
    api_cache_mode = os.environ.get("API_CACHE_MODE", "auto")
    write_store = os.environ.get("WRITE_STORE", "1") == "1"

    config = AppConfig.from_env()
    start, end = resolve_period(
        mode=mode,
        timezone=config.timezone,
        explicit_start=os.environ.get("PERIOD_START"),
        explicit_end=os.environ.get("PERIOD_END"),
    )
    log.info("resolved period: mode=%s type=%s start=%s end=%s", mode, period_type, start, end)

    period_dir_name = f"{period_type}_{start}_{end}"
    manifest_entry = {
        "key": start[:7],
        "label": _month_label(start),
        "start": start,
        "end": end,
        "path": f"{period_dir_name}/metrics.json",
        "source": source,
        "validation_status": "success",
    }

    store = None
    if write_store:
        if not os.environ.get("MOTHERDUCK_TOKEN_RW"):
            raise SystemExit("MOTHERDUCK_TOKEN_RW is required when WRITE_STORE=1")
        store = AnalyticsStore.motherduck(config.motherduck_database)

    with _acquire_period_lease(period_dir_name):
        if source == "api":
            run_api(
                config,
                period_type,
                start,
                end,
                store=store,
                client=build_versature_client_from_env(),
                api_cache_mode=api_cache_mode,
            )
        elif source == "csv":
            run_csv(config, period_type, start, end, store=store)
        else:
            raise SystemExit(f"SOURCE must be 'api' or 'csv', got: {source!r}")

        upload_reports(Path(config.data_dir), period_dir_name, manifest_entry)
    return 0


@contextmanager
def _acquire_period_lease(period_dir_name: str):
    """Acquire a blob lease on .locks/<period_dir_name>.lock to serialize concurrent runs.

    No-op when REPORTS_STORAGE_ACCOUNT_URL is unset (local dev).
    """
    account_url = os.environ.get("REPORTS_STORAGE_ACCOUNT_URL")
    if not account_url:
        yield
        return

    from azure.storage.blob import BlobServiceClient
    from pipeline.blob_upload import _build_credential

    container_name = os.environ.get("REPORTS_CONTAINER", "reports")
    service = BlobServiceClient(account_url=account_url, credential=_build_credential())
    blob = service.get_blob_client(container=container_name, blob=f".locks/{period_dir_name}.lock")
    # Ensure placeholder exists
    try:
        blob.upload_blob(b"", overwrite=False)
    except Exception:
        pass  # already exists
    lease = blob.acquire_lease(lease_duration=60)
    try:
        yield
    finally:
        try:
            lease.release()
        except Exception:
            log.warning("failed to release lease on %s", period_dir_name)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests; expect PASS**

Run: `pytest tests/test_azure_run.py -v`
Expected: all PASS.

- [ ] **Step 5: Run full pipeline test suite**

Run: `pytest -q`
Expected: green.

- [ ] **Step 6: Smoke-run the entrypoint locally with explicit dates (no upload, no MD)**

Run:
```bash
DATA_DIR=/tmp/azure-run-smoke \
PERIOD_MODE=explicit PERIOD_TYPE=month PERIOD_START=2026-04-01 PERIOD_END=2026-04-30 \
SOURCE=csv WRITE_STORE=0 \
CSV_DIR=./data/csv-uploads \
python -m pipeline.azure_run || true
```

Expected: either succeeds (if CSVs are present) or fails with the same "Missing required queue CSVs" message that `python -m pipeline.main` produces in the same scenario — confirming the wrapper threads through correctly. Either way, no `REPORTS_STORAGE_ACCOUNT_URL` = no upload attempt.

- [ ] **Step 7: Commit**

```bash
git add pipeline/azure_run.py tests/test_azure_run.py
git commit -m "feat(pipeline): azure_run entrypoint — period resolution, lease, run, upload

Thin wrapper used by the container ENTRYPOINT. Reads env vars set by
Bicep on the Container Apps Job. Upload only happens after run_api or
run_csv returns successfully, so MotherDuck-write failures abort
before any blob is touched. Lease + upload are both no-ops when
REPORTS_STORAGE_ACCOUNT_URL is unset, so local CLI usage is
unaffected."
```

---

## Phase 2: Dashboard code (TDD, no Azure)

### Task 7: Base URL resolver in `reportManifest.ts` and `reportLoader.ts`

**Files:**
- Modify: `dashboard/src/data/reportManifest.ts`
- Modify: `dashboard/src/data/reportLoader.ts`
- Modify: `dashboard/src/data/reportManifest.test.ts`
- Modify: `dashboard/src/data/reportLoader.test.ts`

- [ ] **Step 1: Write failing tests for base-URL resolution**

Append to `dashboard/src/data/reportManifest.test.ts`:

```ts
import { resolveReportsBaseUrl } from "./reportManifest";

describe("resolveReportsBaseUrl", () => {
  it("uses VITE_REPORTS_BASE_URL when set, stripping trailing slash", () => {
    expect(resolveReportsBaseUrl({ VITE_REPORTS_BASE_URL: "https://x.blob.core.windows.net/reports/" }))
      .toBe("https://x.blob.core.windows.net/reports");
  });

  it("falls back to /data/reports when env var is unset", () => {
    expect(resolveReportsBaseUrl({})).toBe("/data/reports");
  });
});

describe("manifest entries with relative paths", () => {
  it("prepends the base URL to relative paths from manifest", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        json: async () => ({
          reports: [{
            key: "2026-04",
            label: "April 2026",
            start: "2026-04-01",
            end: "2026-04-30",
            path: "month_2026-04-01_2026-04-30/metrics.json",
            source: "api",
          }],
        }),
      })),
    );
    const options = await loadReportManifest(undefined, { VITE_REPORTS_BASE_URL: "https://x/reports" });
    expect(options[0].path).toBe("https://x/reports/month_2026-04-01_2026-04-30/metrics.json");
    vi.unstubAllGlobals();
  });

  it("leaves absolute paths in manifest entries unchanged (backward compatibility)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        json: async () => ({
          reports: [{
            key: "2026-03",
            label: "March 2026",
            start: "2026-03-01",
            end: "2026-03-31",
            path: "/data/reports/month_2026-03-01_2026-03-31/metrics.json",
            source: "api",
          }],
        }),
      })),
    );
    const options = await loadReportManifest(undefined, { VITE_REPORTS_BASE_URL: "https://x/reports" });
    expect(options[0].path).toBe("/data/reports/month_2026-03-01_2026-03-31/metrics.json");
    vi.unstubAllGlobals();
  });
});
```

- [ ] **Step 2: Run the dashboard tests; expect import failure**

Run: `cd dashboard && npm test -- --run`
Expected: `resolveReportsBaseUrl` is not exported.

- [ ] **Step 3: Rewrite `reportManifest.ts`**

Replace `dashboard/src/data/reportManifest.ts` with:

```ts
import { DEFAULT_REPORT_PATH } from "./reportLoader";

export interface ReportOption {
  key: string;
  label: string;
  start: string;
  end: string;
  path: string;
  source: string;
}

interface ManifestPayload {
  reports?: unknown;
}

interface ImportMetaEnvLike {
  VITE_REPORTS_BASE_URL?: string;
  VITE_ENABLE_FIXTURE_FALLBACK?: string;
  DEV?: boolean;
}

export function resolveReportsBaseUrl(env: ImportMetaEnvLike = import.meta.env as ImportMetaEnvLike): string {
  const raw = env.VITE_REPORTS_BASE_URL;
  if (typeof raw === "string" && raw.length > 0) {
    return raw.replace(/\/+$/, "");
  }
  return "/data/reports";
}

export const MANIFEST_PATH = `${resolveReportsBaseUrl()}/manifest.json`;

export const DEFAULT_REPORT_OPTION: ReportOption = {
  key: "2026-04",
  label: "April 2026",
  start: "2026-04-01",
  end: "2026-04-30",
  path: DEFAULT_REPORT_PATH,
  source: "excel_reference_overlay",
};

export function buildReportPath(start: string, end: string, env?: ImportMetaEnvLike): string {
  const base = resolveReportsBaseUrl(env);
  return `${base}/month_${start}_${end}/metrics.json`;
}

export async function loadReportManifest(
  path?: string,
  env: ImportMetaEnvLike = import.meta.env as ImportMetaEnvLike,
): Promise<ReportOption[]> {
  const resolvedPath = path ?? `${resolveReportsBaseUrl(env)}/manifest.json`;
  const allowFixture = env.DEV === true || env.VITE_ENABLE_FIXTURE_FALLBACK === "true";
  try {
    if (typeof fetch !== "function") {
      throw new Error("Fetch is not available in this environment.");
    }
    const response = await fetch(resolvedPath, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Manifest request failed with HTTP ${response.status}.`);
    }
    const payload = (await response.json()) as ManifestPayload;
    const reports = Array.isArray(payload.reports) ? payload.reports : [];
    const base = resolveReportsBaseUrl(env);
    const options = reports.map((r) => normalizeReportOption(r, base));
    if (options.length === 0) {
      if (allowFixture) return [DEFAULT_REPORT_OPTION];
      throw new Error("Manifest has no entries.");
    }
    return sortReportOptions(options);
  } catch (err) {
    if (allowFixture) return [DEFAULT_REPORT_OPTION];
    throw err;
  }
}

export function sortReportOptions(options: ReportOption[]): ReportOption[] {
  return [...options].sort((a, b) => b.start.localeCompare(a.start));
}

function normalizeReportOption(value: unknown, base: string): ReportOption {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error("Report manifest entry must be an object.");
  }
  const record = value as Record<string, unknown>;
  const rawPath = requireString(record.path, "path");
  const resolvedPath = isAbsolute(rawPath) ? rawPath : `${base}/${rawPath}`;
  return {
    key: requireString(record.key, "key"),
    label: requireString(record.label, "label"),
    start: requireString(record.start, "start"),
    end: requireString(record.end, "end"),
    path: resolvedPath,
    source: requireString(record.source, "source"),
  };
}

function isAbsolute(path: string): boolean {
  return path.startsWith("/") || /^https?:\/\//.test(path);
}

function requireString(value: unknown, field: string): string {
  if (typeof value !== "string" || value.length === 0) {
    throw new Error(`Report manifest ${field} must be a string.`);
  }
  return value;
}
```

- [ ] **Step 4: Run the dashboard tests; expect PASS**

Run: `cd dashboard && npm test -- --run`
Expected: green. Existing tests pass because:
- `buildReportPath("2026-03-01", "2026-03-31")` with no env returns `/data/reports/month_..../metrics.json` (same as before).
- Existing `loadReportManifest` test passes because the absolute path in its mock is preserved by `normalizeReportOption`.

If the old `loadReportManifest` test fails because of the no-entries vs. empty-list semantics, update it: with the new code, an empty manifest in dev mode returns `[DEFAULT_REPORT_OPTION]` and in prod mode throws. The old test stubbed a single-entry response and expected one option — still passes.

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/data/reportManifest.ts dashboard/src/data/reportManifest.test.ts
git commit -m "feat(dashboard): VITE_REPORTS_BASE_URL resolver + fixture fallback gating

Manifest entries with relative paths get the base URL prepended.
Absolute paths (legacy / local-dev manifests) pass through unchanged.
DEFAULT_REPORT_OPTION fixture only kicks in when DEV=true or
VITE_ENABLE_FIXTURE_FALLBACK=true — production builds surface the
manifest error instead of silently substituting April 2026 data."
```

---

### Task 8: `reportLoader.ts` — base URL + fixture gate

**Files:**
- Modify: `dashboard/src/data/reportLoader.ts`
- Modify: `dashboard/src/data/reportLoader.test.ts`

- [ ] **Step 1: Write failing tests**

Append to `dashboard/src/data/reportLoader.test.ts`:

```ts
import { loadReport } from "./reportLoader";

describe("loadReport with fixture fallback gate", () => {
  it("returns error status in production when fetch fails (no fixture)", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: false, status: 500 })));
    const result = await loadReport({ path: "https://x/foo.json", env: { DEV: false } });
    expect(result.status).toBe("error");
    vi.unstubAllGlobals();
  });

  it("returns fixture in dev when fetch fails", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: false, status: 500 })));
    const result = await loadReport({ path: "https://x/foo.json", env: { DEV: true } });
    expect(result.status).toBe("loaded");
    expect(result.source).toBe("fixture");
    vi.unstubAllGlobals();
  });
});
```

- [ ] **Step 2: Replace `reportLoader.ts`**

Edit `dashboard/src/data/reportLoader.ts`:

```ts
import fixtureReport from "../fixtures/april-2026-metrics.json";
import type { DashboardReport, QueueId, ReportLoadResult } from "./reportTypes";
import { QUEUE_ORDER } from "./reportTypes";

interface ImportMetaEnvLike {
  VITE_REPORTS_BASE_URL?: string;
  VITE_ENABLE_FIXTURE_FALLBACK?: string;
  DEV?: boolean;
}

function resolveBase(env: ImportMetaEnvLike = import.meta.env as ImportMetaEnvLike): string {
  const raw = env.VITE_REPORTS_BASE_URL;
  if (typeof raw === "string" && raw.length > 0) return raw.replace(/\/+$/, "");
  return "/data/reports";
}

export const DEFAULT_REPORT_PATH = `${resolveBase()}/month_2026-04-01_2026-04-30/metrics.json`;

export class ReportValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ReportValidationError";
  }
}

// (Keep validateReport, requireRecord, requireString, requireNumber, requireArray, isQueueId from the original — unchanged.)

export async function loadReport(options?: {
  path?: string;
  useFixtureFallback?: boolean;
  env?: ImportMetaEnvLike;
}): Promise<ReportLoadResult> {
  const env = options?.env ?? (import.meta.env as ImportMetaEnvLike);
  const path = options?.path ?? DEFAULT_REPORT_PATH;
  const allowFixture = env.DEV === true || env.VITE_ENABLE_FIXTURE_FALLBACK === "true";
  const useFixtureFallback = options?.useFixtureFallback ?? allowFixture;

  try {
    if (typeof fetch !== "function") {
      throw new Error("Fetch is not available in this environment.");
    }
    const response = await fetch(path, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Report request failed with HTTP ${response.status}.`);
    }
    const json = await response.json();
    return {
      status: "loaded",
      source: "remote",
      path,
      report: validateReport(json),
    };
  } catch (error) {
    if (useFixtureFallback) {
      return {
        status: "loaded",
        source: "fixture",
        path,
        report: validateReport(fixtureReport),
        warning: error instanceof Error ? error.message : "Report fetch failed.",
      };
    }
    return {
      status: "error",
      source: "remote",
      path,
      error: error instanceof Error ? error.message : "Report fetch failed.",
    };
  }
}

// (Keep validateReport and helper functions exactly as they were in the original file.)
```

Keep all the original validation helpers (`validateReport`, `requireRecord`, `requireString`, `requireNumber`, `requireArray`, `isQueueId`) verbatim from the existing file. Only the `DEFAULT_REPORT_PATH` line, the `ImportMetaEnvLike` interface, the `resolveBase` helper, and the `loadReport` signature change.

- [ ] **Step 3: Run tests**

Run: `cd dashboard && npm test -- --run`
Expected: green.

- [ ] **Step 4: Commit**

```bash
git add dashboard/src/data/reportLoader.ts dashboard/src/data/reportLoader.test.ts
git commit -m "feat(dashboard): gate report fixture fallback on DEV / explicit opt-in

In production, a fetch failure now returns status='error' so the UI
shows an error state instead of silently rendering the bundled April
2026 fixture."
```

---

### Task 9: robots.txt and noindex meta

**Files:**
- Create: `dashboard/public/robots.txt`
- Modify: `dashboard/index.html`

- [ ] **Step 1: Create `dashboard/public/robots.txt`**

Write:

```
User-agent: *
Disallow: /
```

- [ ] **Step 2: Add noindex meta to `dashboard/index.html`**

Find the `<head>` section in `dashboard/index.html` and add this line right after the existing `<meta charset="UTF-8">`:

```html
    <meta name="robots" content="noindex,nofollow" />
```

- [ ] **Step 3: Verify the dev server still serves both**

Run: `cd dashboard && npm run dev &`
Then: `curl -s http://127.0.0.1:5173/robots.txt`
Expected: `User-agent: *\nDisallow: /`
Then: `curl -s http://127.0.0.1:5173/ | grep noindex`
Expected: the meta tag is present.
Then: `kill %1` to stop the dev server.

- [ ] **Step 4: Commit**

```bash
git add dashboard/public/robots.txt dashboard/index.html
git commit -m "feat(dashboard): robots.txt + noindex meta to reduce search-engine discovery"
```

---

## Phase 3: Function code (TDD, no Azure)

### Task 10: Function scaffolding

**Files:**
- Create: `functions/host.json`
- Create: `functions/requirements.txt`
- Create: `functions/run-pipeline/function.json`
- Create: `functions/run-pipeline/__init__.py` (skeleton; logic in Task 11)
- Create: `functions/tests/conftest.py`

- [ ] **Step 1: Create `functions/host.json`**

```json
{
  "version": "2.0",
  "logging": {
    "applicationInsights": {
      "samplingSettings": {
        "isEnabled": true,
        "excludedTypes": "Request"
      }
    }
  },
  "extensionBundle": {
    "id": "Microsoft.Azure.Functions.ExtensionBundle",
    "version": "[4.*, 5.0.0)"
  }
}
```

- [ ] **Step 2: Create `functions/requirements.txt`**

```
azure-functions>=1.20
azure-identity>=1.16
httpx>=0.27
```

- [ ] **Step 3: Create `functions/run-pipeline/function.json`**

```json
{
  "scriptFile": "__init__.py",
  "bindings": [
    {
      "authLevel": "anonymous",
      "type": "httpTrigger",
      "direction": "in",
      "name": "req",
      "methods": ["post"],
      "route": "run-pipeline"
    },
    {
      "type": "http",
      "direction": "out",
      "name": "$return"
    }
  ]
}
```

Authentication is application-layer (admin key in header), not platform-level — the platform-level `function` auth would force the caller to know the platform function key, which is rotatable but stored alongside infra rather than in Key Vault. We do app-level auth and gate on the Key Vault-backed admin key.

- [ ] **Step 4: Create a stub `__init__.py`**

```python
import azure.functions as func


def main(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse("not implemented", status_code=501)
```

- [ ] **Step 5: Create test conftest**

Create `functions/tests/conftest.py`:

```python
import sys
from pathlib import Path

# Make 'functions/run-pipeline' importable as a package-relative path for tests.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "run-pipeline"))
```

- [ ] **Step 6: Commit**

```bash
git add functions/
git commit -m "feat(function): scaffolding for run-pipeline HTTP trigger"
```

---

### Task 11: Function — payload validation + admin key

**Files:**
- Modify: `functions/run-pipeline/__init__.py`
- Create: `functions/tests/test_run_pipeline.py`

- [ ] **Step 1: Write failing tests for the pure validator**

Create `functions/tests/test_run_pipeline.py`:

```python
import json
from datetime import date, timedelta

import pytest

import importlib.util
import sys
from pathlib import Path

# Load the run-pipeline module by absolute path (hyphenated dir name)
_module_path = Path(__file__).resolve().parents[1] / "run-pipeline" / "__init__.py"
spec = importlib.util.spec_from_file_location("run_pipeline_main", _module_path)
run_pipeline_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_pipeline_main)


parse_and_validate = run_pipeline_main.parse_and_validate


def test_parse_and_validate_accepts_valid_month_request():
    body = {"period": "month", "start": "2026-04-01", "end": "2026-04-30", "api_cache_mode": "auto"}
    result = parse_and_validate(body, now=date(2026, 5, 11))
    assert result.start == "2026-04-01"
    assert result.end == "2026-04-30"
    assert result.api_cache_mode == "auto"
    assert result.period == "month"


def test_parse_and_validate_rejects_non_month_period():
    body = {"period": "day", "start": "2026-04-01", "end": "2026-04-01"}
    with pytest.raises(ValueError, match="month"):
        parse_and_validate(body, now=date(2026, 5, 11))


def test_parse_and_validate_rejects_future_end_date():
    body = {"period": "month", "start": "2026-06-01", "end": "2026-06-30"}
    with pytest.raises(ValueError, match="future"):
        parse_and_validate(body, now=date(2026, 5, 11))


def test_parse_and_validate_rejects_window_over_92_days():
    body = {"period": "month", "start": "2025-01-01", "end": "2025-05-01"}
    with pytest.raises(ValueError, match="92"):
        parse_and_validate(body, now=date(2026, 5, 11))


def test_parse_and_validate_rejects_bad_api_cache_mode():
    body = {"period": "month", "start": "2026-04-01", "end": "2026-04-30", "api_cache_mode": "bogus"}
    with pytest.raises(ValueError, match="api_cache_mode"):
        parse_and_validate(body, now=date(2026, 5, 11))


def test_parse_and_validate_defaults_period_to_month_and_cache_to_auto():
    body = {"start": "2026-04-01", "end": "2026-04-30"}
    result = parse_and_validate(body, now=date(2026, 5, 11))
    assert result.period == "month"
    assert result.api_cache_mode == "auto"


def test_parse_and_validate_rejects_inverted_dates():
    body = {"period": "month", "start": "2026-04-30", "end": "2026-04-01"}
    with pytest.raises(ValueError, match="start <= end"):
        parse_and_validate(body, now=date(2026, 5, 11))
```

- [ ] **Step 2: Implement `parse_and_validate` in `__init__.py`**

Replace `functions/run-pipeline/__init__.py` with:

```python
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import date

import azure.functions as func

log = logging.getLogger(__name__)


@dataclass
class ValidatedRequest:
    period: str
    start: str
    end: str
    api_cache_mode: str


def parse_and_validate(body: dict, now: date | None = None) -> ValidatedRequest:
    now = now or date.today()
    period = body.get("period", "month")
    if period != "month":
        raise ValueError(f"period must be 'month' in v1 (got {period!r})")
    api_cache_mode = body.get("api_cache_mode", "auto")
    if api_cache_mode not in {"auto", "refresh", "reuse"}:
        raise ValueError(f"api_cache_mode must be auto|refresh|reuse (got {api_cache_mode!r})")
    start_str = body.get("start")
    end_str = body.get("end")
    try:
        start = date.fromisoformat(start_str)
        end = date.fromisoformat(end_str)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"start and end must be ISO YYYY-MM-DD dates: {exc}") from exc
    if start > end:
        raise ValueError("start <= end is required")
    if end > now:
        raise ValueError("end must not be in the future")
    if (end - start).days > 92:
        raise ValueError("window exceeds 92 days")
    return ValidatedRequest(period=period, start=start_str, end=end_str, api_cache_mode=api_cache_mode)


def main(req: func.HttpRequest) -> func.HttpResponse:
    expected_key = os.environ.get("ADMIN_API_KEY")
    provided_key = req.headers.get("x-admin-key")
    if not expected_key or not provided_key or provided_key != expected_key:
        log.info("admin key mismatch from %s", req.headers.get("x-forwarded-for", "?"))
        return func.HttpResponse("unauthorized", status_code=401)
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse("body must be JSON", status_code=400)
    try:
        validated = parse_and_validate(body)
    except ValueError as exc:
        return func.HttpResponse(str(exc), status_code=400)
    log.info(
        "validated request: period=%s start=%s end=%s cache=%s",
        validated.period, validated.start, validated.end, validated.api_cache_mode,
    )
    # Job-start logic added in Task 12.
    return func.HttpResponse(
        json.dumps({"execution_name": "stub-not-yet-implemented"}),
        status_code=501,
        mimetype="application/json",
    )
```

- [ ] **Step 3: Install Function-side deps in a separate venv**

Run:
```bash
python3 -m venv functions/.venv
functions/.venv/bin/pip install -r functions/requirements.txt pytest
```

Expected: installs cleanly.

- [ ] **Step 4: Run the Function tests**

Run: `functions/.venv/bin/pytest functions/tests -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add functions/run-pipeline/__init__.py functions/tests/test_run_pipeline.py
git commit -m "feat(function): admin-key auth + payload validation

period restricted to 'month' in v1 (day/week reports would not surface
to the dashboard). Max 92-day window. End not in future. ISO date
parsing."
```

---

### Task 12: Function — GET-mutate-POST job start

**Files:**
- Modify: `functions/run-pipeline/__init__.py`
- Modify: `functions/tests/test_run_pipeline.py`

- [ ] **Step 1: Write failing tests for `mutate_template`**

Append to `functions/tests/test_run_pipeline.py`:

```python
mutate_template = run_pipeline_main.mutate_template
build_job_urls = run_pipeline_main.build_job_urls


def test_mutate_template_overwrites_period_env_vars():
    fetched = {
        "containers": [{
            "name": "pipeline",
            "image": "acr.io/pipeline:abc",
            "command": ["python", "-m", "pipeline.azure_run"],
            "env": [
                {"name": "PERIOD_MODE", "value": "previous-month"},
                {"name": "PERIOD_TYPE", "value": "month"},
                {"name": "API_CACHE_MODE", "value": "auto"},
                {"name": "DATA_DIR", "value": "/data"},
            ],
        }],
        "initContainers": [],
    }
    overrides = {
        "PERIOD_MODE": "explicit",
        "PERIOD_TYPE": "month",
        "PERIOD_START": "2026-04-01",
        "PERIOD_END": "2026-04-30",
        "API_CACHE_MODE": "refresh",
    }
    mutated = mutate_template(fetched, overrides)
    env = {item["name"]: item["value"] for item in mutated["containers"][0]["env"]}
    assert env["PERIOD_MODE"] == "explicit"
    assert env["PERIOD_START"] == "2026-04-01"
    assert env["PERIOD_END"] == "2026-04-30"
    assert env["API_CACHE_MODE"] == "refresh"
    assert env["DATA_DIR"] == "/data"  # preserved


def test_mutate_template_preserves_other_container_fields():
    fetched = {
        "containers": [{
            "name": "pipeline",
            "image": "acr.io/pipeline:abc",
            "command": ["python", "-m", "pipeline.azure_run"],
            "resources": {"cpu": 1.0, "memory": "2Gi"},
            "env": [{"name": "FOO", "value": "bar"}],
        }],
        "initContainers": [{"name": "init", "image": "init:1"}],
    }
    mutated = mutate_template(fetched, {"PERIOD_MODE": "explicit"})
    assert mutated["containers"][0]["image"] == "acr.io/pipeline:abc"
    assert mutated["containers"][0]["resources"] == {"cpu": 1.0, "memory": "2Gi"}
    assert mutated["initContainers"] == [{"name": "init", "image": "init:1"}]


def test_build_job_urls_constructs_arm_paths():
    urls = build_job_urls(
        subscription_id="11111111-1111-1111-1111-111111111111",
        resource_group="rg-x",
        job_name="my-job",
    )
    assert urls.get_template.endswith(
        "/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/rg-x/providers/Microsoft.App/jobs/my-job?api-version=2024-03-01"
    )
    assert urls.start.endswith(
        "/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/rg-x/providers/Microsoft.App/jobs/my-job/start?api-version=2024-03-01"
    )
```

- [ ] **Step 2: Implement `mutate_template` and `build_job_urls`**

Append to `functions/run-pipeline/__init__.py`:

```python
from dataclasses import dataclass

import httpx


@dataclass
class JobUrls:
    get_template: str
    start: str


ARM_BASE = "https://management.azure.com"
API_VERSION = "2024-03-01"


def build_job_urls(subscription_id: str, resource_group: str, job_name: str) -> JobUrls:
    base = (
        f"{ARM_BASE}/subscriptions/{subscription_id}/resourceGroups/{resource_group}"
        f"/providers/Microsoft.App/jobs/{job_name}"
    )
    return JobUrls(
        get_template=f"{base}?api-version={API_VERSION}",
        start=f"{base}/start?api-version={API_VERSION}",
    )


def mutate_template(template: dict, env_overrides: dict[str, str]) -> dict:
    """Return a new JobExecutionTemplate dict with env_overrides applied to the single container.

    Preserves image, command, resources, secrets, init containers, all other env vars.
    """
    out = json.loads(json.dumps(template))  # deep copy
    containers = out.get("containers") or []
    if not containers:
        raise ValueError("template has no containers")
    container = containers[0]
    env = container.get("env") or []
    by_name = {item["name"]: dict(item) for item in env}
    for name, value in env_overrides.items():
        by_name[name] = {"name": name, "value": value}
    container["env"] = list(by_name.values())
    out["containers"] = [container] + containers[1:]
    out["initContainers"] = out.get("initContainers") or []
    return out
```

- [ ] **Step 3: Run tests; expect PASS**

Run: `functions/.venv/bin/pytest functions/tests -v`
Expected: 10 passed.

- [ ] **Step 4: Wire `main` to do the GET-mutate-POST**

Replace the placeholder return at the end of `main` in `functions/run-pipeline/__init__.py`:

```python
def main(req: func.HttpRequest) -> func.HttpResponse:
    expected_key = os.environ.get("ADMIN_API_KEY")
    provided_key = req.headers.get("x-admin-key")
    if not expected_key or not provided_key or provided_key != expected_key:
        log.info("admin key mismatch from %s", req.headers.get("x-forwarded-for", "?"))
        return func.HttpResponse("unauthorized", status_code=401)
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse("body must be JSON", status_code=400)
    try:
        validated = parse_and_validate(body)
    except ValueError as exc:
        return func.HttpResponse(str(exc), status_code=400)

    log.info(
        "validated: period=%s start=%s end=%s cache=%s source_ip=%s",
        validated.period, validated.start, validated.end, validated.api_cache_mode,
        req.headers.get("x-forwarded-for", "?"),
    )

    try:
        execution_name = _start_job(validated)
    except Exception as exc:
        log.exception("job start failed")
        return func.HttpResponse(f"job start failed: {exc}", status_code=502)
    return func.HttpResponse(
        json.dumps({"execution_name": execution_name}),
        status_code=202,
        mimetype="application/json",
    )


def _start_job(validated: ValidatedRequest) -> str:
    from azure.identity import ManagedIdentityCredential
    subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]
    resource_group = os.environ["AZURE_RESOURCE_GROUP"]
    job_name = os.environ["CONTAINER_APP_JOB_NAME"]
    client_id = os.environ["AZURE_CLIENT_ID"]

    credential = ManagedIdentityCredential(client_id=client_id)
    token = credential.get_token("https://management.azure.com/.default").token
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    urls = build_job_urls(subscription_id, resource_group, job_name)

    with httpx.Client(timeout=30.0) as http:
        get_resp = http.get(urls.get_template, headers=headers)
        get_resp.raise_for_status()
        template = get_resp.json()["properties"]["template"]
        mutated = mutate_template(template, {
            "PERIOD_MODE": "explicit",
            "PERIOD_TYPE": validated.period,
            "PERIOD_START": validated.start,
            "PERIOD_END": validated.end,
            "API_CACHE_MODE": validated.api_cache_mode,
        })
        # Jobs - Start body is the JobExecutionTemplate at the top level
        start_resp = http.post(urls.start, headers=headers, json=mutated)
        start_resp.raise_for_status()
    # The response body includes an execution name in the resource id
    location = start_resp.headers.get("location", "")
    return location.rsplit("/", 1)[-1] if location else "unknown"
```

- [ ] **Step 5: Add test that covers the full handler with mocked ARM**

Append to `functions/tests/test_run_pipeline.py`:

```python
from unittest.mock import MagicMock, patch


class FakeHttpRequest:
    def __init__(self, headers=None, body=None):
        self.headers = headers or {}
        self._body = body or {}

    def get_json(self):
        return self._body


def test_handler_returns_401_when_admin_key_missing(monkeypatch):
    monkeypatch.setenv("ADMIN_API_KEY", "secret")
    resp = run_pipeline_main.main(FakeHttpRequest(headers={}, body={}))
    assert resp.status_code == 401


def test_handler_starts_job_on_valid_request(monkeypatch):
    monkeypatch.setenv("ADMIN_API_KEY", "secret")
    monkeypatch.setenv("AZURE_SUBSCRIPTION_ID", "sub")
    monkeypatch.setenv("AZURE_RESOURCE_GROUP", "rg")
    monkeypatch.setenv("CONTAINER_APP_JOB_NAME", "job")
    monkeypatch.setenv("AZURE_CLIENT_ID", "cid")

    fake_template = {
        "properties": {"template": {"containers": [{"name": "p", "image": "i", "env": []}], "initContainers": []}}
    }
    fake_get = MagicMock(status_code=200, json=MagicMock(return_value=fake_template), raise_for_status=MagicMock())
    fake_post = MagicMock(status_code=200, raise_for_status=MagicMock())
    fake_post.headers = {"location": "https://x/.../jobs/job/executions/exec-abc"}
    fake_http = MagicMock()
    fake_http.__enter__.return_value = fake_http
    fake_http.get.return_value = fake_get
    fake_http.post.return_value = fake_post

    with patch("run_pipeline_main.httpx.Client", return_value=fake_http), \
         patch("run_pipeline_main.ManagedIdentityCredential") as fake_cred:
        fake_cred.return_value.get_token.return_value.token = "tok"
        from datetime import date
        run_pipeline_main.parse_and_validate = lambda b, now=None: run_pipeline_main.parse_and_validate.__wrapped__(b, now=date(2026, 5, 11)) if hasattr(run_pipeline_main.parse_and_validate, "__wrapped__") else parse_and_validate(b, now=date(2026, 5, 11))
        resp = run_pipeline_main.main(FakeHttpRequest(
            headers={"x-admin-key": "secret"},
            body={"period": "month", "start": "2026-04-01", "end": "2026-04-30"},
        ))
    assert resp.status_code == 202
    assert b"exec-abc" in resp.get_body()
```

If the test's monkey-patching of `parse_and_validate` becomes awkward, accept that the handler test is harder to wire than the pure unit tests and rely more on the integration check in Phase 7. The critical coverage is in the `mutate_template` and `parse_and_validate` unit tests.

- [ ] **Step 6: Run all tests**

Run: `functions/.venv/bin/pytest functions/tests -v`
Expected: at least `parse_and_validate` and `mutate_template` tests pass. The handler test may need adjustment; that's expected.

- [ ] **Step 7: Commit**

```bash
git add functions/run-pipeline/__init__.py functions/tests/test_run_pipeline.py
git commit -m "feat(function): GET-mutate-POST job start

GETs the current Job template, mutates the single container's
PERIOD_*/API_CACHE_MODE env vars in place, POSTs the mutated
JobExecutionTemplate (top-level containers[], initContainers[]) to
/start. ManagedIdentityCredential uses AZURE_CLIENT_ID to pick the
correct UAMI."
```

---

## Phase 4: Container image

### Task 13: Dockerfile + .dockerignore

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`

- [ ] **Step 1: Create `.dockerignore`**

Write:

```
.git
.github
.venv
__pycache__
*.pyc
.pytest_cache
.ruff_cache
.mypy_cache
data/
dashboard/node_modules
dashboard/dist
docs/
tests/
*.duckdb
*.duckdb.wal
.env
.env.*
infra/
functions/
.worktrees/
```

- [ ] **Step 2: Create `Dockerfile`**

```dockerfile
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps for any wheels that need a compiler. Slim should already cover most.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy only what's needed to install
COPY pyproject.toml ./
COPY pipeline ./pipeline
COPY README.md ./

RUN pip install -e .

# Default DATA_DIR inside the container (ephemeral)
ENV DATA_DIR=/data
RUN mkdir -p /data/reports

ENTRYPOINT ["python", "-m", "pipeline.azure_run"]
```

- [ ] **Step 3: Build locally**

Run: `docker build -t neolore-pipeline:dev .`
Expected: image builds successfully. Build time ~1-2 min on first run, cached afterwards.

- [ ] **Step 4: Smoke-run the image with explicit dates, no upload, no MotherDuck**

Run:
```bash
docker run --rm \
  -e PERIOD_MODE=explicit \
  -e PERIOD_TYPE=month \
  -e PERIOD_START=2026-04-01 \
  -e PERIOD_END=2026-04-30 \
  -e SOURCE=csv \
  -e WRITE_STORE=0 \
  -e CSV_DIR=/app/data/csv-uploads \
  neolore-pipeline:dev || true
```

Expected: same "Missing required queue CSVs" error as a local run with no CSVs — confirms the image's entrypoint reaches `azure_run` → `run_csv` correctly. If CSVs are mounted via `-v $(pwd)/data:/app/data` the image should produce a real report bundle.

- [ ] **Step 5: Commit**

```bash
git add Dockerfile .dockerignore
git commit -m "feat(infra): Dockerfile for the pipeline image

python:3.12-slim base, installs the project, entrypoint runs the
azure_run wrapper. DATA_DIR defaults to /data (ephemeral)."
```

---

## Phase 5: Bicep IaC

This phase is a single template split across several Tasks for review readability. After each Task the operator runs `az deployment group what-if` against a sandbox subscription to validate; that's the verification step.

### Task 14: Bicep — parameters, identities, Key Vault

**Files:**
- Create: `infra/main.bicep`
- Create: `infra/parameters.json`
- Modify: `.gitignore`

- [ ] **Step 1: Update `.gitignore`**

Append the line `infra/parameters.local.json` to `.gitignore`:

```
infra/parameters.local.json
```

- [ ] **Step 2: Create `infra/parameters.json` (committed defaults, no secrets)**

```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "location": { "value": "canadacentral" },
    "namePrefix": { "value": "neolore-queue" },
    "containerJobImage": { "value": "mcr.microsoft.com/k8se/quickstart-jobs:latest" }
  }
}
```

- [ ] **Step 3: Start `infra/main.bicep` with parameters + UAMIs + Key Vault**

```bicep
targetScope = 'resourceGroup'

@description('Primary Azure region')
param location string = 'canadacentral'

@description('Prefix used to name all resources')
param namePrefix string = 'neolore-queue'

@description('Initial placeholder image for the Container Apps Job (replaced by CI/CD)')
param containerJobImage string = 'mcr.microsoft.com/k8se/quickstart-jobs:latest'

@secure()
@description('MotherDuck read-write token')
param motherduckTokenRw string

@secure()
@description('Versature OAuth client id')
param versatureClientId string

@secure()
@description('Versature OAuth client secret')
param versatureClientSecret string

@secure()
@description('Admin API key for the manual-trigger Function')
param adminApiKey string

@description('Queue IDs (non-secret config) — order: english, french, ai_overflow_en, ai_overflow_fr')
param queueEnglish string = '8020'
param queueFrench string = '8021'
param queueAiOverflowEn string = '8030'
param queueAiOverflowFr string = '8031'
param dnisPrimary string = '16135949199'
param dnisSecondary string = '6135949199'
param motherduckDatabase string = 'csh_analytics_v2'
param timezone string = 'America/Toronto'

var resourceSuffix = uniqueString(resourceGroup().id)
var storageAccountName = take(replace('${namePrefix}st${resourceSuffix}', '-', ''), 24)
var keyVaultName = take('${namePrefix}-kv-${resourceSuffix}', 24)
var acrName = take(replace('${namePrefix}acr${resourceSuffix}', '-', ''), 50)
var logAnalyticsName = '${namePrefix}-law'
var appInsightsName = '${namePrefix}-ai'
var containerAppsEnvName = '${namePrefix}-cae'
var containerAppJobName = '${namePrefix}-pipeline-job'
var functionAppName = '${namePrefix}-fn'
var functionStorageName = take(replace('${namePrefix}fn${resourceSuffix}', '-', ''), 24)
var swaName = '${namePrefix}-dashboard'
var pipelineIdentityName = 'id-${namePrefix}-pipeline'
var functionIdentityName = 'id-${namePrefix}-function'

// ---------- User-assigned managed identities ----------

resource pipelineIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-07-31-preview' = {
  name: pipelineIdentityName
  location: location
}

resource functionIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-07-31-preview' = {
  name: functionIdentityName
  location: location
}

// ---------- Key Vault + secrets ----------

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enabledForDeployment: false
    enabledForTemplateDeployment: false
    enabledForDiskEncryption: false
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
  }
}

resource secretMotherduckTokenRw 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'motherduck-token-rw'
  properties: { value: motherduckTokenRw }
}

resource secretVersatureClientId 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'versature-client-id'
  properties: { value: versatureClientId }
}

resource secretVersatureClientSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'versature-client-secret'
  properties: { value: versatureClientSecret }
}

resource secretAdminApiKey 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'admin-api-key'
  properties: { value: adminApiKey }
}

output pipelineIdentityResourceId string = pipelineIdentity.id
output functionIdentityResourceId string = functionIdentity.id
output keyVaultUri string = keyVault.properties.vaultUri
```

- [ ] **Step 4: Lint the template**

Run: `az bicep build --file infra/main.bicep --stdout > /tmp/main.json`
Expected: no errors. Inspect `/tmp/main.json` briefly to confirm ARM JSON output.

- [ ] **Step 5: Commit**

```bash
git add infra/main.bicep infra/parameters.json .gitignore
git commit -m "feat(infra): Bicep — parameters, UAMIs, Key Vault + secrets"
```

---

### Task 15: Bicep — Storage + diagnostic settings + Log Analytics + App Insights

**Files:**
- Modify: `infra/main.bicep`

- [ ] **Step 1: Append the Log Analytics + App Insights resources**

Insert before the `output` block in `infra/main.bicep`:

```bicep
// ---------- Log Analytics + App Insights ----------

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}
```

- [ ] **Step 2: Append the storage account + container + diagnostic setting**

```bicep
// ---------- Storage account + reports container ----------

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  kind: 'StorageV2'
  sku: { name: 'Standard_LRS' }
  properties: {
    allowBlobPublicAccess: true
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
  properties: {
    cors: {
      corsRules: [
        {
          allowedOrigins: [ 'https://*.azurestaticapps.net' ]
          allowedMethods: [ 'GET', 'HEAD' ]
          allowedHeaders: [ '*' ]
          exposedHeaders: [ '*' ]
          maxAgeInSeconds: 3600
        }
      ]
    }
  }
}

resource reportsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'reports'
  properties: {
    publicAccess: 'Blob'
  }
}

resource blobDiag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  scope: blobService
  name: 'blob-to-law'
  properties: {
    workspaceId: logAnalytics.id
    logs: [
      { category: 'StorageWrite', enabled: true }
      { category: 'StorageDelete', enabled: true }
    ]
  }
}
```

- [ ] **Step 3: Add `Storage Blob Data Contributor` for the pipeline UAMI, scoped to the container**

```bicep
var roleStorageBlobDataContributor = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'

resource pipelineBlobRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: reportsContainer
  name: guid(reportsContainer.id, pipelineIdentity.id, roleStorageBlobDataContributor)
  properties: {
    principalId: pipelineIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleStorageBlobDataContributor)
  }
}
```

- [ ] **Step 4: Add `Key Vault Secrets User` role assignments (per-secret scope)**

```bicep
var roleKeyVaultSecretsUser = '4633458b-17de-408a-b874-0445c86b69e6'

resource pipelineKvMd 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: secretMotherduckTokenRw
  name: guid(secretMotherduckTokenRw.id, pipelineIdentity.id)
  properties: {
    principalId: pipelineIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleKeyVaultSecretsUser)
  }
}

resource pipelineKvVersId 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: secretVersatureClientId
  name: guid(secretVersatureClientId.id, pipelineIdentity.id)
  properties: {
    principalId: pipelineIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleKeyVaultSecretsUser)
  }
}

resource pipelineKvVersSecret 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: secretVersatureClientSecret
  name: guid(secretVersatureClientSecret.id, pipelineIdentity.id)
  properties: {
    principalId: pipelineIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleKeyVaultSecretsUser)
  }
}

resource functionKvAdmin 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: secretAdminApiKey
  name: guid(secretAdminApiKey.id, functionIdentity.id)
  properties: {
    principalId: functionIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleKeyVaultSecretsUser)
  }
}
```

- [ ] **Step 5: Lint**

Run: `az bicep build --file infra/main.bicep --stdout > /dev/null`
Expected: no errors. (You may see warnings about `secure parameters used in output` — there shouldn't be any; if there are, fix the offending output line.)

- [ ] **Step 6: Commit**

```bash
git add infra/main.bicep
git commit -m "feat(infra): storage + diagnostics + Log Analytics + App Insights + KV roles"
```

---

### Task 16: Bicep — ACR + Container Apps Env + Container Apps Job

**Files:**
- Modify: `infra/main.bicep`

- [ ] **Step 1: Append ACR + AcrPull for the pipeline UAMI**

Add before the existing `output` block:

```bicep
// ---------- Azure Container Registry ----------

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: false }
}

var roleAcrPull = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

resource pipelineAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: acr
  name: guid(acr.id, pipelineIdentity.id, roleAcrPull)
  properties: {
    principalId: pipelineIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleAcrPull)
  }
}
```

- [ ] **Step 2: Append the Container Apps Environment**

```bicep
// ---------- Container Apps Environment ----------

resource containerAppsEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: containerAppsEnvName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: listKeys(logAnalytics.id, '2023-09-01').primarySharedKey
      }
    }
  }
}
```

- [ ] **Step 3: Append the Container Apps Job**

```bicep
// ---------- Container Apps Job ----------

resource containerAppJob 'Microsoft.App/jobs@2024-03-01' = {
  name: containerAppJobName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${pipelineIdentity.id}': {}
    }
  }
  properties: {
    environmentId: containerAppsEnv.id
    configuration: {
      triggerType: 'Schedule'
      replicaTimeout: 3600
      replicaRetryLimit: 0
      scheduleTriggerConfig: {
        cronExpression: '0 9 1 * *'
        parallelism: 1
        replicaCompletionCount: 1
      }
      registries: [
        {
          server: '${acr.name}.azurecr.io'
          identity: pipelineIdentity.id
        }
      ]
      secrets: [
        { name: 'motherduck-token-rw', identity: pipelineIdentity.id, keyVaultUrl: '${keyVault.properties.vaultUri}secrets/motherduck-token-rw' }
        { name: 'versature-client-id', identity: pipelineIdentity.id, keyVaultUrl: '${keyVault.properties.vaultUri}secrets/versature-client-id' }
        { name: 'versature-client-secret', identity: pipelineIdentity.id, keyVaultUrl: '${keyVault.properties.vaultUri}secrets/versature-client-secret' }
      ]
    }
    template: {
      containers: [
        {
          name: 'pipeline'
          image: containerJobImage
          resources: { cpu: 1, memory: '2Gi' }
          env: [
            { name: 'PERIOD_MODE', value: 'previous-month' }
            { name: 'PERIOD_TYPE', value: 'month' }
            { name: 'API_CACHE_MODE', value: 'auto' }
            { name: 'WRITE_STORE', value: '1' }
            { name: 'SOURCE', value: 'api' }
            { name: 'DATA_DIR', value: '/data' }
            { name: 'TIMEZONE', value: timezone }
            { name: 'MOTHERDUCK_DATABASE', value: motherduckDatabase }
            { name: 'QUEUE_ENGLISH', value: queueEnglish }
            { name: 'QUEUE_FRENCH', value: queueFrench }
            { name: 'QUEUE_AI_OVERFLOW_EN', value: queueAiOverflowEn }
            { name: 'QUEUE_AI_OVERFLOW_FR', value: queueAiOverflowFr }
            { name: 'DNIS_PRIMARY', value: dnisPrimary }
            { name: 'DNIS_SECONDARY', value: dnisSecondary }
            { name: 'AZURE_CLIENT_ID', value: pipelineIdentity.properties.clientId }
            { name: 'REPORTS_STORAGE_ACCOUNT_URL', value: 'https://${storage.name}.blob.${environment().suffixes.storage}' }
            { name: 'REPORTS_CONTAINER', value: 'reports' }
            { name: 'MOTHERDUCK_TOKEN_RW', secretRef: 'motherduck-token-rw' }
            { name: 'VERSATURE_CLIENT_ID', secretRef: 'versature-client-id' }
            { name: 'VERSATURE_CLIENT_SECRET', secretRef: 'versature-client-secret' }
          ]
        }
      ]
    }
  }
}

output containerAppJobName string = containerAppJob.name
output acrLoginServer string = '${acr.name}.azurecr.io'
output storageAccountName string = storage.name
output reportsBaseUrl string = '${storage.properties.primaryEndpoints.blob}reports'
```

- [ ] **Step 4: Append the Container Apps Jobs Operator role on the Job, granted to the function UAMI**

```bicep
// Container Apps Jobs Operator: grants jobs/start/action, jobs/stop/action, read.
var roleContainerAppJobsOperator = 'b9a307c4-5aa3-4b52-ba60-2b17c136cd7b'

resource functionJobsOperator 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: containerAppJob
  name: guid(containerAppJob.id, functionIdentity.id, roleContainerAppJobsOperator)
  properties: {
    principalId: functionIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleContainerAppJobsOperator)
  }
}
```

Note: confirm the role ID by running `az role definition list --name "Container Apps Jobs Operator" --query '[0].name'`. If it differs, update the literal above.

- [ ] **Step 5: Lint**

Run: `az bicep build --file infra/main.bicep --stdout > /dev/null`
Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add infra/main.bicep
git commit -m "feat(infra): ACR + Container Apps Environment + Container Apps Job + role"
```

---

### Task 17: Bicep — Function App + Static Web App

**Files:**
- Modify: `infra/main.bicep`

- [ ] **Step 1: Append Function App storage + Function App**

The Functions runtime requires its own Storage account (for its internal queue + state). Keep it separate from the reports storage.

```bicep
// ---------- Function App ----------

resource functionStorage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: functionStorageName
  location: location
  kind: 'StorageV2'
  sku: { name: 'Standard_LRS' }
  properties: { minimumTlsVersion: 'TLS1_2' }
}

resource functionPlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: '${namePrefix}-fn-plan'
  location: location
  sku: { name: 'Y1', tier: 'Dynamic' }
  properties: { reserved: true }
}

resource functionApp 'Microsoft.Web/sites@2023-12-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp,linux'
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${functionIdentity.id}': {}
    }
  }
  properties: {
    serverFarmId: functionPlan.id
    httpsOnly: true
    keyVaultReferenceIdentity: functionIdentity.id
    siteConfig: {
      linuxFxVersion: 'Python|3.12'
      ftpsState: 'Disabled'
      appSettings: [
        { name: 'FUNCTIONS_EXTENSION_VERSION', value: '~4' }
        { name: 'FUNCTIONS_WORKER_RUNTIME', value: 'python' }
        { name: 'AzureWebJobsStorage', value: 'DefaultEndpointsProtocol=https;AccountName=${functionStorage.name};EndpointSuffix=${environment().suffixes.storage};AccountKey=${listKeys(functionStorage.id, '2023-05-01').keys[0].value}' }
        { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsights.properties.ConnectionString }
        { name: 'AZURE_CLIENT_ID', value: functionIdentity.properties.clientId }
        { name: 'AZURE_SUBSCRIPTION_ID', value: subscription().subscriptionId }
        { name: 'AZURE_RESOURCE_GROUP', value: resourceGroup().name }
        { name: 'CONTAINER_APP_JOB_NAME', value: containerAppJob.name }
        { name: 'ADMIN_API_KEY', value: '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=admin-api-key)' }
      ]
    }
  }
}

output functionAppName string = functionApp.name
output functionAppHostname string = functionApp.properties.defaultHostName
```

- [ ] **Step 2: Append the Static Web App**

```bicep
// ---------- Static Web App ----------

resource swa 'Microsoft.Web/staticSites@2023-12-01' = {
  name: swaName
  location: 'centralus' // SWA has a limited list of regions; centralus is available in all subs
  sku: { name: 'Free', tier: 'Free' }
  properties: {
    // Repo, branch, and provider will be configured manually after first deploy by
    // pasting the SWA's deployment token into GitHub repo secrets and pointing the
    // GitHub Action at it.
    provider: 'GitHub'
  }
}

output swaName string = swa.name
output swaHostname string = swa.properties.defaultHostname
```

- [ ] **Step 3: Lint**

Run: `az bicep build --file infra/main.bicep --stdout > /dev/null`
Expected: clean.

- [ ] **Step 4: Validate the template against an empty resource group (operator step, manual)**

This step requires Azure access. If you have an empty test RG handy:

```bash
az group create --name rg-neolore-test --location canadacentral
az deployment group what-if \
  --resource-group rg-neolore-test \
  --template-file infra/main.bicep \
  --parameters infra/parameters.json \
  --parameters motherduckTokenRw=fake versatureClientId=fake versatureClientSecret=fake adminApiKey=fake
```

Expected: the what-if output lists all 10 resources + role assignments as "Create" with no errors. Tear down:

```bash
az group delete --name rg-neolore-test --yes --no-wait
```

If you don't have Azure access, skip this step — Phase 5 ends here at the linter pass, and Phase 7's first-deploy is the integration test.

- [ ] **Step 5: Commit**

```bash
git add infra/main.bicep
git commit -m "feat(infra): Function App + Static Web App

Function uses Key Vault references for ADMIN_API_KEY with
keyVaultReferenceIdentity set to the function UAMI. Standard Functions
storage + consumption plan. SWA on Free tier."
```

---

## Phase 6: CI/CD workflows

### Task 18: Set up OIDC service principal (one-time operator task)

**Files:** None — these are azure CLI commands the operator runs once, before merging Phase 6.

- [ ] **Step 1: Create the AAD application + service principal for GitHub Actions**

Run (operator):
```bash
az ad app create --display-name "neolore-queue-github-actions" --query appId -o tsv
# → save as $APP_ID

az ad sp create --id $APP_ID --query id -o tsv
# → save as $SP_OBJECT_ID
```

- [ ] **Step 2: Grant the service principal Contributor on the resource group**

```bash
az role assignment create \
  --assignee $APP_ID \
  --role Contributor \
  --scope /subscriptions/$AZURE_SUBSCRIPTION_ID/resourceGroups/rg-neolore-queue-analytics
```

- [ ] **Step 3: Create federated credentials for each workflow**

```bash
GH_REPO="<owner>/<repo>"   # fill in

for branch in main; do
  az ad app federated-credential create --id $APP_ID --parameters "{
    \"name\": \"github-${branch}\",
    \"issuer\": \"https://token.actions.githubusercontent.com\",
    \"subject\": \"repo:${GH_REPO}:ref:refs/heads/${branch}\",
    \"audiences\": [\"api://AzureADTokenExchange\"]
  }"
done
```

- [ ] **Step 4: Record the IDs as GitHub repo secrets**

In GitHub repo settings → Secrets → Actions, set:
- `AZURE_CLIENT_ID` = `$APP_ID` (the OIDC SP, **not** either UAMI)
- `AZURE_TENANT_ID` = `az account show --query tenantId -o tsv`
- `AZURE_SUBSCRIPTION_ID` = current sub id
- `ACR_NAME` = from `az deployment group show ... --query 'properties.outputs.acrLoginServer.value'` after Bicep deploy
- `CONTAINER_APP_JOB_NAME` = from Bicep outputs
- `VITE_REPORTS_BASE_URL` = from Bicep outputs (`reportsBaseUrl`)
- `SWA_DEPLOYMENT_TOKEN` = `az staticwebapp secrets list --name neolore-queue-dashboard --query 'properties.apiKey' -o tsv`

- [ ] **Step 5: No commit — this is operator config**

---

### Task 19: Dashboard deploy workflow

**Files:**
- Create: `.github/workflows/dashboard.yml`

- [ ] **Step 1: Write the workflow**

```yaml
name: Deploy Dashboard

on:
  push:
    branches: [main]
    paths:
      - 'dashboard/**'
      - '.github/workflows/dashboard.yml'
  workflow_dispatch:

permissions:
  contents: read

jobs:
  build_and_deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: dashboard/package-lock.json

      - name: Install
        working-directory: dashboard
        run: npm ci

      - name: Test
        working-directory: dashboard
        run: npm test -- --run

      - name: Build with prod env
        working-directory: dashboard
        env:
          VITE_REPORTS_BASE_URL: ${{ secrets.VITE_REPORTS_BASE_URL }}
        run: npm run build

      - name: Deploy to SWA
        uses: Azure/static-web-apps-deploy@v1
        with:
          azure_static_web_apps_api_token: ${{ secrets.SWA_DEPLOYMENT_TOKEN }}
          action: 'upload'
          app_location: 'dashboard/dist'
          skip_app_build: true
```

- [ ] **Step 2: Commit (do not push to main until Phase 5 deploy is complete)**

```bash
git add .github/workflows/dashboard.yml
git commit -m "ci: dashboard build + deploy workflow"
```

---

### Task 20: Pipeline image workflow

**Files:**
- Create: `.github/workflows/pipeline-image.yml`

- [ ] **Step 1: Write the workflow**

```yaml
name: Build Pipeline Image

on:
  push:
    branches: [main]
    paths:
      - 'pipeline/**'
      - 'pyproject.toml'
      - 'Dockerfile'
      - '.dockerignore'
      - '.github/workflows/pipeline-image.yml'
  workflow_dispatch:

permissions:
  id-token: write
  contents: read

jobs:
  build_and_push:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Test
        run: pytest -q

      - name: Azure login (OIDC)
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      - name: ACR login
        run: az acr login --name ${{ secrets.ACR_NAME }}

      - name: Build + push image
        env:
          IMAGE: ${{ secrets.ACR_NAME }}.azurecr.io/neolore-pipeline:${{ github.sha }}
        run: |
          docker build -t $IMAGE -t ${{ secrets.ACR_NAME }}.azurecr.io/neolore-pipeline:latest .
          docker push $IMAGE
          docker push ${{ secrets.ACR_NAME }}.azurecr.io/neolore-pipeline:latest

      - name: Update Container Apps Job to new image
        env:
          IMAGE: ${{ secrets.ACR_NAME }}.azurecr.io/neolore-pipeline:${{ github.sha }}
        run: |
          az containerapp job update \
            --name ${{ secrets.CONTAINER_APP_JOB_NAME }} \
            --resource-group rg-neolore-queue-analytics \
            --image $IMAGE
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/pipeline-image.yml
git commit -m "ci: pipeline image build + push + Job image update"
```

---

### Task 21: Function deploy workflow

**Files:**
- Create: `.github/workflows/function.yml`

- [ ] **Step 1: Write the workflow**

```yaml
name: Deploy Function

on:
  push:
    branches: [main]
    paths:
      - 'functions/**'
      - '.github/workflows/function.yml'
  workflow_dispatch:

permissions:
  id-token: write
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install
        run: |
          python -m pip install --upgrade pip
          pip install -r functions/requirements.txt pytest

      - name: Test
        run: pytest functions/tests -v

      - name: Azure login (OIDC)
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      - name: Deploy Function
        uses: Azure/functions-action@v1
        with:
          app-name: neolore-queue-fn
          package: functions
          scm-do-build-during-deployment: true
          enable-oryx-build: true
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/function.yml
git commit -m "ci: Function deploy workflow"
```

---

## Phase 7: Docs + first deploy

### Task 22: Update `.env.example` and `README.md`

**Files:**
- Modify: `.env.example`
- Modify: `README.md`

- [ ] **Step 1: Update `.env.example`**

Append the following block to `.env.example`:

```bash

# --- Azure deployment (optional for local dev) ---
# When unset, the pipeline's blob uploader is a no-op and the dashboard
# falls back to /data/reports. Set these only when reproducing the Azure
# environment locally.
REPORTS_STORAGE_ACCOUNT_URL=
REPORTS_CONTAINER=reports
ADMIN_API_KEY=

# Period override env vars (consumed by pipeline.azure_run, not pipeline.main)
PERIOD_MODE=previous-month
PERIOD_TYPE=month
PERIOD_START=
PERIOD_END=
API_CACHE_MODE=auto
WRITE_STORE=1
```

- [ ] **Step 2: Append a "Deploying to Azure" section to `README.md`**

```markdown
## Deploying to Azure

Production runs in Azure using a Container Apps Job (pipeline), a Function App (manual trigger), Blob Storage (reports), and Static Web Apps (dashboard). Design is in `docs/superpowers/specs/2026-05-11-azure-deployment-design.md`; implementation steps in `docs/superpowers/plans/2026-05-11-azure-deployment-implementation.md`.

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
   - Dashboard builds + uploads to SWA.
   - Pipeline image builds + pushes to ACR + updates the Job.
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
... -d '{"period":"month","start":"...","end":"...","api_cache_mode":"refresh"}'
```

Replay from saved extract without calling Versature:
```bash
... -d '{"period":"month","start":"...","end":"...","api_cache_mode":"reuse"}'
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
```

- [ ] **Step 3: Commit**

```bash
git add .env.example README.md
git commit -m "docs: env vars + Azure deployment + operator runbook"
```

---

### Task 23: First-time Bicep deploy (operator step)

**Files:** None (operator action).

- [ ] **Step 1: Prepare gitignored secrets file**

Create `infra/parameters.local.json` per Task 22 step 2 with real secret values. Verify it's gitignored:
```bash
git check-ignore -v infra/parameters.local.json
```
Expected: prints the matching rule from `.gitignore`. **If this command says the file is not ignored, stop and fix `.gitignore` before proceeding.**

- [ ] **Step 2: Deploy**

```bash
az group create --name rg-neolore-queue-analytics --location canadacentral
az deployment group create \
  --resource-group rg-neolore-queue-analytics \
  --template-file infra/main.bicep \
  --parameters infra/parameters.json \
  --parameters @infra/parameters.local.json
```

Expected: completes successfully in 5-10 minutes. Output block includes `acrLoginServer`, `containerAppJobName`, `reportsBaseUrl`, `swaHostname`, `functionAppHostname`, `functionAppName`.

- [ ] **Step 3: Set GitHub repo secrets per Task 18 Step 4 using the deploy outputs**

- [ ] **Step 4: Verify the placeholder Container Apps Job is healthy (it won't actually run usefully yet)**

```bash
az containerapp job show \
  --name <container-app-job-name> \
  --resource-group rg-neolore-queue-analytics \
  --query 'properties.template.containers[0].image' -o tsv
```
Expected: `mcr.microsoft.com/k8se/quickstart-jobs:latest` — the placeholder.

- [ ] **Step 5: Merge Phase 6 workflows to `main`**

If they haven't been merged yet, push them now. The push will trigger all three workflows. Watch them in GitHub Actions:
- Pipeline image: builds + pushes + updates Job image to `neolore-pipeline:<sha>`.
- Function: deploys.
- Dashboard: deploys.

All three should go green within ~10 minutes.

- [ ] **Step 6: Verify the Job's image was replaced by the workflow**

```bash
az containerapp job show \
  --name <container-app-job-name> \
  --resource-group rg-neolore-queue-analytics \
  --query 'properties.template.containers[0].image' -o tsv
```
Expected: now points at `<acr>.azurecr.io/neolore-pipeline:<sha>`.

---

### Task 24: Seed run + acceptance

**Files:** None (operator action).

- [ ] **Step 1: Trigger a manual run for the most recent completed calendar month**

```bash
curl -i -X POST "https://<function-hostname>/api/run-pipeline" \
  -H "x-admin-key: <admin-api-key>" \
  -H "content-type: application/json" \
  -d '{"period":"month","start":"<YYYY-MM-01>","end":"<YYYY-MM-DD>","api_cache_mode":"auto"}'
```

Expected: `HTTP/1.1 202 Accepted` with body `{"execution_name":"..."}`.

- [ ] **Step 2: Wait for execution to succeed**

```bash
az containerapp job execution list \
  --name <container-app-job-name> \
  --resource-group rg-neolore-queue-analytics \
  --query '[?contains(name, `<execution_name>`)].properties.status' -o tsv
```
Expected: eventually reads `Succeeded`. If `Failed`, view logs:
```bash
az containerapp job logs show \
  --name <container-app-job-name> \
  --resource-group rg-neolore-queue-analytics \
  --execution <execution_name> --follow
```

- [ ] **Step 3: Verify the manifest and report landed in blob storage**

```bash
az storage blob list \
  --account-name <storage-account-name> \
  --container-name reports \
  --auth-mode login \
  --query '[].name' -o tsv
```
Expected: includes `manifest.json` and `month_<start>_<end>/metrics.json`.

```bash
az storage blob download \
  --account-name <storage-account-name> \
  --container-name reports --name manifest.json \
  --auth-mode login --file /tmp/manifest.json
cat /tmp/manifest.json
```
Expected: contains an entry with the seeded period.

- [ ] **Step 4: Visit the dashboard**

Open `https://<swa-hostname>` in a browser. Confirm:
- The report month selector shows the seeded month.
- Selecting it loads the metrics from the blob URL (check Network tab — fetches go to `https://<storage>.blob.core.windows.net/reports/...`).
- No console errors.

- [ ] **Step 5: Confirm the dashboard refuses to use the bundled fixture in production**

In the browser dev tools Network tab, set the manifest URL to "block" (right-click → Block request URL). Reload. The UI should show an error state, NOT a chart of April 2026. This proves the fixture fallback gate works.

- [ ] **Step 6: Tag the release**

```bash
git tag -a v0.1.0-azure -m "First Azure deploy: pipeline + dashboard live"
git push --tags
```

- [ ] **Step 7: No additional commit needed.**

---

## Acceptance Criteria (cross-reference)

| Spec section | Plan task(s) |
|---|---|
| Data classification (PII public) | Task 9 (robots/noindex), README warning in Task 22 |
| Architecture: pipeline image | Task 13 |
| Architecture: Container Apps Job | Task 16 |
| Architecture: manual trigger Function | Tasks 10-12, 17 |
| Architecture: Static Web Apps | Tasks 7-9, 17, 19 |
| Manifest concurrency (ETag CAS) | Tasks 3-4 |
| Period-files upload | Task 4 |
| Dashboard base URL resolver | Tasks 7-8 |
| Dashboard fixture fallback gate | Tasks 7-8 |
| Two UAMIs with split roles | Tasks 14, 15, 16, 17 |
| `keyVaultReferenceIdentity` on Function | Task 17 |
| `AZURE_CLIENT_ID` env on container + function | Tasks 16, 17 |
| Blob diagnostic setting (writes/deletes only) | Task 15 |
| `Storage Blob Data Contributor` scoped to container | Task 15 |
| `Container Apps Jobs Operator` on Job | Task 16 |
| Bicep `@secure()` parameters + gitignored local file | Tasks 14, 22, 23 |
| Function payload validation (month-only, ≤92 days, no-future) | Task 11 |
| Function GET-mutate-POST | Task 12 |
| Function indirect-trust documented | (Documented in design spec; nothing to implement) |
| CI/CD via OIDC + SWA token exception | Tasks 18-21 |
| Operator runbook | Task 22 |
| First seed run | Task 24 |

---

## Self-Review

Spec coverage check passed: every requirement in the design spec maps to a task above. Type consistency: function names and signatures referenced across tasks (`resolve_period`, `compute_merged_manifest`, `upload_manifest_with_cas`, `upload_period_files`, `upload_reports`, `parse_and_validate`, `mutate_template`, `build_job_urls`, `_build_credential`, `_acquire_period_lease`) are defined exactly once and used consistently downstream. No placeholders; every code step shows the actual code; every command shows expected output.
