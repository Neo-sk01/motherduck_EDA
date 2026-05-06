from __future__ import annotations

import math
import re
from itertools import count
from typing import Any

import pandas as pd

_restricted_counter = count()


def to_seconds(value: Any) -> float:
    if value is None or pd.isna(value):
        return math.nan
    s = str(value).strip()
    if not s or s.endswith("ms"):
        return math.nan
    parts = s.split(":")
    try:
        nums = [int(part) for part in parts]
    except ValueError:
        return math.nan
    if len(nums) == 2:
        return float(nums[0] * 60 + nums[1])
    if len(nums) == 3:
        return float(nums[0] * 3600 + nums[1] * 60 + nums[2])
    return math.nan


def parse_csv_call_time(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, format="%m/%d/%Y %I:%M %p", errors="raise")


def normalize_caller_number(value: Any, row_key: str | int | None = None) -> str:
    sentinel_key = row_key if row_key is not None else next(_restricted_counter)
    if value is None or pd.isna(value):
        return f"__restricted__:{sentinel_key}"
    text = str(value).strip()
    if not text or text.lower() == "restricted":
        return f"__restricted__:{sentinel_key}"
    digits = re.sub(r"\D+", "", text)
    if not digits:
        return f"__restricted__:{sentinel_key}"
    return digits
