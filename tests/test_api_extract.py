import json

import pytest

from pipeline.api_extract import load_api_extract, write_api_extract
from pipeline.config import QueueConfig


def test_write_api_extract_round_trips_records_stats_and_manifest(tmp_path):
    queues = (
        QueueConfig("8020", "CSR English", "English", "primary"),
        QueueConfig("8030", "CSR Overflow English", "English", "overflow"),
    )
    records = [
        {"from": {"call_id": "call-1"}, "start_time": "2026-03-01T09:00:00-05:00"},
        {"from": {"call_id": "call-2"}, "start_time": "2026-03-01T09:05:00-05:00"},
    ]
    stats_by_queue = {
        "8020": {"queue": "8020", "calls_offered": 2},
        "8030": {"queue": "8030", "calls_offered": 1},
    }

    extract_path = write_api_extract(
        tmp_path,
        period="month",
        start="2026-03-01",
        end="2026-03-31",
        records=records,
        stats_by_queue=stats_by_queue,
        queues=queues,
    )

    extract = load_api_extract(tmp_path, start="2026-03-01", end="2026-03-31")
    manifest = json.loads((extract_path / "manifest.json").read_text())
    assert manifest["status"] == "complete"
    assert manifest["record_count"] == 2
    assert manifest["queues_included"] == ["8020", "8030"]
    assert extract.records == records
    assert extract.stats_by_queue == stats_by_queue


def test_load_api_extract_requires_complete_manifest(tmp_path):
    extract_dir = tmp_path / "api_extracts" / "2026-03-01_2026-03-31"
    extract_dir.mkdir(parents=True)
    (extract_dir / "manifest.json").write_text(json.dumps({"status": "running"}))

    with pytest.raises(FileNotFoundError, match="No complete API extract"):
        load_api_extract(tmp_path, start="2026-03-01", end="2026-03-31")
