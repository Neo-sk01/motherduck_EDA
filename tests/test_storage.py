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
