from __future__ import annotations

import pandas as pd


NO_AGENT_RELEASE_REASONS = {"abandoned", "no answer", "not available"}


def answered_mask(df: pd.DataFrame) -> pd.Series:
    if "agent_sec" in df.columns:
        return pd.to_numeric(df["agent_sec"], errors="coerce").fillna(0).gt(0)
    if "agent_name" in df.columns:
        return valid_agent_name(df["agent_name"]) & ~no_agent_release_mask(df)
    return pd.Series(False, index=df.index)


def valid_agent_name(series: pd.Series) -> pd.Series:
    return (
        series.notna()
        & series.astype(str).str.strip().ne("")
        & series.astype(str).str.strip().str.casefold().ne("null")
    )


def no_agent_release_mask(df: pd.DataFrame) -> pd.Series:
    mask = pd.Series(False, index=df.index)
    for column in ("queue_release_reason", "agent_release_reason"):
        if column not in df.columns:
            continue
        normalized = df[column].fillna("").astype(str).str.strip().str.casefold()
        mask = mask | normalized.isin(NO_AGENT_RELEASE_REASONS)
    return mask
