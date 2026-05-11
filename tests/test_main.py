import json

import pandas as pd
import pytest

from pipeline.api_extract import write_api_extract
from pipeline.config import AppConfig, build_default_queues
from pipeline.main import main, parse_args, run_api, run_csv
from pipeline.storage import AnalyticsStore


def _write_minimal_queue_csv(csv_dir, queue_id: str, call_time: str = "01/15/2025 8:33 am"):
    pd.DataFrame(
        [
            {
                "Call Time": call_time,
                "Orig CallID": f"call-{queue_id}",
                "Caller Number": "905-283-3500",
                "Time in Queue": "00:09",
                "Agent Time": "04:04",
                "Hold Time": "00:00",
                "Agent Name": f"Agent {queue_id}",
                "Queue Release Reason": "Orig: Bye",
                "Agent Release Reason": "Orig: Bye",
            }
        ]
    ).to_csv(csv_dir / f"calls_{queue_id}_2025-01.csv", index=False)


def _write_two_row_queue_csv(csv_dir, queue_id: str):
    pd.DataFrame(
        [
            {
                "Call Time": "01/15/2025 8:33 am",
                "Orig CallID": f"in-range-{queue_id}",
                "Caller Number": "905-283-3500",
                "Time in Queue": "00:09",
                "Agent Time": "04:04",
                "Hold Time": "00:00",
                "Agent Name": f"Agent {queue_id}",
                "Queue Release Reason": "Orig: Bye",
                "Agent Release Reason": "Orig: Bye",
            },
            {
                "Call Time": "02/01/2025 8:33 am",
                "Orig CallID": f"out-range-{queue_id}",
                "Caller Number": "604-294-1500",
                "Time in Queue": "00:11",
                "Agent Time": "00:00",
                "Hold Time": "00:00",
                "Agent Name": None,
                "Queue Release Reason": "No Answer",
                "Agent Release Reason": "No Answer",
            },
        ]
    ).to_csv(csv_dir / f"calls_{queue_id}_2025-wide.csv", index=False)


def test_parse_args_supports_backfill_dates():
    args = parse_args(
        [
            "--source",
            "csv",
            "--period",
            "month",
            "--start",
            "2025-01-01",
            "--end",
            "2025-01-31",
        ]
    )

    assert args.source == "csv"
    assert args.period == "month"
    assert args.start == "2025-01-01"
    assert args.end == "2025-01-31"
    assert args.write_store is False
    assert args.api_cache_mode == "auto"


def test_parse_args_supports_api_cache_mode():
    args = parse_args(
        [
            "--source",
            "api",
            "--period",
            "month",
            "--start",
            "2025-01-01",
            "--end",
            "2025-01-31",
            "--api-cache-mode",
            "reuse",
        ]
    )

    assert args.api_cache_mode == "reuse"


def test_run_csv_writes_report_and_optional_store_for_backfill(tmp_path):
    csv_dir = tmp_path / "csv"
    csv_dir.mkdir()
    data_dir = tmp_path / "data"
    config = AppConfig(
        motherduck_database="test_db",
        source="csv",
        csv_dir=csv_dir,
        data_dir=data_dir,
        timezone="America/Toronto",
        queues=tuple(build_default_queues()),
    )
    for queue in config.queues:
        _write_minimal_queue_csv(csv_dir, queue.queue_id)
    store = AnalyticsStore.local(tmp_path / "analytics.duckdb")

    out_dir = run_csv(
        config,
        period="month",
        start="2025-01-01",
        end="2025-01-31",
        store=store,
    )

    assert out_dir == data_dir / "reports" / "month_2025-01-01_2025-01-31"
    metrics_path = out_dir / "metrics.json"
    assert metrics_path.exists()
    metrics = json.loads(metrics_path.read_text())
    assert set(metrics["queues"]) == {"8020", "8021", "8030", "8031"}
    rows = store.connection.execute(
        """
        select count(*)
        from curated_calls
        where period_start = '2025-01-01'
          and period_end = '2025-01-31'
        """
    ).fetchone()[0]
    assert rows == 4
    warehouse_counts = dict(
        store.connection.execute(
            """
            select 'raw_call_legs', count(*) from raw_call_legs
            union all select 'queue_period_metrics', count(*) from queue_period_metrics
            union all select 'funnel_language_metrics', count(*) from funnel_language_metrics
            union all select 'release_reason_metrics', count(*) from release_reason_metrics
            union all select 'report_runs', count(*) from report_runs
            """
        ).fetchall()
    )
    assert warehouse_counts == {
        "raw_call_legs": 4,
        "queue_period_metrics": 4,
        "funnel_language_metrics": 2,
        "release_reason_metrics": 8,
        "report_runs": 1,
    }


def test_run_csv_filters_rows_outside_requested_backfill_range(tmp_path):
    csv_dir = tmp_path / "csv"
    csv_dir.mkdir()
    config = AppConfig(
        motherduck_database="test_db",
        source="csv",
        csv_dir=csv_dir,
        data_dir=tmp_path / "data",
        timezone="America/Toronto",
        queues=tuple(build_default_queues()),
    )
    for queue in config.queues:
        _write_two_row_queue_csv(csv_dir, queue.queue_id)

    out_dir = run_csv(config, period="month", start="2025-01-01", end="2025-01-31")

    metrics = json.loads((out_dir / "metrics.json").read_text())
    assert {queue_id: row["total_calls"] for queue_id, row in metrics["queues"].items()} == {
        "8020": 1,
        "8021": 1,
        "8030": 1,
        "8031": 1,
    }


def test_run_csv_records_source_gap_report_before_failing(tmp_path):
    csv_dir = tmp_path / "csv"
    csv_dir.mkdir()
    config = AppConfig(
        motherduck_database="test_db",
        source="csv",
        csv_dir=csv_dir,
        data_dir=tmp_path / "data",
        timezone="America/Toronto",
        queues=tuple(build_default_queues()),
    )
    for queue in config.queues[:3]:
        _write_minimal_queue_csv(csv_dir, queue.queue_id)

    with pytest.raises(FileNotFoundError, match="8031"):
        run_csv(config, period="month", start="2025-01-01", end="2025-01-31")

    metrics = json.loads((config.data_dir / "reports" / "month_2025-01-01_2025-01-31" / "metrics.json").read_text())
    assert metrics["validation"] == {"status": "source_gap"}
    assert metrics["source_gaps"][0]["queue_id"] == "8031"


def test_main_rejects_api_mode_at_this_milestone():
    calls = []

    def fake_run_api(config, period, start, end, store=None, client=None, api_cache_mode="auto"):
        calls.append((period, start, end, store, client, api_cache_mode))
        return config.data_dir / "reports" / f"{period}_{start}_{end}"

    pytest.importorskip("pipeline.ingest_api")
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv("VERSATURE_ACCESS_TOKEN", "token")
        monkeypatch.setattr("pipeline.main.run_api", fake_run_api)
        assert main(
            [
                "--source",
                "api",
                "--period",
                "month",
                "--start",
                "2025-01-01",
                "--end",
                "2025-01-31",
            ]
        ) == 0

    assert [(period, start, end, store, api_cache_mode) for period, start, end, store, _, api_cache_mode in calls] == [
        ("month", "2025-01-01", "2025-01-31", None, "auto")
    ]


def test_main_api_mode_rejects_invalid_environment_source_after_dispatch(monkeypatch):
    monkeypatch.setenv("SOURCE", "invalid")
    monkeypatch.setenv("VERSATURE_ACCESS_TOKEN", "token")
    monkeypatch.setattr(
        "pipeline.main.run_api",
        lambda config, period, start, end, store=None, client=None: config.data_dir / "reports" / f"{period}_{start}_{end}",
    )

    with pytest.raises(ValueError, match="SOURCE must be one of"):
        main(
            [
                "--source",
                "api",
                "--period",
                "month",
                "--start",
                "2025-01-01",
                "--end",
                "2025-01-31",
            ]
        )


def test_run_api_reopens_motherduck_store_after_long_fetch_before_writes(tmp_path, monkeypatch):
    class FakeClient:
        def get_cdr_users(self, start_date, end_date):
            return [
                {
                    "from": {"call_id": "call-1", "number": "9052833500"},
                    "to": {"call_id": "20250115101100000000-a", "user": {"name": "Agent One"}},
                    "by": {"user": "8020"},
                    "start_time": "2025-01-15T10:11:00-05:00",
                    "answer_time": "2025-01-15T10:11:09-05:00",
                    "duration": 42,
                    "queue_time": 9,
                    "hold_time": 0,
                    "release_reason": "Orig: Bye",
                }
            ]

        def get_call_queue_stats(self, queue_id, start, end):
            return {"queue": queue_id, "calls_offered": 1, "calls_forwarded": 0, "abandoned_calls": 0}

    class FakeStore:
        def __init__(self, label):
            self.label = label
            self.calls = []

        def replace_queue_dimension(self, queues):
            self.calls.append(("queue_dim", len(queues)))

        def replace_raw_call_legs(self, start, end, df, source_mode):
            self.calls.append(("raw", len(df), source_mode))

        def replace_curated_calls(self, start, end, df):
            self.calls.append(("curated", len(df)))

        def replace_report_outputs(self, *args, **kwargs):
            self.calls.append(("report", kwargs.get("validation", {}).get("status")))

    stale_store = FakeStore("stale")
    fresh_store = FakeStore("fresh")
    monkeypatch.setenv("MOTHERDUCK_TOKEN_RW", "present")
    monkeypatch.setattr("pipeline.main.AnalyticsStore.motherduck", lambda database: fresh_store)
    config = AppConfig(
        motherduck_database="test_db",
        source="api",
        csv_dir=tmp_path / "csv",
        data_dir=tmp_path / "data",
        timezone="America/Toronto",
        queues=tuple(build_default_queues()),
    )

    run_api(
        config,
        period="month",
        start="2025-01-01",
        end="2025-01-31",
        store=stale_store,
        client=FakeClient(),
    )

    assert stale_store.calls == []
    assert [call[0] for call in fresh_store.calls] == ["queue_dim", "raw", "curated", "report"]


def test_run_api_retries_retryable_motherduck_write_without_refetching_records(tmp_path, monkeypatch):
    class FakeClient:
        def __init__(self):
            self.cdr_fetches = 0

        def get_cdr_users(self, start_date, end_date):
            self.cdr_fetches += 1
            return [
                {
                    "from": {"call_id": "call-1", "number": "9052833500"},
                    "to": {"call_id": "20250115101100000000-a", "user": {"name": "Agent One"}},
                    "by": {"user": "8020"},
                    "start_time": "2025-01-15T10:11:00-05:00",
                    "answer_time": "2025-01-15T10:11:09-05:00",
                    "duration": 42,
                    "queue_time": 9,
                    "hold_time": 0,
                    "release_reason": "Orig: Bye",
                }
            ]

        def get_call_queue_stats(self, queue_id, start, end):
            return {"queue": queue_id, "calls_offered": 1, "calls_forwarded": 0, "abandoned_calls": 0}

    class FakeStore:
        def __init__(self, fail_raw=False):
            self.fail_raw = fail_raw
            self.calls = []

        def replace_queue_dimension(self, queues):
            self.calls.append(("queue_dim", len(queues)))

        def replace_raw_call_legs(self, start, end, df, source_mode):
            self.calls.append(("raw", len(df), source_mode))
            if self.fail_raw:
                raise RuntimeError("Catalog Error: Remote catalog has changed. Please rerun query.")

        def replace_curated_calls(self, start, end, df):
            self.calls.append(("curated", len(df)))

        def replace_report_outputs(self, *args, **kwargs):
            self.calls.append(("report", kwargs.get("validation", {}).get("status")))

    first_store = FakeStore(fail_raw=True)
    retry_store = FakeStore()
    stores = [first_store, retry_store]
    client = FakeClient()

    monkeypatch.setenv("MOTHERDUCK_TOKEN_RW", "present")
    monkeypatch.setattr("pipeline.main.AnalyticsStore.motherduck", lambda database: stores.pop(0))
    config = AppConfig(
        motherduck_database="test_db",
        source="api",
        csv_dir=tmp_path / "csv",
        data_dir=tmp_path / "data",
        timezone="America/Toronto",
        queues=tuple(build_default_queues()),
    )

    run_api(
        config,
        period="month",
        start="2025-01-01",
        end="2025-01-31",
        store=FakeStore(),
        client=client,
    )

    assert client.cdr_fetches == 1
    assert [call[0] for call in first_store.calls] == ["queue_dim", "raw"]
    assert [call[0] for call in retry_store.calls] == ["queue_dim", "raw", "curated", "report"]


def test_run_api_can_reuse_completed_api_extract_without_fetching_from_api(tmp_path):
    class FailIfCalledClient:
        def get_cdr_users(self, start_date, end_date):
            raise AssertionError("CDR extract should be loaded from disk")

        def get_call_queue_stats(self, queue_id, start, end):
            raise AssertionError("Queue stats should be loaded from disk")

    config = AppConfig(
        motherduck_database="test_db",
        source="api",
        csv_dir=tmp_path / "csv",
        data_dir=tmp_path / "data",
        timezone="America/Toronto",
        queues=tuple(build_default_queues()),
    )
    write_api_extract(
        config.data_dir,
        period="month",
        start="2025-01-01",
        end="2025-01-31",
        records=[
            {
                "from": {"call_id": "call-1", "number": "9052833500"},
                "to": {"call_id": "20250115101100000000-a", "user": {"name": "Agent One"}},
                "by": {"user": "8020"},
                "start_time": "2025-01-15T10:11:00-05:00",
                "answer_time": "2025-01-15T10:11:09-05:00",
                "duration": 42,
                "queue_time": 9,
                "hold_time": 0,
                "release_reason": "Orig: Bye",
            }
        ],
        stats_by_queue={
            queue.queue_id: {"queue": queue.queue_id, "calls_offered": 1, "calls_forwarded": 0, "abandoned_calls": 0}
            for queue in config.queues
        },
        queues=config.queues,
    )

    out_dir = run_api(
        config,
        period="month",
        start="2025-01-01",
        end="2025-01-31",
        client=FailIfCalledClient(),
        api_cache_mode="reuse",
    )

    metrics = json.loads((out_dir / "metrics.json").read_text())
    assert metrics["validation"]["record_count"] == 1
    assert metrics["queues"]["8020"]["total_calls"] == 1


def test_run_api_auto_mode_writes_extract_after_fetching_once(tmp_path):
    class FakeClient:
        def __init__(self):
            self.cdr_fetches = 0
            self.stats_fetches = []

        def get_cdr_users(self, start_date, end_date):
            self.cdr_fetches += 1
            return [
                {
                    "from": {"call_id": "call-1", "number": "9052833500"},
                    "to": {"call_id": "20250115101100000000-a", "user": {"name": "Agent One"}},
                    "by": {"user": "8020"},
                    "start_time": "2025-01-15T10:11:00-05:00",
                    "answer_time": "2025-01-15T10:11:09-05:00",
                    "duration": 42,
                    "queue_time": 9,
                    "hold_time": 0,
                    "release_reason": "Orig: Bye",
                }
            ]

        def get_call_queue_stats(self, queue_id, start, end):
            self.stats_fetches.append(queue_id)
            return {"queue": queue_id, "calls_offered": 1, "calls_forwarded": 0, "abandoned_calls": 0}

    config = AppConfig(
        motherduck_database="test_db",
        source="api",
        csv_dir=tmp_path / "csv",
        data_dir=tmp_path / "data",
        timezone="America/Toronto",
        queues=tuple(build_default_queues()),
    )
    client = FakeClient()

    run_api(
        config,
        period="month",
        start="2025-01-01",
        end="2025-01-31",
        client=client,
        api_cache_mode="auto",
    )

    manifest = json.loads(
        (config.data_dir / "api_extracts" / "2025-01-01_2025-01-31" / "manifest.json").read_text()
    )
    assert client.cdr_fetches == 1
    assert client.stats_fetches == ["8020", "8021", "8030", "8031"]
    assert manifest["status"] == "complete"
    assert manifest["record_count"] == 1


def test_main_write_store_opts_into_motherduck_for_api(monkeypatch):
    sentinel_store = object()
    stores = []

    def fake_run_api(config, period, start, end, store=None, client=None, api_cache_mode="auto"):
        stores.append(store)
        return config.data_dir / "reports" / f"{period}_{start}_{end}"

    monkeypatch.setenv("MOTHERDUCK_TOKEN_RW", "present")
    monkeypatch.setenv("VERSATURE_ACCESS_TOKEN", "token")
    monkeypatch.setattr("pipeline.main.run_api", fake_run_api)
    monkeypatch.setattr("pipeline.main.AnalyticsStore.motherduck", lambda database: sentinel_store)

    assert main(
        [
            "--source",
            "api",
            "--period",
            "month",
            "--start",
            "2025-01-01",
            "--end",
            "2025-01-31",
            "--write-store",
        ]
    ) == 0
    assert stores == [sentinel_store]


def test_main_api_requires_authentication_settings(monkeypatch):
    monkeypatch.delenv("VERSATURE_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("VERSATURE_CLIENT_ID", raising=False)
    monkeypatch.delenv("VERSATURE_CLIENT_SECRET", raising=False)

    with pytest.raises(SystemExit) as exc:
        main(
            [
                "--source",
                "api",
                "--period",
                "month",
                "--start",
                "2025-01-01",
                "--end",
                "2025-01-31",
            ]
        )

    assert str(exc.value) == (
        "API mode requires VERSATURE_ACCESS_TOKEN or both VERSATURE_CLIENT_ID and "
        "VERSATURE_CLIENT_SECRET."
    )


def test_main_defaults_to_report_only_even_when_motherduck_token_exists(monkeypatch):
    stores = []

    def fake_run_csv(config, period, start, end, store=None):
        stores.append(store)
        return config.data_dir / "reports" / f"{period}_{start}_{end}"

    def fail_motherduck(database):
        raise AssertionError("MotherDuck writes require explicit --write-store")

    monkeypatch.setenv("MOTHERDUCK_TOKEN_RW", "present")
    monkeypatch.setattr("pipeline.main.run_csv", fake_run_csv)
    monkeypatch.setattr("pipeline.main.AnalyticsStore.motherduck", fail_motherduck)

    assert main(["--source", "csv", "--period", "month", "--start", "2025-01-01", "--end", "2025-01-31"]) == 0
    assert stores == [None]


def test_main_write_store_opts_into_motherduck_store(monkeypatch):
    sentinel_store = object()
    stores = []

    def fake_run_csv(config, period, start, end, store=None):
        stores.append(store)
        return config.data_dir / "reports" / f"{period}_{start}_{end}"

    monkeypatch.setenv("MOTHERDUCK_TOKEN_RW", "present")
    monkeypatch.setattr("pipeline.main.run_csv", fake_run_csv)
    monkeypatch.setattr("pipeline.main.AnalyticsStore.motherduck", lambda database: sentinel_store)

    assert main(
        [
            "--source",
            "csv",
            "--period",
            "month",
            "--start",
            "2025-01-01",
            "--end",
            "2025-01-31",
            "--write-store",
        ]
    ) == 0
    assert stores == [sentinel_store]
