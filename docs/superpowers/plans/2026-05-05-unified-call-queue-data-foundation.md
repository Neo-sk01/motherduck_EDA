# Unified Call Queue Data Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the validated data foundation for the NeoLore unified call queue analytics dashboard: ingestion, parsing, deduplication, MotherDuck persistence, report JSON emission, historical backfill, and April 2026 validation.

**Architecture:** Implement a Python package under `pipeline/` with small modules for configuration, ingestion, parsing, deduplication, metrics, cross-queue analysis, anomaly detection, storage, report writing, API inventory, and CLI orchestration. Unit tests use synthetic data and local DuckDB; April reference tests use real files only when available. The React dashboard and thin backend API are a follow-on plan after this data contract is stable.

**Tech Stack:** Python 3.11+, pandas, duckdb, pyarrow, httpx, tenacity, pytest, python-dotenv, MotherDuck via DuckDB `md:` connection.

---

## Scope Boundary

This plan implements the data foundation from the approved design spec:

- CSV, API, and hybrid-ready pipeline structure.
- Four queue topology.
- Exact parsing and deduplication rules.
- Per-queue metrics.
- Cross-queue funnel, agent, caller, comparative, and anomaly metrics.
- MotherDuck write path.
- `data/reports/{period}_{key}/metrics.json` and per-queue JSON files.
- Historical backfill before `2026-04-01`.
- April 2026 validation gates.

This plan does not implement the React dashboard or backend API. Those will be implemented in a separate plan against the JSON/MotherDuck contract produced here.

## File Map

- Create `pyproject.toml`: package metadata, runtime dependencies, pytest config.
- Create `.gitignore`: ignore secrets, generated data, caches, build artifacts.
- Create `.env.example`: secret-free environment contract.
- Create `README.md`: local setup and pipeline commands.
- Create `pipeline/__init__.py`: package marker.
- Create `pipeline/config.py`: environment loading, queue metadata, source mode parsing.
- Create `pipeline/parse.py`: timestamp, duration, caller, and release reason normalization.
- Create `pipeline/dedup.py`: CSV/API deduplication with keep-last semantics.
- Create `pipeline/ingest_csv.py`: load four queue CSV exports and preserve raw rows.
- Create `pipeline/client.py`: Versature API client with pagination, auth header, rate limiting, retry behavior.
- Create `pipeline/flatten.py`: nested JSON field flattening and field inventory.
- Create `pipeline/curate.py`: raw-to-curated call table construction.
- Create `pipeline/metrics_queue.py`: per-queue metrics from curated calls.
- Create `pipeline/crossqueue.py`: funnel metrics, consolidated agent/caller tables, comparative series.
- Create `pipeline/anomaly.py`: anomaly rules from the brief.
- Create `pipeline/storage.py`: DuckDB/MotherDuck schema creation and period replacement writes.
- Create `pipeline/report.py`: report JSON assembly and file emission.
- Create `pipeline/main.py`: CLI orchestration.
- Create `tests/conftest.py`: shared synthetic fixtures.
- Create `tests/test_config.py`: environment and queue metadata tests.
- Create `tests/test_parse.py`: timestamp/duration/caller parsing tests.
- Create `tests/test_dedup.py`: CSV/API keep-last tests.
- Create `tests/test_ingest_csv.py`: CSV source loading tests.
- Create `tests/test_curate.py`: curated schema tests.
- Create `tests/test_metrics_queue.py`: per-queue metric tests.
- Create `tests/test_crossqueue.py`: funnel and consolidation tests.
- Create `tests/test_anomaly.py`: anomaly detection tests.
- Create `tests/test_storage.py`: local DuckDB schema/write/idempotency tests.
- Create `tests/test_report.py`: metrics JSON emission tests.
- Create `tests/test_client.py`: API pagination/retry/response-shape tests with mocked transport.
- Create `tests/test_april_2026_reference.py`: real-data validation tests, skipped when required files are unavailable.

---

### Task 1: Project Scaffold And Secret-Safe Environment Contract

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `README.md`

- [ ] **Step 1: Write the scaffold files**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "neolore-queue-analytics"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "duckdb>=1.2.0",
  "httpx>=0.27.0",
  "pandas>=2.2.0",
  "pyarrow>=15.0.0",
  "python-dotenv>=1.0.0",
  "tenacity>=8.2.0"
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0.0"
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

Create `.gitignore`:

```gitignore
.env
.env.*
!.env.example
__pycache__/
.pytest_cache/
.ruff_cache/
.mypy_cache/
*.pyc
data/raw/
data/curated/
data/reports/
data/csv-uploads/
*.duckdb
*.duckdb.wal
node_modules/
dist/
```

Create `.env.example`:

```dotenv
MOTHERDUCK_TOKEN_RW=
MOTHERDUCK_TOKEN_RO=
MOTHERDUCK_DATABASE=csh_analytics_v2
VERSATURE_BASE_URL=https://integrate.versature.com/api
VERSATURE_CLIENT_ID=
VERSATURE_CLIENT_SECRET=
VERSATURE_API_VERSION=application/vnd.integrate.v1.10.0+json
VERSATURE_ACCESS_TOKEN=
SOURCE=csv
CSV_DIR=./data/csv-uploads
DATA_DIR=./data
TIMEZONE=America/Toronto
QUEUE_ENGLISH=8020
QUEUE_FRENCH=8021
QUEUE_AI_OVERFLOW_EN=8030
QUEUE_AI_OVERFLOW_FR=8031
DNIS_PRIMARY=16135949199
DNIS_SECONDARY=6135949199
```

Create `README.md`:

```markdown
# NeoLore Queue Analytics

Batch analytics pipeline and dashboard data foundation for four NeoLore CSR queues.

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
cp .env.example .env
```

Put secrets only in `.env`. Do not commit secrets.

## CSV Run

Place the four SONAR Queue Detail CSV files in `data/csv-uploads/`, then run:

```bash
python -m pipeline.main --source csv --period month --start 2026-04-01 --end 2026-04-30
```

## Tests

```bash
pytest
```
```

- [ ] **Step 2: Verify scaffold parses**

Run: `python -m pytest --collect-only`

Expected: collection succeeds with `no tests collected` until tests are added.

- [ ] **Step 3: Commit scaffold**

```bash
git add pyproject.toml .gitignore .env.example README.md
git commit -m "chore: scaffold queue analytics project"
```

---

### Task 2: Configuration And Queue Metadata

**Files:**
- Create: `pipeline/__init__.py`
- Create: `pipeline/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing config tests**

Create `tests/test_config.py`:

```python
from pipeline.config import AppConfig, QueueConfig, build_default_queues, parse_source_mode


def test_default_queues_match_brief():
    queues = build_default_queues()
    assert [q.queue_id for q in queues] == ["8020", "8021", "8030", "8031"]
    assert queues[0] == QueueConfig("8020", "CSR English", "English", "primary")
    assert queues[1] == QueueConfig("8021", "CSR French", "French", "primary")
    assert queues[2] == QueueConfig("8030", "CSR Overflow English", "English", "overflow")
    assert queues[3] == QueueConfig("8031", "CSR Overflow French", "French", "overflow")


def test_source_mode_is_restricted():
    assert parse_source_mode("csv") == "csv"
    assert parse_source_mode("api") == "api"
    assert parse_source_mode("hybrid") == "hybrid"


def test_source_mode_rejects_unknown_value():
    try:
        parse_source_mode("live")
    except ValueError as exc:
        assert "SOURCE must be one of" in str(exc)
    else:
        raise AssertionError("unknown source mode should raise ValueError")


def test_app_config_from_env(monkeypatch):
    monkeypatch.setenv("MOTHERDUCK_DATABASE", "csh_analytics_v2")
    monkeypatch.setenv("SOURCE", "csv")
    monkeypatch.setenv("CSV_DIR", "./data/csv-uploads")
    monkeypatch.setenv("DATA_DIR", "./data")
    monkeypatch.setenv("TIMEZONE", "America/Toronto")
    cfg = AppConfig.from_env()
    assert cfg.motherduck_database == "csh_analytics_v2"
    assert cfg.source == "csv"
    assert cfg.csv_dir.endswith("data/csv-uploads")
    assert cfg.data_dir.endswith("data")
    assert cfg.timezone == "America/Toronto"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'pipeline.config'`.

- [ ] **Step 3: Implement config module**

Create `pipeline/__init__.py`:

```python
"""NeoLore queue analytics pipeline."""
```

Create `pipeline/config.py`:

```python
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

SourceMode = Literal["csv", "api", "hybrid"]
QueueRole = Literal["primary", "overflow"]


@dataclass(frozen=True)
class QueueConfig:
    queue_id: str
    name: str
    language: str
    role: QueueRole


@dataclass(frozen=True)
class AppConfig:
    motherduck_database: str
    source: SourceMode
    csv_dir: Path
    data_dir: Path
    timezone: str
    queues: tuple[QueueConfig, ...]

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            motherduck_database=os.getenv("MOTHERDUCK_DATABASE", "csh_analytics_v2"),
            source=parse_source_mode(os.getenv("SOURCE", "csv")),
            csv_dir=Path(os.getenv("CSV_DIR", "./data/csv-uploads")),
            data_dir=Path(os.getenv("DATA_DIR", "./data")),
            timezone=os.getenv("TIMEZONE", "America/Toronto"),
            queues=tuple(build_default_queues()),
        )


def parse_source_mode(value: str) -> SourceMode:
    if value in {"csv", "api", "hybrid"}:
        return value  # type: ignore[return-value]
    raise ValueError("SOURCE must be one of: csv, api, hybrid")


def build_default_queues() -> list[QueueConfig]:
    return [
        QueueConfig(os.getenv("QUEUE_ENGLISH", "8020"), "CSR English", "English", "primary"),
        QueueConfig(os.getenv("QUEUE_FRENCH", "8021"), "CSR French", "French", "primary"),
        QueueConfig(os.getenv("QUEUE_AI_OVERFLOW_EN", "8030"), "CSR Overflow English", "English", "overflow"),
        QueueConfig(os.getenv("QUEUE_AI_OVERFLOW_FR", "8031"), "CSR Overflow French", "French", "overflow"),
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`

Expected: PASS.

- [ ] **Step 5: Commit config**

```bash
git add pipeline/__init__.py pipeline/config.py tests/test_config.py
git commit -m "feat: add pipeline configuration"
```

---

### Task 3: Timestamp, Duration, Caller, And Release Parsing

**Files:**
- Create: `pipeline/parse.py`
- Create: `tests/test_parse.py`

- [ ] **Step 1: Write failing parsing tests**

Create `tests/test_parse.py`:

```python
import math

import pandas as pd

from pipeline.parse import normalize_caller_number, parse_csv_call_time, to_seconds


def test_to_seconds_parses_mm_ss_and_hh_mm_ss():
    assert to_seconds("00:09") == 9
    assert to_seconds("04:58") == 298
    assert to_seconds("1:02:03") == 3723


def test_to_seconds_treats_ms_artifact_and_bad_values_as_missing():
    assert math.isnan(to_seconds("53ms"))
    assert math.isnan(to_seconds(""))
    assert math.isnan(to_seconds(None))
    assert math.isnan(to_seconds("bad"))


def test_parse_csv_call_time_uses_sonar_format():
    parsed = parse_csv_call_time(pd.Series(["04/01/2026 8:33 am", "04/30/2026 3:40 pm"]))
    assert str(parsed.iloc[0]) == "2026-04-01 08:33:00"
    assert str(parsed.iloc[1]) == "2026-04-30 15:40:00"


def test_normalize_caller_number_does_not_aggregate_restricted():
    assert normalize_caller_number("905-283-3500") == "9052833500"
    assert normalize_caller_number("+1 (905) 283-3500") == "19052833500"
    assert normalize_caller_number("Restricted").startswith("__restricted__:")
    assert normalize_caller_number(None).startswith("__restricted__:")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_parse.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'pipeline.parse'`.

- [ ] **Step 3: Implement parsing module**

Create `pipeline/parse.py`:

```python
from __future__ import annotations

import math
import re
from typing import Any

import pandas as pd


def to_seconds(value: Any) -> float:
    if value is None or pd.isna(value):
        return math.nan
    s = str(value).strip()
    if not s or s.endswith("ms"):
        return math.nan
    parts = s.split(":")
    try:
        nums = [int(part) for part in parts]
    except ValueError:
        return math.nan
    if len(nums) == 2:
        return float(nums[0] * 60 + nums[1])
    if len(nums) == 3:
        return float(nums[0] * 3600 + nums[1] * 60 + nums[2])
    return math.nan


def parse_csv_call_time(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, format="%m/%d/%Y %I:%M %p", errors="raise")


def normalize_caller_number(value: Any, row_key: str | int | None = None) -> str:
    if value is None or pd.isna(value):
        return f"__restricted__:{row_key if row_key is not None else 'missing'}"
    text = str(value).strip()
    if not text or text.lower() == "restricted":
        return f"__restricted__:{row_key if row_key is not None else text.lower() or 'missing'}"
    digits = re.sub(r"\\D+", "", text)
    if not digits:
        return f"__restricted__:{row_key if row_key is not None else 'nondigit'}"
    return digits
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_parse.py -v`

Expected: PASS.

- [ ] **Step 5: Commit parsing**

```bash
git add pipeline/parse.py tests/test_parse.py
git commit -m "feat: add call field parsing"
```

---

### Task 4: Deduplication Rules

**Files:**
- Create: `pipeline/dedup.py`
- Create: `tests/test_dedup.py`

- [ ] **Step 1: Write failing dedup tests**

Create `tests/test_dedup.py`:

```python
import pandas as pd

from pipeline.dedup import deduplicate_api, deduplicate_csv


def test_deduplicate_csv_drops_junk_columns_and_keeps_last_orig_call_id():
    df = pd.DataFrame(
        [
            {"Unnamed: 0": 1, "Orig CallID": "a", "Agent Name": "First", "Unnamed: 17": None},
            {"Unnamed: 0": 2, "Orig CallID": "a", "Agent Name": "Last", "Unnamed: 17": None},
            {"Unnamed: 0": 3, "Orig CallID": "b", "Agent Name": "Only", "Unnamed: 17": None},
        ]
    )
    out = deduplicate_csv(df)
    assert list(out["Orig CallID"]) == ["a", "b"]
    assert list(out["Agent Name"]) == ["Last", "Only"]
    assert "Unnamed: 0" not in out.columns
    assert "Unnamed: 17" not in out.columns


def test_deduplicate_api_sorts_to_call_id_and_keeps_last_from_call_id():
    df = pd.DataFrame(
        [
            {"from.call_id": "root", "to.call_id": "20260401101000000000-b", "agent": "Last"},
            {"from.call_id": "root", "to.call_id": "20260401100000000000-a", "agent": "First"},
            {"from.call_id": "other", "to.call_id": "20260401102000000000-c", "agent": "Only"},
        ]
    )
    out = deduplicate_api(df)
    assert list(out["from.call_id"]) == ["root", "other"]
    assert list(out["agent"]) == ["Last", "Only"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_dedup.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'pipeline.dedup'`.

- [ ] **Step 3: Implement dedup module**

Create `pipeline/dedup.py`:

```python
from __future__ import annotations

import pandas as pd


def deduplicate_csv(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.drop(columns=[c for c in ["Unnamed: 0", "Unnamed: 17"] if c in df.columns], errors="ignore")
    return cleaned.drop_duplicates(subset=["Orig CallID"], keep="last").reset_index(drop=True)


def deduplicate_api(df: pd.DataFrame) -> pd.DataFrame:
    ordered = df
    if "to.call_id" in ordered.columns:
        ordered = ordered.sort_values("to.call_id", kind="stable")
    elif "start_time" in ordered.columns:
        ordered = ordered.sort_values("start_time", kind="stable")
    return ordered.drop_duplicates(subset=["from.call_id"], keep="last").reset_index(drop=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_dedup.py -v`

Expected: PASS.

- [ ] **Step 5: Commit dedup**

```bash
git add pipeline/dedup.py tests/test_dedup.py
git commit -m "feat: add verified deduplication rules"
```

---

### Task 5: CSV Ingestion For Four Queues

**Files:**
- Create: `pipeline/ingest_csv.py`
- Create: `tests/test_ingest_csv.py`

- [ ] **Step 1: Write failing CSV ingestion tests**

Create `tests/test_ingest_csv.py`:

```python
from pathlib import Path

import pandas as pd

from pipeline.config import QueueConfig
from pipeline.ingest_csv import find_queue_csv, load_queue_csv


def test_find_queue_csv_matches_queue_id(tmp_path: Path):
    path = tmp_path / "queue_details_2026-04-01_2026-04-30_8020_undefined.csv"
    path.write_text("Call Time,Orig CallID\\n04/01/2026 8:33 am,a\\n")
    found = find_queue_csv(tmp_path, "8020")
    assert found == path


def test_load_queue_csv_adds_source_metadata(tmp_path: Path):
    path = tmp_path / "queue_details_2026-04-01_2026-04-30_8020_undefined.csv"
    pd.DataFrame([{"Call Time": "04/01/2026 8:33 am", "Orig CallID": "a"}]).to_csv(path, index=False)
    queue = QueueConfig("8020", "CSR English", "English", "primary")
    df = load_queue_csv(path, queue)
    assert df.loc[0, "source_queue_id"] == "8020"
    assert df.loc[0, "source_queue_name"] == "CSR English"
    assert df.loc[0, "source_language"] == "English"
    assert df.loc[0, "source_role"] == "primary"
    assert df.loc[0, "source_file"].endswith("_8020_undefined.csv")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ingest_csv.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'pipeline.ingest_csv'`.

- [ ] **Step 3: Implement CSV ingestion**

Create `pipeline/ingest_csv.py`:

```python
from __future__ import annotations

from pathlib import Path

import pandas as pd

from pipeline.config import QueueConfig


def find_queue_csv(csv_dir: Path, queue_id: str) -> Path:
    matches = sorted(csv_dir.glob(f"*_{queue_id}_*.csv"))
    if not matches:
        raise FileNotFoundError(f"No CSV found for queue {queue_id} in {csv_dir}")
    if len(matches) > 1:
        names = ", ".join(path.name for path in matches)
        raise ValueError(f"Multiple CSV files found for queue {queue_id}: {names}")
    return matches[0]


def load_queue_csv(path: Path, queue: QueueConfig) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["source_queue_id"] = queue.queue_id
    df["source_queue_name"] = queue.name
    df["source_language"] = queue.language
    df["source_role"] = queue.role
    df["source_file"] = str(path)
    return df
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ingest_csv.py -v`

Expected: PASS.

- [ ] **Step 5: Commit CSV ingestion**

```bash
git add pipeline/ingest_csv.py tests/test_ingest_csv.py
git commit -m "feat: add csv queue ingestion"
```

---

### Task 6: Curated Calls Schema

**Files:**
- Create: `pipeline/curate.py`
- Create: `tests/test_curate.py`

- [ ] **Step 1: Write failing curated schema tests**

Create `tests/test_curate.py`:

```python
import pandas as pd

from pipeline.curate import curate_csv_calls


def test_curate_csv_calls_adds_derived_fields_and_handled_flag():
    raw = pd.DataFrame(
        [
            {
                "Call Time": "04/01/2026 8:33 am",
                "Caller Number": "905-283-3500",
                "Orig CallID": "a",
                "Time in Queue": "00:09",
                "Agent Name": "Alicia Yameen",
                "Agent Time": "04:04",
                "Hold Time": "00:00",
                "Queue Release Reason": "Orig: Bye",
                "Agent Release Reason": "Orig: Bye",
                "source_queue_id": "8020",
                "source_queue_name": "CSR English",
                "source_language": "English",
                "source_role": "primary",
            },
            {
                "Call Time": "04/01/2026 8:35 am",
                "Caller Number": "Restricted",
                "Orig CallID": "b",
                "Time in Queue": "00:10",
                "Agent Name": None,
                "Agent Time": "00:00",
                "Hold Time": "00:00",
                "Queue Release Reason": "No Answer",
                "Agent Release Reason": "No Answer",
                "source_queue_id": "8020",
                "source_queue_name": "CSR English",
                "source_language": "English",
                "source_role": "primary",
            },
        ]
    )
    out = curate_csv_calls(raw)
    assert list(out["queue_id"]) == ["8020", "8020"]
    assert list(out["call_id"]) == ["a", "b"]
    assert list(out["handled_flag"]) == ["Handled", "No Talk Time"]
    assert out.loc[0, "queue_sec"] == 9
    assert out.loc[0, "agent_sec"] == 244
    assert out.loc[0, "date"] == "2026-04-01"
    assert out.loc[0, "hour"] == 8
    assert out.loc[0, "dow"] == "Wednesday"
    assert out.loc[1, "caller_number_norm"].startswith("__restricted__:")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_curate.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'pipeline.curate'`.

- [ ] **Step 3: Implement curated calls**

Create `pipeline/curate.py`:

```python
from __future__ import annotations

import pandas as pd

from pipeline.parse import normalize_caller_number, parse_csv_call_time, to_seconds


def curate_csv_calls(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame()
    call_dt = parse_csv_call_time(df["Call Time"])
    out["queue_id"] = df["source_queue_id"].astype(str)
    out["queue_name"] = df["source_queue_name"]
    out["language"] = df["source_language"]
    out["role"] = df["source_role"]
    out["call_id"] = df["Orig CallID"].astype(str)
    out["call_time"] = df["Call Time"]
    out["call_datetime"] = call_dt
    out["date"] = call_dt.dt.strftime("%Y-%m-%d")
    out["hour"] = call_dt.dt.hour
    out["dow"] = call_dt.dt.day_name()
    out["caller_name"] = df.get("Caller Name")
    out["caller_number"] = df["Caller Number"]
    out["caller_number_norm"] = [
        normalize_caller_number(value, row_key=call_id)
        for value, call_id in zip(df["Caller Number"], df["Orig CallID"], strict=False)
    ]
    out["dnis"] = df.get("DNIS")
    out["agent_extension"] = df.get("Agent Extension")
    out["agent_phone"] = df.get("Agent Phone")
    out["agent_name"] = df.get("Agent Name")
    out["queue_sec"] = df["Time in Queue"].map(to_seconds)
    out["agent_sec"] = df["Agent Time"].map(to_seconds)
    out["hold_sec"] = df["Hold Time"].map(to_seconds)
    out["agent_release_reason"] = df.get("Agent Release Reason")
    out["queue_release_reason"] = df.get("Queue Release Reason")
    out["handled_flag"] = out["agent_sec"].fillna(0).gt(0).map({True: "Handled", False: "No Talk Time"})
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_curate.py -v`

Expected: PASS.

- [ ] **Step 5: Commit curated calls**

```bash
git add pipeline/curate.py tests/test_curate.py
git commit -m "feat: add curated call schema"
```

---

### Task 7: Per-Queue Metrics

**Files:**
- Create: `pipeline/metrics_queue.py`
- Create: `tests/conftest.py`
- Create: `tests/test_metrics_queue.py`

- [ ] **Step 1: Write failing per-queue metric tests**

Create `tests/conftest.py`:

```python
import pandas as pd
import pytest


@pytest.fixture
def curated_sample() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"queue_id": "8020", "date": "2026-04-01", "hour": 8, "dow": "Wednesday", "call_id": "a", "agent_name": "Alicia", "agent_sec": 244.0, "queue_sec": 9.0, "hold_sec": 0.0, "caller_number_norm": "9052833500", "queue_release_reason": "Orig: Bye", "agent_release_reason": "Orig: Bye", "handled_flag": "Handled"},
            {"queue_id": "8020", "date": "2026-04-01", "hour": 9, "dow": "Wednesday", "call_id": "b", "agent_name": None, "agent_sec": 0.0, "queue_sec": 10.0, "hold_sec": 0.0, "caller_number_norm": "1112223333", "queue_release_reason": "No Answer", "agent_release_reason": "No Answer", "handled_flag": "No Talk Time"},
            {"queue_id": "8020", "date": "2026-04-02", "hour": 9, "dow": "Thursday", "call_id": "c", "agent_name": "Alicia", "agent_sec": 300.0, "queue_sec": 7.0, "hold_sec": 20.0, "caller_number_norm": "9052833500", "queue_release_reason": "Term: Bye", "agent_release_reason": "Term: Bye", "handled_flag": "Handled"},
        ]
    )
```

Create `tests/test_metrics_queue.py`:

```python
from pipeline.metrics_queue import compute_queue_metrics


def test_compute_queue_metrics_headlines(curated_sample):
    metrics = compute_queue_metrics(curated_sample, "8020")
    assert metrics["queue_id"] == "8020"
    assert metrics["total_calls"] == 3
    assert metrics["handled_calls"] == 2
    assert metrics["no_agent_calls"] == 1
    assert metrics["no_agent_rate"] == 1 / 3
    assert metrics["days_with_calls"] == 2
    assert metrics["busiest_day"] == {"date": "2026-04-01", "calls": 2}
    assert metrics["quietest_day"] == {"date": "2026-04-02", "calls": 1}


def test_compute_queue_metrics_series_and_leaderboards(curated_sample):
    metrics = compute_queue_metrics(curated_sample, "8020")
    assert metrics["daily_volume"][0] == {"date": "2026-04-01", "calls": 2}
    assert metrics["hourly_volume"][1]["hour"] == 9
    assert metrics["hourly_volume"][1]["calls"] == 2
    assert metrics["hourly_volume"][1]["no_answer_rate"] == 0.5
    assert metrics["agent_leaderboard"][0]["agent_name"] == "Alicia"
    assert metrics["agent_leaderboard"][0]["calls"] == 2
    assert metrics["top_callers"][0]["caller_number_norm"] == "9052833500"
    assert metrics["top_callers"][0]["calls"] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_metrics_queue.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'pipeline.metrics_queue'`.

- [ ] **Step 3: Implement per-queue metrics**

Create `pipeline/metrics_queue.py`:

```python
from __future__ import annotations

import pandas as pd


def compute_queue_metrics(curated: pd.DataFrame, queue_id: str) -> dict:
    df = curated[curated["queue_id"].astype(str) == str(queue_id)].copy()
    handled = df[df["agent_name"].notna()]
    daily = df.groupby("date").size().rename("calls").reset_index()
    daily_records = daily.sort_values("date").to_dict("records")
    hourly = (
        df.assign(no_answer=df["agent_name"].isna())
        .groupby("hour")
        .agg(calls=("call_id", "count"), no_answer_count=("no_answer", "sum"))
        .reset_index()
    )
    hourly["no_answer_rate"] = hourly["no_answer_count"] / hourly["calls"]

    agent = (
        handled.groupby("agent_name")
        .agg(calls=("call_id", "count"), avg_sec=("agent_sec", "mean"), median_sec=("agent_sec", "median"), total_sec=("agent_sec", "sum"))
        .reset_index()
        .sort_values(["calls", "agent_name"], ascending=[False, True])
    )
    if not agent.empty:
        agent["pct_of_answered"] = agent["calls"] / agent["calls"].sum()

    callers = (
        df[~df["caller_number_norm"].astype(str).str.startswith("__restricted__:")]
        .groupby("caller_number_norm")
        .size()
        .rename("calls")
        .reset_index()
        .sort_values(["calls", "caller_number_norm"], ascending=[False, True])
    )

    busiest = daily.sort_values(["calls", "date"], ascending=[False, True]).iloc[0].to_dict()
    quietest = daily.sort_values(["calls", "date"], ascending=[True, True]).iloc[0].to_dict()

    return {
        "queue_id": str(queue_id),
        "total_calls": int(len(df)),
        "handled_calls": int(len(handled)),
        "no_agent_calls": int(df["agent_name"].isna().sum()),
        "no_agent_rate": float(df["agent_name"].isna().sum() / len(df)) if len(df) else 0.0,
        "days_with_calls": int(daily["date"].nunique()),
        "avg_calls_per_active_day": float(len(df) / daily["date"].nunique()) if len(daily) else 0.0,
        "busiest_day": {"date": str(busiest["date"]), "calls": int(busiest["calls"])},
        "quietest_day": {"date": str(quietest["date"]), "calls": int(quietest["calls"])},
        "daily_volume": [{"date": str(r["date"]), "calls": int(r["calls"])} for r in daily_records],
        "hourly_volume": [
            {"hour": int(r["hour"]), "calls": int(r["calls"]), "no_answer_count": int(r["no_answer_count"]), "no_answer_rate": float(r["no_answer_rate"])}
            for r in hourly.sort_values("hour").to_dict("records")
        ],
        "agent_leaderboard": [
            {
                "agent_name": str(r["agent_name"]),
                "calls": int(r["calls"]),
                "avg_sec": float(r["avg_sec"]),
                "median_sec": float(r["median_sec"]),
                "total_sec": float(r["total_sec"]),
                "pct_of_answered": float(r["pct_of_answered"]),
            }
            for r in agent.to_dict("records")
        ],
        "top_callers": [
            {"caller_number_norm": str(r["caller_number_norm"]), "calls": int(r["calls"])}
            for r in callers.head(10).to_dict("records")
        ],
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_metrics_queue.py -v`

Expected: PASS.

- [ ] **Step 5: Commit per-queue metrics**

```bash
git add pipeline/metrics_queue.py tests/conftest.py tests/test_metrics_queue.py
git commit -m "feat: add per-queue metrics"
```

---

### Task 8: Cross-Queue Funnel, Agent, Caller, And Comparative Metrics

**Files:**
- Create: `pipeline/crossqueue.py`
- Create: `tests/test_crossqueue.py`

- [ ] **Step 1: Write failing cross-queue tests**

Create `tests/test_crossqueue.py`:

```python
import pandas as pd

from pipeline.crossqueue import compute_crossqueue_metrics


def test_compute_crossqueue_metrics_funnel_and_consolidation():
    df = pd.DataFrame(
        [
            {"queue_id": "8020", "language": "English", "role": "primary", "call_id": "en1", "agent_name": "Gabriel Hubert", "caller_number_norm": "9052833500", "date": "2026-04-01", "hour": 8},
            {"queue_id": "8020", "language": "English", "role": "primary", "call_id": "en2", "agent_name": None, "caller_number_norm": "9052833500", "date": "2026-04-01", "hour": 9},
            {"queue_id": "8030", "language": "English", "role": "overflow", "call_id": "en2o", "agent_name": None, "caller_number_norm": "9052833500", "date": "2026-04-01", "hour": 9},
            {"queue_id": "8021", "language": "French", "role": "primary", "call_id": "fr1", "agent_name": None, "caller_number_norm": "8197908197", "date": "2026-04-01", "hour": 8},
            {"queue_id": "8031", "language": "French", "role": "overflow", "call_id": "fr1o", "agent_name": "Gabriel Hubert", "caller_number_norm": "8197908197", "date": "2026-04-01", "hour": 8},
        ]
    )
    metrics = compute_crossqueue_metrics(df)
    english = metrics["funnels"]["English"]
    assert english["primary_calls"] == 2
    assert english["primary_answered"] == 1
    assert english["primary_failed"] == 1
    assert english["overflow_received"] == 1
    assert english["overflow_failed"] == 1
    assert english["effective_answer_rate"] == 0.5
    assert metrics["agents"][0]["agent_name"] == "Gabriel Hubert"
    assert metrics["agents"][0]["total_calls"] == 2
    assert metrics["callers"][0]["caller_number_norm"] == "9052833500"
    assert metrics["callers"][0]["total_calls"] == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_crossqueue.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'pipeline.crossqueue'`.

- [ ] **Step 3: Implement cross-queue metrics**

Create `pipeline/crossqueue.py`:

```python
from __future__ import annotations

import pandas as pd


def compute_crossqueue_metrics(curated: pd.DataFrame) -> dict:
    funnels = {language: _language_funnel(curated, language) for language in ["English", "French"]}
    return {
        "funnels": funnels,
        "agents": _consolidated_agents(curated),
        "callers": _consolidated_callers(curated),
        "same_hour_no_answer": _same_hour_no_answer(curated),
        "same_day_volume": _same_day_volume(curated),
    }


def _language_funnel(curated: pd.DataFrame, language: str) -> dict:
    lang = curated[curated["language"] == language]
    primary = lang[lang["role"] == "primary"]
    overflow = lang[lang["role"] == "overflow"]
    primary_calls = len(primary)
    primary_answered = int(primary["agent_name"].notna().sum())
    primary_failed = primary_calls - primary_answered
    overflow_received = len(overflow)
    overflow_answered = int(overflow["agent_name"].notna().sum())
    overflow_failed = overflow_received - overflow_answered
    final_answered = primary_answered + overflow_answered
    return {
        "primary_calls": int(primary_calls),
        "primary_answered": int(primary_answered),
        "primary_failed": int(primary_failed),
        "overflow_received": int(overflow_received),
        "routing_match": float(overflow_received / primary_failed) if primary_failed else 0.0,
        "overflow_answered": int(overflow_answered),
        "overflow_failed": int(overflow_failed),
        "lost": int(overflow_failed),
        "lost_rate": float(overflow_failed / primary_calls) if primary_calls else 0.0,
        "effective_answer_rate": float(final_answered / primary_calls) if primary_calls else 0.0,
        "unaccounted": int(primary_failed - overflow_received),
    }


def _consolidated_agents(curated: pd.DataFrame) -> list[dict]:
    handled = curated[curated["agent_name"].notna()]
    if handled.empty:
        return []
    pivot = handled.pivot_table(index="agent_name", columns="queue_id", values="call_id", aggfunc="count", fill_value=0)
    pivot["total_calls"] = pivot.sum(axis=1)
    rows = pivot.reset_index().sort_values(["total_calls", "agent_name"], ascending=[False, True])
    return [{str(k): int(v) if isinstance(v, (int, float)) and k != "agent_name" else v for k, v in row.items()} for row in rows.to_dict("records")]


def _consolidated_callers(curated: pd.DataFrame) -> list[dict]:
    callers = curated[~curated["caller_number_norm"].astype(str).str.startswith("__restricted__:")]
    if callers.empty:
        return []
    pivot = callers.pivot_table(index="caller_number_norm", columns="queue_id", values="call_id", aggfunc="count", fill_value=0)
    pivot["total_calls"] = pivot.sum(axis=1)
    rows = pivot.reset_index().sort_values(["total_calls", "caller_number_norm"], ascending=[False, True])
    return [{str(k): int(v) if isinstance(v, (int, float)) and k != "caller_number_norm" else v for k, v in row.items()} for row in rows.to_dict("records")]


def _same_hour_no_answer(curated: pd.DataFrame) -> list[dict]:
    grouped = (
        curated.assign(no_answer=curated["agent_name"].isna())
        .groupby(["queue_id", "hour"])
        .agg(calls=("call_id", "count"), no_answer_count=("no_answer", "sum"))
        .reset_index()
    )
    grouped["no_answer_rate"] = grouped["no_answer_count"] / grouped["calls"]
    return grouped.sort_values(["queue_id", "hour"]).to_dict("records")


def _same_day_volume(curated: pd.DataFrame) -> list[dict]:
    grouped = curated.groupby(["queue_id", "date"]).size().rename("calls").reset_index()
    return grouped.sort_values(["date", "queue_id"]).to_dict("records")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_crossqueue.py -v`

Expected: PASS.

- [ ] **Step 5: Commit cross-queue metrics**

```bash
git add pipeline/crossqueue.py tests/test_crossqueue.py
git commit -m "feat: add cross-queue analytics"
```

---

### Task 9: Anomaly Detection

**Files:**
- Create: `pipeline/anomaly.py`
- Create: `tests/test_anomaly.py`

- [ ] **Step 1: Write failing anomaly tests**

Create `tests/test_anomaly.py`:

```python
from pipeline.anomaly import detect_anomalies


def test_detect_anomalies_flags_system_agent_high_caller_and_single_point_agent():
    queue_metrics = {
        "8031": {
            "queue_id": "8031",
            "agent_leaderboard": [{"agent_name": "CSH - BUILDS", "calls": 11, "pct_of_answered": 0.50}],
            "hourly_volume": [{"hour": 12, "calls": 10, "no_answer_rate": 0.60}],
        },
        "8021": {
            "queue_id": "8021",
            "agent_leaderboard": [{"agent_name": "Gabriel Hubert", "calls": 24, "pct_of_answered": 0.75}],
            "hourly_volume": [{"hour": 8, "calls": 4, "no_answer_rate": 0.25}],
        },
    }
    crossqueue = {"callers": [{"caller_number_norm": "9052833500", "total_calls": 63}]}
    anomalies = detect_anomalies(queue_metrics, crossqueue, caller_threshold=20)
    descriptions = [a["description"] for a in anomalies]
    assert any("CSH - BUILDS" in d for d in descriptions)
    assert any("9052833500" in d for d in descriptions)
    assert any("Gabriel Hubert" in d and "60%" in d for d in descriptions)
    assert any("12:00" in d and "50%" in d for d in descriptions)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_anomaly.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'pipeline.anomaly'`.

- [ ] **Step 3: Implement anomaly detection**

Create `pipeline/anomaly.py`:

```python
from __future__ import annotations


def detect_anomalies(queue_metrics: dict[str, dict], crossqueue: dict, caller_threshold: int = 20) -> list[dict]:
    anomalies: list[dict] = []
    for queue_id, metrics in queue_metrics.items():
        for agent in metrics.get("agent_leaderboard", []):
            name = str(agent["agent_name"])
            share = float(agent.get("pct_of_answered", 0.0))
            if _looks_non_human_agent(name):
                anomalies.append({
                    "severity": "high",
                    "kind": "system_agent",
                    "queue_id": queue_id,
                    "description": f"{name} appears in queue {queue_id} agent leaderboard and should be verified as human or system.",
                    "target": {"view": "per-queue", "queue_id": queue_id},
                })
            if share > 0.60:
                anomalies.append({
                    "severity": "high",
                    "kind": "single_agent_dependency",
                    "queue_id": queue_id,
                    "description": f"{name} handled more than 60% of answered calls on queue {queue_id}.",
                    "target": {"view": "per-queue", "queue_id": queue_id},
                })
        for hour in metrics.get("hourly_volume", []):
            if float(hour.get("no_answer_rate", 0.0)) > 0.50:
                anomalies.append({
                    "severity": "medium",
                    "kind": "hourly_no_answer",
                    "queue_id": queue_id,
                    "description": f"Queue {queue_id} has no-answer rate above 50% at {int(hour['hour']):02d}:00.",
                    "target": {"view": "per-queue", "queue_id": queue_id},
                })
    for caller in crossqueue.get("callers", []):
        if int(caller.get("total_calls", 0)) > caller_threshold:
            number = str(caller["caller_number_norm"])
            anomalies.append({
                "severity": "medium",
                "kind": "caller_concentration",
                "description": f"Caller {number} exceeded {caller_threshold} cross-queue contacts.",
                "target": {"view": "cross-queue", "entity": number},
            })
    return anomalies


def _looks_non_human_agent(name: str) -> bool:
    words = [part for part in name.replace("-", " ").split() if part]
    return "-" in name or any(len(word) >= 3 and word.isupper() for word in words)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_anomaly.py -v`

Expected: PASS.

- [ ] **Step 5: Commit anomaly detection**

```bash
git add pipeline/anomaly.py tests/test_anomaly.py
git commit -m "feat: add anomaly detection"
```

---

### Task 10: Local DuckDB And MotherDuck Storage

**Files:**
- Create: `pipeline/storage.py`
- Create: `tests/test_storage.py`

- [ ] **Step 1: Write failing storage tests**

Create `tests/test_storage.py`:

```python
import pandas as pd

from pipeline.storage import AnalyticsStore


def test_store_creates_tables_and_replaces_period(tmp_path):
    db_path = tmp_path / "analytics.duckdb"
    store = AnalyticsStore.local(db_path)
    store.initialize_schema()
    df = pd.DataFrame(
        [{"queue_id": "8020", "call_id": "a", "date": "2026-04-01", "agent_name": "Alicia"}]
    )
    store.replace_curated_calls("2026-04-01", "2026-04-30", df)
    first = store.connection.execute("select count(*) from curated_calls").fetchone()[0]
    store.replace_curated_calls("2026-04-01", "2026-04-30", df)
    second = store.connection.execute("select count(*) from curated_calls").fetchone()[0]
    assert first == 1
    assert second == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_storage.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'pipeline.storage'`.

- [ ] **Step 3: Implement storage**

Create `pipeline/storage.py`:

```python
from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pandas as pd


class AnalyticsStore:
    def __init__(self, connection: duckdb.DuckDBPyConnection):
        self.connection = connection

    @classmethod
    def local(cls, path: Path) -> "AnalyticsStore":
        return cls(duckdb.connect(str(path)))

    @classmethod
    def motherduck(cls, database: str, token_env: str = "MOTHERDUCK_TOKEN_RW") -> "AnalyticsStore":
        token = os.environ[token_env]
        conn = duckdb.connect(f"md:{database}?motherduck_token={token}")
        return cls(conn)

    def initialize_schema(self) -> None:
        self.connection.execute(
            """
            create table if not exists curated_calls (
                period_start date,
                period_end date,
                queue_id varchar,
                call_id varchar,
                date date,
                agent_name varchar
            )
            """
        )

    def replace_curated_calls(self, start: str, end: str, df: pd.DataFrame) -> None:
        self.initialize_schema()
        self.connection.execute(
            "delete from curated_calls where period_start = ? and period_end = ?",
            [start, end],
        )
        to_write = df.copy()
        to_write.insert(0, "period_end", end)
        to_write.insert(0, "period_start", start)
        self.connection.register("curated_input", to_write)
        self.connection.execute("insert into curated_calls select * from curated_input")
        self.connection.unregister("curated_input")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_storage.py -v`

Expected: PASS.

- [ ] **Step 5: Commit storage**

```bash
git add pipeline/storage.py tests/test_storage.py
git commit -m "feat: add analytics storage"
```

---

### Task 11: Report JSON Emission

**Files:**
- Create: `pipeline/report.py`
- Create: `tests/test_report.py`

- [ ] **Step 1: Write failing report tests**

Create `tests/test_report.py`:

```python
import json

from pipeline.report import write_report_bundle


def test_write_report_bundle_emits_metrics_and_per_queue_files(tmp_path):
    queue_metrics = {"8020": {"queue_id": "8020", "total_calls": 1181}}
    crossqueue = {"funnels": {"English": {"effective_answer_rate": 0.847}}}
    anomalies = [{"severity": "medium", "description": "Caller threshold"}]
    out_dir = write_report_bundle(
        data_dir=tmp_path,
        period="month",
        start="2026-04-01",
        end="2026-04-30",
        queue_metrics=queue_metrics,
        crossqueue=crossqueue,
        anomalies=anomalies,
    )
    metrics = json.loads((out_dir / "metrics.json").read_text())
    per_queue = json.loads((out_dir / "metrics_8020.json").read_text())
    assert metrics["period"] == "month"
    assert metrics["date_range"] == {"start": "2026-04-01", "end": "2026-04-30"}
    assert metrics["queues"]["8020"]["total_calls"] == 1181
    assert metrics["crossqueue"]["funnels"]["English"]["effective_answer_rate"] == 0.847
    assert per_queue["queue_id"] == "8020"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_report.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'pipeline.report'`.

- [ ] **Step 3: Implement report writing**

Create `pipeline/report.py`:

```python
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def write_report_bundle(
    data_dir: Path,
    period: str,
    start: str,
    end: str,
    queue_metrics: dict[str, dict[str, Any]],
    crossqueue: dict[str, Any],
    anomalies: list[dict[str, Any]],
) -> Path:
    key = f"{period}_{start}_{end}"
    out_dir = data_dir / "reports" / key
    out_dir.mkdir(parents=True, exist_ok=True)
    metrics = {
        "period": period,
        "date_range": {"start": start, "end": end},
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "queues": queue_metrics,
        "crossqueue": crossqueue,
        "anomalies": anomalies,
    }
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True, default=str))
    for queue_id, payload in queue_metrics.items():
        (out_dir / f"metrics_{queue_id}.json").write_text(json.dumps(payload, indent=2, sort_keys=True, default=str))
    return out_dir
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_report.py -v`

Expected: PASS.

- [ ] **Step 5: Commit report writing**

```bash
git add pipeline/report.py tests/test_report.py
git commit -m "feat: emit report json bundle"
```

---

### Task 12: API Client, Pagination, And Field Inventory

**Files:**
- Create: `pipeline/client.py`
- Create: `pipeline/flatten.py`
- Create: `tests/test_client.py`

- [ ] **Step 1: Write failing API client tests**

Create `tests/test_client.py`:

```python
import httpx

from pipeline.client import VersatureClient
from pipeline.flatten import flatten_record, inventory_field_paths


def test_flatten_record_and_inventory_paths():
    record = {"from": {"call_id": "root", "user": "caller"}, "to": {"call_id": "leg"}, "duration": 30}
    flat = flatten_record(record)
    assert flat["from.call_id"] == "root"
    assert flat["to.call_id"] == "leg"
    assert inventory_field_paths([record]) == ["duration", "from.call_id", "from.user", "to.call_id"]


def test_client_pages_result_until_more_false():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if len(calls) == 1:
            return httpx.Response(200, json={"result": [{"id": 1}], "cursor": "abc", "more": True})
        return httpx.Response(200, json={"result": [{"id": 2}], "cursor": None, "more": False})

    transport = httpx.MockTransport(handler)
    client = VersatureClient(
        base_url="https://integrate.versature.com/api",
        api_version="application/vnd.integrate.v1.10.0+json",
        access_token="token",
        transport=transport,
    )
    rows = client.get_cdr_users("2026-04-01T00:00:00", "2026-04-02T00:00:00")
    assert rows == [{"id": 1}, {"id": 2}]
    assert "cursor=abc" in calls[1]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_client.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'pipeline.client'`.

- [ ] **Step 3: Implement API client and flattening**

Create `pipeline/flatten.py`:

```python
from __future__ import annotations

from typing import Any


def flatten_record(record: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in record.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(flatten_record(value, path))
        else:
            flat[path] = value
    return flat


def inventory_field_paths(records: list[dict[str, Any]]) -> list[str]:
    paths: set[str] = set()
    for record in records:
        paths.update(flatten_record(record).keys())
    return sorted(paths)
```

Create `pipeline/client.py`:

```python
from __future__ import annotations

import time
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


class VersatureClient:
    def __init__(
        self,
        base_url: str,
        api_version: str,
        access_token: str,
        transport: httpx.BaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(
            headers={"Authorization": f"Bearer {access_token}", "Accept": api_version},
            transport=transport,
            timeout=30.0,
        )

    def get_cdr_users(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            params = {"start_date": start_date, "end_date": end_date}
            if cursor:
                params["cursor"] = cursor
            body = self._get_json("/cdrs/users/", params=params)
            rows.extend(body["result"])
            if not body.get("more"):
                return rows
            cursor = body.get("cursor")
            time.sleep(0.5)

    @retry(retry=retry_if_exception_type(httpx.HTTPError), wait=wait_exponential(multiplier=1, max=16), stop=stop_after_attempt(5))
    def _get_json(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        response = self.client.get(f"{self.base_url}{path}", params=params)
        response.raise_for_status()
        body = response.json()
        if "result" not in body:
            raise ValueError("Expected Versature response to include top-level result")
        return body
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_client.py -v`

Expected: PASS.

- [ ] **Step 5: Commit API client**

```bash
git add pipeline/client.py pipeline/flatten.py tests/test_client.py
git commit -m "feat: add versature api client"
```

---

### Task 13: CLI Orchestration And Historical Backfill

**Files:**
- Create: `pipeline/main.py`
- Create: `tests/test_main.py`

- [ ] **Step 1: Write failing CLI argument tests**

Create `tests/test_main.py`:

```python
from pipeline.main import parse_args


def test_parse_args_supports_backfill_dates():
    args = parse_args(["--source", "csv", "--period", "month", "--start", "2025-01-01", "--end", "2025-01-31"])
    assert args.source == "csv"
    assert args.period == "month"
    assert args.start == "2025-01-01"
    assert args.end == "2025-01-31"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_main.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'pipeline.main'`.

- [ ] **Step 3: Implement CLI parser and CSV orchestration**

Create `pipeline/main.py`:

```python
from __future__ import annotations

import argparse

import pandas as pd

from pipeline.anomaly import detect_anomalies
from pipeline.config import AppConfig
from pipeline.crossqueue import compute_crossqueue_metrics
from pipeline.curate import curate_csv_calls
from pipeline.dedup import deduplicate_csv
from pipeline.ingest_csv import find_queue_csv, load_queue_csv
from pipeline.metrics_queue import compute_queue_metrics
from pipeline.report import write_report_bundle


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="NeoLore queue analytics pipeline")
    parser.add_argument("--source", choices=["csv", "api", "hybrid"], required=True)
    parser.add_argument("--period", choices=["day", "week", "month"], required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    return parser.parse_args(argv)


def run_csv(config: AppConfig, period: str, start: str, end: str):
    curated_frames = []
    for queue in config.queues:
        path = find_queue_csv(config.csv_dir, queue.queue_id)
        raw = load_queue_csv(path, queue)
        deduped = deduplicate_csv(raw)
        curated_frames.append(curate_csv_calls(deduped))
    curated = pd.concat(curated_frames, ignore_index=True)
    queue_metrics = {queue.queue_id: compute_queue_metrics(curated, queue.queue_id) for queue in config.queues}
    crossqueue = compute_crossqueue_metrics(curated)
    anomalies = detect_anomalies(queue_metrics, crossqueue)
    return write_report_bundle(config.data_dir, period, start, end, queue_metrics, crossqueue, anomalies)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config = AppConfig.from_env()
    if args.source != "csv":
        raise SystemExit("Only CSV orchestration is executable at this milestone; API and hybrid modules are implemented separately.")
    run_csv(config, args.period, args.start, args.end)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run CLI test to verify it passes**

Run: `pytest tests/test_main.py -v`

Expected: PASS.

- [ ] **Step 5: Run all unit tests**

Run: `pytest`

Expected: PASS for all synthetic tests.

- [ ] **Step 6: Commit CLI**

```bash
git add pipeline/main.py tests/test_main.py
git commit -m "feat: add csv pipeline cli"
```

---

### Task 14: April 2026 Reference Validation

**Files:**
- Create: `tests/test_april_2026_reference.py`

- [ ] **Step 1: Write reference validation tests that skip when full source set is unavailable**

Create `tests/test_april_2026_reference.py`:

```python
from pathlib import Path

import pytest

from pipeline.config import AppConfig
from pipeline.main import run_csv


REQUIRED_QUEUE_IDS = ["8020", "8021", "8030", "8031"]


def _has_all_april_csvs(csv_dir: Path) -> bool:
    return all(list(csv_dir.glob(f"*_{queue_id}_*.csv")) for queue_id in REQUIRED_QUEUE_IDS)


def test_april_2026_reference_csv_metrics(monkeypatch, tmp_path):
    cfg = AppConfig.from_env()
    if not _has_all_april_csvs(cfg.csv_dir):
        pytest.skip("Full April 2026 four-queue CSV source set is not available")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    cfg = AppConfig.from_env()
    out_dir = run_csv(cfg, "month", "2026-04-01", "2026-04-30")
    metrics_path = out_dir / "metrics.json"
    assert metrics_path.exists()

    import json

    metrics = json.loads(metrics_path.read_text())
    assert metrics["queues"]["8020"]["total_calls"] == 1181
    assert metrics["queues"]["8021"]["total_calls"] == 66
    assert metrics["queues"]["8030"]["total_calls"] == 343
    assert metrics["queues"]["8031"]["total_calls"] == 30
    assert round(metrics["crossqueue"]["funnels"]["English"]["routing_match"], 3) == 0.988
    assert round(metrics["crossqueue"]["funnels"]["French"]["routing_match"], 3) == 0.882
    assert round(metrics["crossqueue"]["funnels"]["English"]["effective_answer_rate"], 3) == 0.847
    assert round(metrics["crossqueue"]["funnels"]["French"]["effective_answer_rate"], 3) == 0.879
    assert metrics["crossqueue"]["agents"][0]["agent_name"] == "Gabriel Hubert"
    assert metrics["crossqueue"]["agents"][0]["total_calls"] == 299
    top_callers = {row["caller_number_norm"]: row["total_calls"] for row in metrics["crossqueue"]["callers"]}
    assert top_callers["9052833500"] == 63
```

- [ ] **Step 2: Run reference test**

Run: `pytest tests/test_april_2026_reference.py -v`

Expected without all four source files: SKIPPED with `Full April 2026 four-queue CSV source set is not available`.

Expected with all four source files: PASS exactly or FAIL with the specific mismatched metric.

- [ ] **Step 3: Commit reference validation**

```bash
git add tests/test_april_2026_reference.py
git commit -m "test: add april reference validation"
```

---

### Task 15: Final Data Foundation Verification

**Files:**
- Modify only if verification reveals a defect in earlier tasks.

- [ ] **Step 1: Run full synthetic test suite**

Run: `pytest`

Expected: PASS, with the April reference test skipped only when the complete four-queue source set is absent.

- [ ] **Step 2: Run CSV pipeline if all four April files are present**

Run: `python -m pipeline.main --source csv --period month --start 2026-04-01 --end 2026-04-30`

Expected with all four source files: report bundle appears under `data/reports/month_2026-04-01_2026-04-30/`.

Expected without all four source files: command fails with a clear missing queue CSV error naming the queue.

- [ ] **Step 3: Verify generated report contract if run succeeded**

Run: `python -m json.tool data/reports/month_2026-04-01_2026-04-30/metrics.json`

Expected: valid JSON containing `period`, `date_range`, `queues`, `crossqueue`, and `anomalies`.

- [ ] **Step 4: Commit verification fixes**

If Step 1 or Step 2 exposed a defect, fix it in the smallest relevant module and commit:

```bash
git add pipeline tests
git commit -m "fix: stabilize data foundation verification"
```

If no fixes were needed, do not create an empty commit.

---

## Self-Review

Spec coverage:

- Four queue topology: Task 2.
- CSV ingestion first: Tasks 5, 13, 14.
- API/hybrid readiness: Task 12 plus the CLI source-mode boundary in Task 13.
- Deduplication: Task 4.
- Parsing: Task 3 and Task 6.
- Per-queue metrics: Task 7.
- Cross-queue metrics: Task 8.
- Anomalies: Task 9.
- MotherDuck/local DuckDB storage: Task 10.
- Report JSON bundle: Task 11.
- Historical backfill: Task 13.
- April reference validation: Task 14.

Intentional follow-on scope:

- Backend API endpoints and React + Vite dashboard are deferred to the next implementation plan, after this plan produces a stable data/report contract.

Placeholder scan:

- No vague markers or unnamed implementation work remains.
- Each task names exact files, tests, commands, and expected results.

Type consistency:

- Queue IDs are strings across config, ingestion, curation, metrics, and tests.
- Curated call columns used by metrics are defined in `pipeline/curate.py`.
- Report shape used by validation is produced by `pipeline/report.py`.
