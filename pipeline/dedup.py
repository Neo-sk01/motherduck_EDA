from __future__ import annotations

import pandas as pd


def deduplicate_csv(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.drop(columns=[c for c in ["Unnamed: 0", "Unnamed: 17"] if c in df.columns], errors="ignore")
    _require_key(cleaned, "Orig CallID")
    return cleaned.drop_duplicates(subset=["Orig CallID"], keep="last").reset_index(drop=True)


def deduplicate_api(df: pd.DataFrame) -> pd.DataFrame:
    _require_key(df, "from.call_id")
    ordered = df
    if "to.call_id" in ordered.columns:
        ordered = ordered.sort_values("to.call_id", kind="stable")
    elif "start_time" in ordered.columns:
        ordered = ordered.sort_values("start_time", kind="stable")
    else:
        raise ValueError("API dedup requires to.call_id or start_time for chronological ordering")
    return ordered.drop_duplicates(subset=["from.call_id"], keep="last").reset_index(drop=True)


def _require_key(df: pd.DataFrame, column: str) -> None:
    if column not in df.columns:
        raise ValueError(f"Missing required dedup key column: {column}")
    key_values = df[column]
    blank = key_values.astype("string").str.strip().eq("")
    if key_values.isna().any() or blank.any():
        raise ValueError(f"Dedup key column {column} contains missing or blank values")
