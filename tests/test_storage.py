import pandas as pd

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
