from __future__ import annotations

from typing import Any


def compute_merged_manifest(existing: dict[str, Any] | None, new_entry: dict[str, Any]) -> dict[str, Any]:
    reports: list[dict[str, Any]]
    if existing is None:
        reports = []
    else:
        raw = existing.get("reports")
        reports = list(raw) if isinstance(raw, list) else []
    key = new_entry["key"]
    reports = [row for row in reports if not (isinstance(row, dict) and row.get("key") == key)]
    reports.append(new_entry)
    reports.sort(key=lambda row: str(row.get("start", "")), reverse=True)
    return {"reports": reports}
