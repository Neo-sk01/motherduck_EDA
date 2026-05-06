from __future__ import annotations

import json
from datetime import datetime, timezone
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
    return out_dir
