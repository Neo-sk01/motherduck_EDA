from __future__ import annotations

import json
from datetime import datetime, timezone
import calendar
from pathlib import Path
from typing import Any


def write_report_bundle(
    data_dir: Path,
    period: str,
    start: str,
    end: str,
    queue_metrics: dict[str, dict[str, Any]],
    crossqueue: dict[str, Any],
    anomalies: list[dict[str, Any]],
    source_gaps: list[dict[str, Any]] | None = None,
    validation: dict[str, Any] | None = None,
    source_mode: str = "csv",
) -> Path:
    key = f"{period}_{start}_{end}"
    out_dir = data_dir / "reports" / key
    out_dir.mkdir(parents=True, exist_ok=True)
    metrics = {
        "period": period,
        "date_range": {"start": start, "end": end},
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "queues": queue_metrics,
        "crossqueue": crossqueue,
        "anomalies": anomalies,
        "source_gaps": source_gaps or [],
        "validation": validation or {"status": "success"},
    }
    (out_dir / "metrics.json").write_text(
        json.dumps(metrics, allow_nan=False, indent=2, sort_keys=True)
    )
    for queue_id, payload in queue_metrics.items():
        (out_dir / f"metrics_{queue_id}.json").write_text(
            json.dumps(payload, allow_nan=False, indent=2, sort_keys=True)
        )
    if period == "month":
        _update_manifest(data_dir, start, end, source_mode, validation or {"status": "success"})
    return out_dir


def _update_manifest(data_dir: Path, start: str, end: str, source_mode: str, validation: dict[str, Any]) -> None:
    manifest_path = data_dir / "reports" / "manifest.json"
    if manifest_path.exists():
        payload = json.loads(manifest_path.read_text())
        reports = payload.get("reports", [])
        if not isinstance(reports, list):
            reports = []
    else:
        reports = []

    key = start[:7]
    entry = {
        "key": key,
        "label": _month_label(start),
        "start": start,
        "end": end,
        "path": f"/data/reports/month_{start}_{end}/metrics.json",
        "source": source_mode,
        "validation_status": str(validation.get("status", "success")),
    }
    reports = [row for row in reports if not (isinstance(row, dict) and row.get("key") == key)]
    reports.append(entry)
    reports = sorted(reports, key=lambda row: str(row.get("start", "")), reverse=True)
    manifest_path.write_text(json.dumps({"reports": reports}, allow_nan=False, indent=2, sort_keys=True))


def _month_label(start: str) -> str:
    year, month, *_ = start.split("-")
    return f"{calendar.month_name[int(month)]} {year}"
