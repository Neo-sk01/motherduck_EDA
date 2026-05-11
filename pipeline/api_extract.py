from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipeline.config import QueueConfig


@dataclass(frozen=True)
class ApiExtract:
    path: Path
    records: list[dict[str, Any]]
    stats_by_queue: dict[str, dict[str, Any]]
    manifest: dict[str, Any]


def api_extract_path(data_dir: Path, start: str, end: str) -> Path:
    return data_dir / "api_extracts" / f"{start}_{end}"


def api_extract_exists(data_dir: Path, start: str, end: str) -> bool:
    manifest_path = api_extract_path(data_dir, start, end) / "manifest.json"
    if not manifest_path.exists():
        return False
    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError:
        return False
    return manifest.get("status") == "complete"


def write_api_extract(
    data_dir: Path,
    period: str,
    start: str,
    end: str,
    records: list[dict[str, Any]],
    stats_by_queue: dict[str, dict[str, Any]],
    queues: tuple[QueueConfig, ...],
) -> Path:
    out_dir = api_extract_path(data_dir, start, end)
    out_dir.mkdir(parents=True, exist_ok=True)

    records_tmp = out_dir / "cdr_users.jsonl.tmp"
    records_path = out_dir / "cdr_users.jsonl"
    stats_tmp = out_dir / "queue_stats.json.tmp"
    stats_path = out_dir / "queue_stats.json"
    manifest_tmp = out_dir / "manifest.json.tmp"
    manifest_path = out_dir / "manifest.json"

    records_tmp.write_text("".join(json.dumps(record, allow_nan=False, sort_keys=True) + "\n" for record in records))
    records_tmp.replace(records_path)

    stats_tmp.write_text(json.dumps(stats_by_queue, allow_nan=False, indent=2, sort_keys=True))
    stats_tmp.replace(stats_path)

    manifest = {
        "status": "complete",
        "period": period,
        "start": start,
        "end": end,
        "record_count": len(records),
        "queue_stats_count": len(stats_by_queue),
        "queues_included": [queue.queue_id for queue in queues],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "records_path": records_path.name,
        "stats_path": stats_path.name,
    }
    manifest_tmp.write_text(json.dumps(manifest, allow_nan=False, indent=2, sort_keys=True))
    manifest_tmp.replace(manifest_path)
    return out_dir


def load_api_extract(data_dir: Path, start: str, end: str) -> ApiExtract:
    out_dir = api_extract_path(data_dir, start, end)
    manifest_path = out_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"No complete API extract exists for {start} to {end}")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("status") != "complete":
        raise FileNotFoundError(f"No complete API extract exists for {start} to {end}")

    records_path = out_dir / str(manifest.get("records_path", "cdr_users.jsonl"))
    stats_path = out_dir / str(manifest.get("stats_path", "queue_stats.json"))
    if not records_path.exists() or not stats_path.exists():
        raise FileNotFoundError(f"No complete API extract exists for {start} to {end}")

    records = [
        json.loads(line)
        for line in records_path.read_text().splitlines()
        if line.strip()
    ]
    stats_by_queue = json.loads(stats_path.read_text())
    if not isinstance(stats_by_queue, dict):
        raise ValueError(f"API extract queue stats must be an object for {start} to {end}")
    return ApiExtract(out_dir, records, stats_by_queue, manifest)
