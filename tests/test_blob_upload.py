import pytest

from pipeline.blob_upload import compute_merged_manifest


def _entry(key, start, end, source="api", status="success"):
    return {
        "key": key,
        "label": f"{key} label",
        "start": start,
        "end": end,
        "path": f"month_{start}_{end}/metrics.json",
        "source": source,
        "validation_status": status,
    }


def test_compute_merged_manifest_seeds_empty():
    new = _entry("2026-04", "2026-04-01", "2026-04-30")
    merged = compute_merged_manifest(existing={"reports": []}, new_entry=new)
    assert merged == {"reports": [new]}


def test_compute_merged_manifest_appends_new_period():
    march = _entry("2026-03", "2026-03-01", "2026-03-31")
    april = _entry("2026-04", "2026-04-01", "2026-04-30")
    merged = compute_merged_manifest(existing={"reports": [march]}, new_entry=april)
    assert [r["key"] for r in merged["reports"]] == ["2026-04", "2026-03"]


def test_compute_merged_manifest_replaces_same_key():
    april_csv = _entry("2026-04", "2026-04-01", "2026-04-30", source="csv")
    april_api = _entry("2026-04", "2026-04-01", "2026-04-30", source="api")
    merged = compute_merged_manifest(existing={"reports": [april_csv]}, new_entry=april_api)
    assert len(merged["reports"]) == 1
    assert merged["reports"][0]["source"] == "api"


def test_compute_merged_manifest_handles_none_existing():
    new = _entry("2026-04", "2026-04-01", "2026-04-30")
    merged = compute_merged_manifest(existing=None, new_entry=new)
    assert merged == {"reports": [new]}


def test_compute_merged_manifest_tolerates_malformed_existing():
    new = _entry("2026-04", "2026-04-01", "2026-04-30")
    merged = compute_merged_manifest(existing={"reports": "not-a-list"}, new_entry=new)
    assert merged == {"reports": [new]}
