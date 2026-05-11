from __future__ import annotations

import pandas as pd

from pipeline.classify import answered_mask
from pipeline.parse import normalize_caller_number, parse_csv_call_time, to_seconds


def curate_csv_calls(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame()
    call_dt = parse_csv_call_time(df["Call Time"])
    out["queue_id"] = df["source_queue_id"].astype(str)
    out["queue_name"] = df["source_queue_name"]
    out["language"] = df["source_language"]
    out["role"] = df["source_role"]
    out["call_id"] = df["Orig CallID"].astype(str)
    out["call_time"] = df["Call Time"]
    out["call_datetime"] = call_dt
    out["date"] = call_dt.dt.strftime("%Y-%m-%d")
    out["hour"] = call_dt.dt.hour
    out["dow"] = call_dt.dt.day_name()
    out["caller_name"] = df.get("Caller Name")
    out["caller_number"] = df["Caller Number"]
    out["caller_number_norm"] = [
        normalize_caller_number(value, row_key=call_id)
        for value, call_id in zip(df["Caller Number"], df["Orig CallID"], strict=False)
    ]
    out["dnis"] = df.get("DNIS")
    out["agent_extension"] = df.get("Agent Extension")
    out["agent_phone"] = df.get("Agent Phone")
    out["agent_name"] = df.get("Agent Name")
    out["queue_sec"] = df["Time in Queue"].map(to_seconds)
    out["agent_sec"] = df["Agent Time"].map(to_seconds)
    out["hold_sec"] = df["Hold Time"].map(to_seconds)
    out["agent_release_reason"] = df.get("Agent Release Reason")
    out["queue_release_reason"] = df.get("Queue Release Reason")
    answered = answered_mask(out)
    out["handled_flag"] = answered.map({True: "Handled", False: "No Agent"})
    return out
