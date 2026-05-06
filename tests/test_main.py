import json

import pandas as pd
import pytest

from pipeline.config import AppConfig, build_default_queues
from pipeline.main import main, parse_args, run_csv
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
        "Only CSV orchestration is executable at this milestone; API and hybrid modules are "
        "implemented separately."
    )


def test_main_rejects_api_mode_before_loading_environment(monkeypatch):
    monkeypatch.setenv("SOURCE", "invalid")

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
        "Only CSV orchestration is executable at this milestone; API and hybrid modules are "
        "implemented separately."
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
