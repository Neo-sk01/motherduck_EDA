import json

import pandas as pd
import pytest

from pipeline.config import AppConfig, build_default_queues
from pipeline.main import main, parse_args, run_csv
from pipeline.storage import AnalyticsStore


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
        pd.DataFrame(
            [
                {
                    "Call Time": "01/15/2025 8:33 am",
                    "Orig CallID": f"call-{queue.queue_id}",
                    "Caller Number": "905-283-3500",
                    "Time in Queue": "00:09",
                    "Agent Time": "04:04",
                    "Hold Time": "00:00",
                    "Agent Name": f"Agent {queue.queue_id}",
                    "Queue Release Reason": "Orig: Bye",
                    "Agent Release Reason": "Orig: Bye",
                }
            ]
        ).to_csv(csv_dir / f"calls_{queue.queue_id}_2025-01.csv", index=False)
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
