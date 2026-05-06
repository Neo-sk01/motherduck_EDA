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
    assert per_queue["queue_id"] == "8020"


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
