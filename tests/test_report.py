import json
import math

import pytest

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
    assert metrics["source_gaps"] == []
    assert metrics["validation"] == {"status": "success"}
    assert per_queue["queue_id"] == "8020"


def test_write_report_bundle_can_record_source_gaps(tmp_path):
    out_dir = write_report_bundle(
        data_dir=tmp_path,
        period="month",
        start="2026-02-01",
        end="2026-02-28",
        queue_metrics={},
        crossqueue={},
        anomalies=[],
        source_gaps=[{"queue_id": "8031", "reason": "missing_csv"}],
        validation={"status": "source_gap"},
    )

    metrics = json.loads((out_dir / "metrics.json").read_text())
    assert metrics["source_gaps"] == [{"queue_id": "8031", "reason": "missing_csv"}]
    assert metrics["validation"] == {"status": "source_gap"}


def test_write_report_bundle_updates_monthly_manifest(tmp_path):
    write_report_bundle(
        data_dir=tmp_path,
        period="month",
        start="2026-03-01",
        end="2026-03-31",
        queue_metrics={"8020": {"queue_id": "8020", "total_calls": 1}},
        crossqueue={},
        anomalies=[],
        source_mode="api",
    )
    write_report_bundle(
        data_dir=tmp_path,
        period="month",
        start="2026-04-01",
        end="2026-04-30",
        queue_metrics={"8020": {"queue_id": "8020", "total_calls": 2}},
        crossqueue={},
        anomalies=[],
        source_mode="csv",
    )

    manifest = json.loads((tmp_path / "reports" / "manifest.json").read_text())

    assert [row["key"] for row in manifest["reports"]] == ["2026-04", "2026-03"]
    assert manifest["reports"][0] == {
        "key": "2026-04",
        "label": "April 2026",
        "start": "2026-04-01",
        "end": "2026-04-30",
        "path": "month_2026-04-01_2026-04-30/metrics.json",
        "source": "csv",
        "validation_status": "success",
    }


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


def test_write_report_bundle_rejects_non_finite_json_values(tmp_path):
    with pytest.raises(ValueError, match="Out of range float values"):
        write_report_bundle(
            data_dir=tmp_path,
            period="month",
            start="2026-04-01",
            end="2026-04-30",
            queue_metrics={"8020": {"queue_id": "8020", "answer_rate": math.nan}},
            crossqueue={},
            anomalies=[],
        )
