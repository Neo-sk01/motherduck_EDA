import json
import os
import shutil
from pathlib import Path

import pytest

from pipeline.config import AppConfig, build_default_queues
from pipeline.main import run_csv


APRIL_SOURCE_FILES = {
    "8020": "queue_details_04_01_2026 12_00 am_04_30_2026 11_59 pm_8020_undefined.csv",
    "8021": "queue_details_04_01_2026 12_00 am_04_30_2026 11_59 pm_8021_undefined.csv",
    "8030": "queue_details_04_01_2026 12_00 am_04_30_2026 11_59 pm_8030_undefined.csv",
    "8031": "queue_details_04_01_2026 12_00 am_04_30_2026 11_59 pm_8031_undefined.csv",
}


def _april_source_dir() -> Path:
    return Path(os.getenv("APRIL_2026_CSV_DIR", "/Users/neosekaleli/Downloads"))


def _copy_april_csvs(source_dir: Path, csv_dir: Path) -> None:
    missing = [
        filename
        for filename in APRIL_SOURCE_FILES.values()
        if not (source_dir / filename).exists()
    ]
    if missing:
        pytest.skip(f"Full April 2026 four-queue CSV source set is not available: {missing}")
    csv_dir.mkdir()
    for filename in APRIL_SOURCE_FILES.values():
        shutil.copy2(source_dir / filename, csv_dir / filename)


def test_april_2026_reference_csv_metrics(tmp_path):
    csv_dir = tmp_path / "csv"
    _copy_april_csvs(_april_source_dir(), csv_dir)
    config = AppConfig(
        motherduck_database="test_db",
        source="csv",
        csv_dir=csv_dir,
        data_dir=tmp_path / "data",
        timezone="America/Toronto",
        queues=tuple(build_default_queues()),
    )

    out_dir = run_csv(config, "month", "2026-04-01", "2026-04-30")
    metrics = json.loads((out_dir / "metrics.json").read_text())

    assert {queue_id: row["total_calls"] for queue_id, row in metrics["queues"].items()} == {
        "8020": 1181,
        "8021": 66,
        "8030": 343,
        "8031": 30,
    }
    assert metrics["queues"]["8020"]["handled_calls"] == 834
    assert metrics["queues"]["8020"]["no_agent_calls"] == 347

    english = metrics["crossqueue"]["funnels"]["English"]
    french = metrics["crossqueue"]["funnels"]["French"]
    assert english["primary_answered"] == 834
    assert english["primary_failed"] == 347
    assert english["overflow_received"] == 343
    assert english["overflow_answered"] == 162
    assert english["lost"] == 181
    assert round(english["routing_match"], 3) == 0.988
    assert round(english["effective_answer_rate"], 3) == 0.847
    assert french["primary_answered"] == 32
    assert french["primary_failed"] == 34
    assert french["overflow_received"] == 30
    assert french["overflow_answered"] == 22
    assert french["lost"] == 8
    assert round(french["routing_match"], 3) == 0.882
    assert round(french["effective_answer_rate"], 3) == 0.879

    gabriel = next(row for row in metrics["crossqueue"]["agents"] if row["agent_name"] == "Gabriel Hubert")
    assert gabriel == {
        "8020": 182,
        "8021": 24,
        "8030": 87,
        "8031": 6,
        "agent_name": "Gabriel Hubert",
        "total_calls": 299,
    }
    callers = {row["caller_number_norm"]: row for row in metrics["crossqueue"]["callers"]}
    assert callers["9052833500"]["total_calls"] == 63

    anomaly_kinds = {row["kind"] for row in metrics["anomalies"]}
    assert "system_agent" in anomaly_kinds
    assert "caller_concentration" in anomaly_kinds
