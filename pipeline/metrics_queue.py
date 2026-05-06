from __future__ import annotations

import math
from typing import Any

import pandas as pd


def compute_queue_metrics(curated: pd.DataFrame, queue_id: str) -> dict:
    df = curated[curated["queue_id"].astype(str) == str(queue_id)].copy()
    if df.empty:
        return {
            "queue_id": str(queue_id),
            "total_calls": 0,
            "handled_calls": 0,
            "no_agent_calls": 0,
            "no_agent_rate": 0.0,
            "days_with_calls": 0,
            "avg_calls_per_active_day": 0.0,
            "busiest_day": None,
            "quietest_day": None,
            "daily_volume": [],
            "hourly_volume": [],
            "dow_volume": [],
            "duration_distributions": {
                "queue_sec": _duration_distribution(pd.Series(dtype="float64")),
                "agent_sec": _duration_distribution(pd.Series(dtype="float64")),
                "hold_sec": _duration_distribution(pd.Series(dtype="float64")),
            },
            "agent_leaderboard": [],
            "top_callers": [],
        }
    handled_mask = _handled_mask(df)
    handled = df[handled_mask & df["agent_name"].notna()]
    daily = df.groupby("date").size().rename("calls").reset_index()
    daily_records = daily.sort_values("date").to_dict("records")
    dow = df.groupby("dow").size().rename("calls").reset_index()
    hourly = (
        df.assign(no_answer=~handled_mask)
        .groupby("hour")
        .agg(calls=("call_id", "count"), no_answer_count=("no_answer", "sum"))
        .reset_index()
    )
    hourly["no_answer_rate"] = hourly["no_answer_count"] / hourly["calls"]

    agent = (
        handled.groupby("agent_name")
        .agg(calls=("call_id", "count"), avg_sec=("agent_sec", "mean"), median_sec=("agent_sec", "median"), total_sec=("agent_sec", "sum"))
        .reset_index()
        .sort_values(["calls", "agent_name"], ascending=[False, True])
    )
    if not agent.empty:
        agent["pct_of_answered"] = agent["calls"] / agent["calls"].sum()

    callers = (
        df[~df["caller_number_norm"].astype(str).str.startswith("__restricted__:")]
        .groupby("caller_number_norm")
        .size()
        .rename("calls")
        .reset_index()
        .sort_values(["calls", "caller_number_norm"], ascending=[False, True])
    )

    busiest = daily.sort_values(["calls", "date"], ascending=[False, True]).iloc[0].to_dict()
    quietest = daily.sort_values(["calls", "date"], ascending=[True, True]).iloc[0].to_dict()

    return {
        "queue_id": str(queue_id),
        "total_calls": int(len(df)),
        "handled_calls": int(handled_mask.sum()),
        "no_agent_calls": int((~handled_mask).sum()),
        "no_agent_rate": float((~handled_mask).sum() / len(df)) if len(df) else 0.0,
        "days_with_calls": int(daily["date"].nunique()),
        "avg_calls_per_active_day": float(len(df) / daily["date"].nunique()) if len(daily) else 0.0,
        "busiest_day": {"date": str(busiest["date"]), "calls": int(busiest["calls"])},
        "quietest_day": {"date": str(quietest["date"]), "calls": int(quietest["calls"])},
        "daily_volume": [{"date": str(r["date"]), "calls": int(r["calls"])} for r in daily_records],
        "hourly_volume": [
            {"hour": int(r["hour"]), "calls": int(r["calls"]), "no_answer_count": int(r["no_answer_count"]), "no_answer_rate": float(r["no_answer_rate"])}
            for r in hourly.sort_values("hour").to_dict("records")
        ],
        "dow_volume": [
            {"dow": str(r["dow"]), "calls": int(r["calls"])}
            for r in dow.sort_values("dow").to_dict("records")
        ],
        "duration_distributions": {
            "queue_sec": _duration_distribution(df["queue_sec"]),
            "agent_sec": _duration_distribution(handled["agent_sec"]),
            "hold_sec": _duration_distribution(df.loc[df["hold_sec"].fillna(0).gt(0), "hold_sec"]),
        },
        "agent_leaderboard": [
            {
                "agent_name": str(r["agent_name"]),
                "calls": int(r["calls"]),
                "avg_sec": _json_number(r["avg_sec"]),
                "median_sec": _json_number(r["median_sec"]),
                "total_sec": _json_number(r["total_sec"]),
                "pct_of_answered": float(r["pct_of_answered"]),
            }
            for r in agent.to_dict("records")
        ],
        "top_callers": [
            {"caller_number_norm": str(r["caller_number_norm"]), "calls": int(r["calls"])}
            for r in callers.head(10).to_dict("records")
        ],
    }


def _handled_mask(df: pd.DataFrame) -> pd.Series:
    if "handled_flag" in df.columns:
        return df["handled_flag"].eq("Handled")
    return df["agent_sec"].fillna(0).gt(0)


def _duration_distribution(series: pd.Series) -> dict[str, int | float | None]:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return {
            "count": 0,
            "mean": None,
            "std": None,
            "min": None,
            "p25": None,
            "median": None,
            "p75": None,
            "max": None,
        }
    return {
        "count": int(values.count()),
        "mean": _json_number(values.mean()),
        "std": _json_number(values.std()),
        "min": _json_number(values.min()),
        "p25": _json_number(values.quantile(0.25)),
        "median": _json_number(values.median()),
        "p75": _json_number(values.quantile(0.75)),
        "max": _json_number(values.max()),
    }


def _json_number(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        return None
    return number
