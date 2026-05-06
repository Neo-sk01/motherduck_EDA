from __future__ import annotations

import pandas as pd


def compute_queue_metrics(curated: pd.DataFrame, queue_id: str) -> dict:
    df = curated[curated["queue_id"].astype(str) == str(queue_id)].copy()
    handled = df[df["agent_name"].notna()]
    daily = df.groupby("date").size().rename("calls").reset_index()
    daily_records = daily.sort_values("date").to_dict("records")
    hourly = (
        df.assign(no_answer=df["agent_name"].isna())
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
        "handled_calls": int(len(handled)),
        "no_agent_calls": int(df["agent_name"].isna().sum()),
        "no_agent_rate": float(df["agent_name"].isna().sum() / len(df)) if len(df) else 0.0,
        "days_with_calls": int(daily["date"].nunique()),
        "avg_calls_per_active_day": float(len(df) / daily["date"].nunique()) if len(daily) else 0.0,
        "busiest_day": {"date": str(busiest["date"]), "calls": int(busiest["calls"])},
        "quietest_day": {"date": str(quietest["date"]), "calls": int(quietest["calls"])},
        "daily_volume": [{"date": str(r["date"]), "calls": int(r["calls"])} for r in daily_records],
        "hourly_volume": [
            {"hour": int(r["hour"]), "calls": int(r["calls"]), "no_answer_count": int(r["no_answer_count"]), "no_answer_rate": float(r["no_answer_rate"])}
            for r in hourly.sort_values("hour").to_dict("records")
        ],
        "agent_leaderboard": [
            {
                "agent_name": str(r["agent_name"]),
                "calls": int(r["calls"]),
                "avg_sec": float(r["avg_sec"]),
                "median_sec": float(r["median_sec"]),
                "total_sec": float(r["total_sec"]),
                "pct_of_answered": float(r["pct_of_answered"]),
            }
            for r in agent.to_dict("records")
        ],
        "top_callers": [
            {"caller_number_norm": str(r["caller_number_norm"]), "calls": int(r["calls"])}
            for r in callers.head(10).to_dict("records")
        ],
    }
