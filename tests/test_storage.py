import pandas as pd

from pipeline.config import QueueConfig
from pipeline.curate import curate_csv_calls
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


def test_store_accepts_real_curated_dataframe(tmp_path):
    db_path = tmp_path / "analytics.duckdb"
    store = AnalyticsStore.local(db_path)
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
            }
        ]
    )
    curated = curate_csv_calls(raw)
    store.replace_curated_calls("2026-04-01", "2026-04-30", curated)
    row = store.connection.execute(
        "select queue_name, language, role, queue_sec, handled_flag from curated_calls"
    ).fetchone()
    assert row == ("CSR English", "English", "primary", 9.0, "Handled")


def test_replace_curated_calls_rolls_back_on_insert_failure(tmp_path):
    db_path = tmp_path / "analytics.duckdb"
    store = AnalyticsStore.local(db_path)
    good = pd.DataFrame([{"queue_id": "8020", "call_id": "a", "date": "2026-04-01", "agent_name": "Alicia"}])
    store.replace_curated_calls("2026-04-01", "2026-04-30", good)

    bad = pd.DataFrame([{"queue_id": "8020", "call_id": "b", "date": "not-a-date", "agent_name": "Broken"}])
    try:
        store.replace_curated_calls("2026-04-01", "2026-04-30", bad)
    except Exception:
        pass
    else:
        raise AssertionError("bad replacement should fail")

    rows = store.connection.execute(
        "select call_id, agent_name from curated_calls where period_start = '2026-04-01'"
    ).fetchall()
    assert rows == [("a", "Alicia")]


def test_store_replaces_raw_rows_queue_dimension_and_dashboard_outputs(tmp_path):
    store = AnalyticsStore.local(tmp_path / "analytics.duckdb")
    queues = (
        QueueConfig("8020", "CSR English", "English", "primary"),
        QueueConfig("8030", "CSR Overflow English", "English", "overflow"),
    )
    raw = pd.DataFrame(
        [
            {"source_queue_id": "8020", "Orig CallID": "duplicate", "source_file": "8020.csv", "Call Time": "04/01/2026 8:33 am"},
            {"source_queue_id": "8020", "Orig CallID": "duplicate", "source_file": "8020.csv", "Call Time": "04/01/2026 8:34 am"},
        ]
    )
    queue_metrics = {
        "8020": {
            "queue_id": "8020",
            "total_calls": 2,
            "daily_volume": [{"date": "2026-04-01", "calls": 2}],
            "hourly_volume": [{"hour": 8, "calls": 2, "no_answer_count": 1, "no_answer_rate": 0.5}],
            "dow_volume": [{"dow": "Wednesday", "calls": 2}],
            "agent_leaderboard": [{"agent_name": "Alicia", "calls": 1}],
            "top_callers": [{"caller_number_norm": "9052833500", "calls": 2}],
            "release_reasons": {
                "queue": [{"reason": "No Answer", "calls": 1}],
                "agent": [{"reason": "Orig: Bye", "calls": 1}],
            },
        }
    }
    crossqueue = {
        "funnels": {"English": {"primary_calls": 2, "lost": 1}},
        "agents": [{"agent_name": "Alicia", "total_calls": 1}],
        "callers": [{"caller_number_norm": "9052833500", "total_calls": 2}],
        "same_hour_no_answer": [{"queue_id": "8020", "hour": 8, "calls": 2}],
        "same_day_volume": [{"queue_id": "8020", "date": "2026-04-01", "calls": 2}],
    }
    anomalies = [{"kind": "caller_concentration", "severity": "medium", "target": {"entity": "9052833500"}}]

    store.replace_queue_dimension(queues)
    store.replace_raw_call_legs("2026-04-01", "2026-04-30", raw, "csv")
    store.replace_report_outputs("2026-04-01", "2026-04-30", "month", "csv", queue_metrics, crossqueue, anomalies)
    store.replace_report_outputs("2026-04-01", "2026-04-30", "month", "csv", queue_metrics, crossqueue, anomalies)

    counts = dict(
        store.connection.execute(
            """
            select 'queue_dim', count(*) from queue_dim
            union all select 'raw_call_legs', count(*) from raw_call_legs
            union all select 'report_runs', count(*) from report_runs
            union all select 'queue_period_metrics', count(*) from queue_period_metrics
            union all select 'queue_daily_metrics', count(*) from queue_daily_metrics
            union all select 'queue_hourly_metrics', count(*) from queue_hourly_metrics
            union all select 'queue_dow_metrics', count(*) from queue_dow_metrics
            union all select 'agent_queue_metrics', count(*) from agent_queue_metrics
            union all select 'caller_queue_metrics', count(*) from caller_queue_metrics
            union all select 'release_reason_metrics', count(*) from release_reason_metrics
            union all select 'funnel_language_metrics', count(*) from funnel_language_metrics
            union all select 'crossqueue_agent_metrics', count(*) from crossqueue_agent_metrics
            union all select 'crossqueue_caller_metrics', count(*) from crossqueue_caller_metrics
            union all select 'comparative_series', count(*) from comparative_series
            union all select 'anomalies', count(*) from anomalies
            """
        ).fetchall()
    )
    assert counts == {
        "queue_dim": 2,
        "raw_call_legs": 2,
        "report_runs": 1,
        "queue_period_metrics": 1,
        "queue_daily_metrics": 1,
        "queue_hourly_metrics": 1,
        "queue_dow_metrics": 1,
        "agent_queue_metrics": 1,
        "caller_queue_metrics": 1,
        "release_reason_metrics": 2,
        "funnel_language_metrics": 1,
        "crossqueue_agent_metrics": 1,
        "crossqueue_caller_metrics": 1,
        "comparative_series": 2,
        "anomalies": 1,
    }
