"""Helpers for flattening nested API records."""

from typing import Any


def flatten_record(record: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """Flatten nested dictionaries into dotted field paths."""
    flattened: dict[str, Any] = {}

    for key, value in record.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flattened.update(flatten_record(value, path))
        else:
            flattened[path] = value

    return flattened


def inventory_field_paths(records: list[dict[str, Any]]) -> list[str]:
    """Return sorted unique flattened field paths across records."""
    paths: set[str] = set()
    for record in records:
        paths.update(flatten_record(record).keys())
    return sorted(paths)
