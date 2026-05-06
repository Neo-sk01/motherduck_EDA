from __future__ import annotations

from numbers import Number
from typing import Any

import pandas as pd


def compute_crossqueue_metrics(curated: pd.DataFrame) -> dict:
    funnels = {language: _language_funnel(curated, language) for language in ["English", "French"]}
    return {
        "funnels": funnels,
        "agents": _consolidated_agents(curated),
        "callers": _consolidated_callers(curated),
        "same_hour_no_answer": _same_hour_no_answer(curated),
        "same_day_volume": _same_day_volume(curated),
    }


def _language_funnel(curated: pd.DataFrame, language: str) -> dict:
    lang = curated[curated["language"] == language]
    handled_mask = _handled_mask(lang)
    primary = lang[lang["role"] == "primary"]
    overflow = lang[lang["role"] == "overflow"]
    primary_handled = handled_mask.loc[primary.index]
    overflow_handled = handled_mask.loc[overflow.index]
    primary_calls = len(primary)
    primary_answered = int(primary_handled.sum())
    primary_failed = primary_calls - primary_answered
    overflow_received = len(overflow)
    overflow_answered = int(overflow_handled.sum())
    overflow_failed = overflow_received - overflow_answered
    unaccounted = primary_failed - overflow_received
    lost = overflow_failed + max(unaccounted, 0)
    final_answered = primary_answered + overflow_answered
    return {
        "primary_calls": int(primary_calls),
        "primary_answered": int(primary_answered),
        "primary_failed": int(primary_failed),
        "overflow_received": int(overflow_received),
        "routing_match": float(overflow_received / primary_failed) if primary_failed else 0.0,
        "overflow_answered": int(overflow_answered),
        "overflow_failed": int(overflow_failed),
        "lost": int(lost),
        "lost_rate": float(lost / primary_calls) if primary_calls else 0.0,
        "effective_answer_rate": float(final_answered / primary_calls) if primary_calls else 0.0,
        "unaccounted": int(unaccounted),
    }


def _consolidated_agents(curated: pd.DataFrame) -> list[dict]:
    handled = curated[_handled_mask(curated) & curated["agent_name"].notna()]
    if handled.empty:
        return []
    pivot = handled.pivot_table(index="agent_name", columns="queue_id", values="call_id", aggfunc="count", fill_value=0)
    pivot["total_calls"] = pivot.sum(axis=1)
    rows = pivot.reset_index().sort_values(["total_calls", "agent_name"], ascending=[False, True])
    return [_json_row(row, text_fields={"agent_name"}) for row in rows.to_dict("records")]


def _consolidated_callers(curated: pd.DataFrame) -> list[dict]:
    callers = curated[~curated["caller_number_norm"].astype(str).str.startswith("__restricted__:")]
    if callers.empty:
        return []
    pivot = callers.pivot_table(index="caller_number_norm", columns="queue_id", values="call_id", aggfunc="count", fill_value=0)
    pivot["total_calls"] = pivot.sum(axis=1)
    rows = pivot.reset_index().sort_values(["total_calls", "caller_number_norm"], ascending=[False, True])
    return [_json_row(row, text_fields={"caller_number_norm"}) for row in rows.to_dict("records")]


def _same_hour_no_answer(curated: pd.DataFrame) -> list[dict]:
    grouped = (
        curated.assign(no_answer=~_handled_mask(curated))
        .groupby(["queue_id", "hour"])
        .agg(calls=("call_id", "count"), no_answer_count=("no_answer", "sum"))
        .reset_index()
    )
    grouped["no_answer_rate"] = grouped["no_answer_count"] / grouped["calls"]
    return [
        {
            "queue_id": str(r["queue_id"]),
            "hour": int(r["hour"]),
            "calls": int(r["calls"]),
            "no_answer_count": int(r["no_answer_count"]),
            "no_answer_rate": float(r["no_answer_rate"]),
        }
        for r in grouped.sort_values(["queue_id", "hour"]).to_dict("records")
    ]


def _same_day_volume(curated: pd.DataFrame) -> list[dict]:
    grouped = curated.groupby(["queue_id", "date"]).size().rename("calls").reset_index()
    return [
        {"queue_id": str(r["queue_id"]), "date": str(r["date"]), "calls": int(r["calls"])}
        for r in grouped.sort_values(["date", "queue_id"]).to_dict("records")
    ]


def _handled_mask(df: pd.DataFrame) -> pd.Series:
    if "handled_flag" in df.columns:
        return df["handled_flag"].eq("Handled")
    if "agent_sec" in df.columns:
        return df["agent_sec"].fillna(0).gt(0)
    return df["agent_name"].notna()


def _json_row(row: dict[str, Any], text_fields: set[str]) -> dict:
    out = {}
    for key, value in row.items():
        if key in text_fields:
            out[str(key)] = str(value)
        elif isinstance(value, Number) and pd.notna(value):
            out[str(key)] = int(value)
        else:
            out[str(key)] = value
    return out
