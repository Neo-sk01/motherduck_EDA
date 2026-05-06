import pandas as pd

from pipeline.curate import curate_csv_calls


def test_curate_csv_calls_adds_derived_fields_and_handled_flag():
    raw = pd.DataFrame(
        [
            {
                "Call Time": "04/01/2026 8:33 am",
                "Caller Number": "905-283-3500",
                "Orig CallID": "a",
                "Time in Queue": "00:09",
                "Agent Name": "Alicia Yameen",
                "Agent Time": "04:04",
                "Hold Time": "00:00",
                "Queue Release Reason": "Orig: Bye",
                "Agent Release Reason": "Orig: Bye",
                "source_queue_id": "8020",
                "source_queue_name": "CSR English",
                "source_language": "English",
                "source_role": "primary",
            },
            {
                "Call Time": "04/01/2026 8:35 am",
                "Caller Number": "Restricted",
                "Orig CallID": "b",
                "Time in Queue": "00:10",
                "Agent Name": None,
                "Agent Time": "00:00",
                "Hold Time": "00:00",
                "Queue Release Reason": "No Answer",
                "Agent Release Reason": "No Answer",
                "source_queue_id": "8020",
                "source_queue_name": "CSR English",
                "source_language": "English",
                "source_role": "primary",
            },
        ]
    )
    out = curate_csv_calls(raw)
    assert list(out["queue_id"]) == ["8020", "8020"]
    assert list(out["call_id"]) == ["a", "b"]
    assert list(out["handled_flag"]) == ["Handled", "No Agent"]
    assert out.loc[0, "queue_sec"] == 9
    assert out.loc[0, "agent_sec"] == 244
    assert out.loc[0, "date"] == "2026-04-01"
    assert out.loc[0, "hour"] == 8
    assert out.loc[0, "dow"] == "Wednesday"
    assert out.loc[1, "caller_number_norm"].startswith("__restricted__:")
