from __future__ import annotations

import pandas as pd


def deduplicate_csv(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.drop(columns=[c for c in ["Unnamed: 0", "Unnamed: 17"] if c in df.columns], errors="ignore")
    return cleaned.drop_duplicates(subset=["Orig CallID"], keep="last").reset_index(drop=True)


def deduplicate_api(df: pd.DataFrame) -> pd.DataFrame:
    ordered = df
    if "to.call_id" in ordered.columns:
        ordered = ordered.sort_values("to.call_id", kind="stable")
    elif "start_time" in ordered.columns:
        ordered = ordered.sort_values("start_time", kind="stable")
    return ordered.drop_duplicates(subset=["from.call_id"], keep="last").reset_index(drop=True)
