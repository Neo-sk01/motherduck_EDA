import pandas as pd

from pipeline.config import build_default_queues
from pipeline.ingest_api import curate_api_records


def test_curate_api_records_deduplicates_and_maps_cdr_fields():
    queues = tuple(build_default_queues())
    records = [
        {
            "from": {"call_id": "call-1", "number": "+1 (905) 283-3500"},
            "to": {"call_id": "20260105101100000000-a", "user": {"name": "Transfer Agent"}},
            "by": {"user": "8020", "username": "8020@neolore.com"},
            "start_time": "2026-01-05T10:11:00-05:00",
            "answer_time": "2026-01-05T10:11:09-05:00",
            "duration": 42,
            "queue_time": 9,
            "hold_time": 0,
            "release_reason": "Transfer",
        },
        {
            "from": {"call_id": "call-1", "number": "+1 (905) 283-3500"},
            "to": {"call_id": "20260105101200000000-b", "user": {"name": "Resolving Agent"}},
            "by": {"user": "8020", "username": "8020@neolore.com"},
            "start_time": "2026-01-05T10:12:00-05:00",
            "answer_time": "2026-01-05T10:12:08-05:00",
            "duration": 84,
            "queue_time": 8,
            "hold_time": 3,
            "release_reason": "Orig: Bye",
        },
        {
            "from": {"call_id": "call-2", "number": None},
            "to": {"call_id": "20260105101300000000-c", "user": {"name": None}},
            "by": {"user": "8030", "username": "8030@neolore.com"},
            "start_time": "2026-01-05T10:13:00-05:00",
            "answer_time": None,
            "duration": 12,
            "queue_time": 12,
            "release_reason": "No Answer",
        },
    ]

    result = curate_api_records(records, queues=queues, timezone="America/Toronto")

    assert result.validation["status"] == "success"
    assert result.field_inventory[:4] == ["answer_time", "by.user", "by.username", "duration"]
    assert len(result.raw_flat) == 3
    assert list(result.curated["call_id"]) == ["call-1", "call-2"]
    first = result.curated.iloc[0]
    assert first["queue_id"] == "8020"
    assert first["queue_name"] == "CSR English"
    assert first["agent_name"] == "Resolving Agent"
    assert first["caller_number_norm"] == "19052833500"
    assert first["queue_sec"] == 8.0
    assert first["agent_sec"] == 84.0
    assert first["hold_sec"] == 3.0
    assert first["handled_flag"] == "Handled"
    second = result.curated.iloc[1]
    assert second["queue_id"] == "8030"
    assert second["caller_number_norm"].startswith("__restricted__:")
    assert second["handled_flag"] == "No Agent"


def test_curate_api_records_falls_back_to_answering_user_for_agent_name():
    result = curate_api_records(
        [
            {
                "from": {"call_id": "call-1", "number": "9052833500"},
                "to": {"call_id": "20260105101100000000-a", "user": "48", "username": "48@neolore.com"},
                "by": {"user": "8020"},
                "start_time": "2026-01-05T10:11:00-05:00",
                "answer_time": "2026-01-05T10:11:09-05:00",
            },
        ],
        queues=tuple(build_default_queues()),
        timezone="America/Toronto",
    )

    assert result.validation["status"] == "success"
    assert result.curated.iloc[0]["agent_name"] == "48"
    assert result.curated.iloc[0]["agent_extension"] == "48"


def test_curate_api_records_reports_missing_required_api_fields():
    result = curate_api_records(
        [{"from": {"number": "9052833500"}, "start_time": "2026-01-05T10:11:00-05:00"}],
        queues=tuple(build_default_queues()),
        timezone="America/Toronto",
    )

    assert result.curated.empty
    assert result.validation["status"] == "source_gap"
    assert "from.call_id" in result.validation["missing_required_fields"]
    assert result.source_gaps == [
        {
            "queue_id": "all",
            "reason": "missing_api_fields",
            "message": "Missing required API fields: from.call_id",
        }
    ]


def test_curate_api_records_ignores_untracked_queue_rows():
    result = curate_api_records(
        [
            {
                "from": {"call_id": "tracked", "number": "9052833500"},
                "to": {"call_id": "20260105101100000000-a"},
                "call_queue": {"id": "8020"},
                "start_time": "2026-01-05T10:11:00-05:00",
            },
            {
                "from": {"call_id": "other", "number": "9052833500"},
                "to": {"call_id": "20260105101200000000-b"},
                "call_queue": {"id": "9000"},
                "start_time": "2026-01-05T10:12:00-05:00",
            },
        ],
        queues=tuple(build_default_queues()),
        timezone="America/Toronto",
    )

    assert result.validation["status"] == "success"
    assert result.validation["ignored_unmapped_queue_rows"] == 1
    assert result.source_gaps == []
    assert list(result.curated["call_id"]) == ["tracked"]


def test_curate_api_records_filters_to_requested_date_range():
    result = curate_api_records(
        [
            {
                "from": {"call_id": "in-range", "number": "9052833500"},
                "to": {"call_id": "20260105101100000000-a"},
                "call_queue": {"id": "8020"},
                "start_time": "2026-01-05T10:11:00-05:00",
            },
            {
                "from": {"call_id": "out-range", "number": "9052833500"},
                "to": {"call_id": "20260201101100000000-b"},
                "call_queue": {"id": "8020"},
                "start_time": "2026-02-01T10:11:00-05:00",
            },
        ],
        queues=tuple(build_default_queues()),
        timezone="America/Toronto",
        start="2026-01-01",
        end="2026-01-31",
    )

    assert result.validation["status"] == "success"
    assert list(result.curated["call_id"]) == ["in-range"]
    assert pd.to_datetime(result.curated.iloc[0]["call_datetime"]).month == 1
