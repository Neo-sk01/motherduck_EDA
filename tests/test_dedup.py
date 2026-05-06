import pandas as pd

from pipeline.dedup import deduplicate_api, deduplicate_csv


def test_deduplicate_csv_drops_junk_columns_and_keeps_last_orig_call_id():
    df = pd.DataFrame(
        [
            {"Unnamed: 0": 1, "Orig CallID": "a", "Agent Name": "First", "Unnamed: 17": None},
            {"Unnamed: 0": 2, "Orig CallID": "a", "Agent Name": "Last", "Unnamed: 17": None},
            {"Unnamed: 0": 3, "Orig CallID": "b", "Agent Name": "Only", "Unnamed: 17": None},
        ]
    )
    out = deduplicate_csv(df)
    assert list(out["Orig CallID"]) == ["a", "b"]
    assert list(out["Agent Name"]) == ["Last", "Only"]
    assert "Unnamed: 0" not in out.columns
    assert "Unnamed: 17" not in out.columns


def test_deduplicate_api_sorts_to_call_id_and_keeps_last_from_call_id():
    df = pd.DataFrame(
        [
            {"from.call_id": "root", "to.call_id": "20260401101000000000-b", "agent": "Last"},
            {"from.call_id": "root", "to.call_id": "20260401100000000000-a", "agent": "First"},
            {"from.call_id": "other", "to.call_id": "20260401102000000000-c", "agent": "Only"},
        ]
    )
    out = deduplicate_api(df)
    assert list(out["from.call_id"]) == ["root", "other"]
    assert list(out["agent"]) == ["Last", "Only"]


def test_deduplicate_api_uses_start_time_when_to_call_id_is_absent():
    df = pd.DataFrame(
        [
            {"from.call_id": "root", "start_time": "2026-04-01T10:10:00", "agent": "Last"},
            {"from.call_id": "root", "start_time": "2026-04-01T10:00:00", "agent": "First"},
        ]
    )
    out = deduplicate_api(df)
    assert list(out["agent"]) == ["Last"]


def test_deduplicate_csv_rejects_missing_or_blank_keys():
    df = pd.DataFrame(
        [
            {"Orig CallID": "a", "Agent Name": "Only"},
            {"Orig CallID": "", "Agent Name": "Blank"},
        ]
    )
    try:
        deduplicate_csv(df)
    except ValueError as exc:
        assert "Orig CallID" in str(exc)
    else:
        raise AssertionError("blank Orig CallID should raise ValueError")


def test_deduplicate_api_rejects_missing_or_blank_keys():
    df = pd.DataFrame(
        [
            {"from.call_id": "root", "to.call_id": "20260401100000000000-a"},
            {"from.call_id": None, "to.call_id": "20260401101000000000-b"},
        ]
    )
    try:
        deduplicate_api(df)
    except ValueError as exc:
        assert "from.call_id" in str(exc)
    else:
        raise AssertionError("missing from.call_id should raise ValueError")


def test_deduplicate_api_requires_chronological_order_column():
    df = pd.DataFrame(
        [
            {"from.call_id": "root", "agent": "First"},
            {"from.call_id": "root", "agent": "Last"},
        ]
    )
    try:
        deduplicate_api(df)
    except ValueError as exc:
        assert "to.call_id or start_time" in str(exc)
    else:
        raise AssertionError("API dedup without ordering column should raise ValueError")
