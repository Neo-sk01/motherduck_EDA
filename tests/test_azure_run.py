from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from pipeline.azure_run import resolve_period


def test_resolve_period_previous_month_from_toronto_perspective():
    now = datetime(2026, 5, 11, 14, 30, tzinfo=ZoneInfo("America/Toronto"))
    start, end = resolve_period(mode="previous-month", timezone="America/Toronto", now=now)
    assert start == "2026-04-01"
    assert end == "2026-04-30"


def test_resolve_period_previous_month_handles_january_boundary():
    now = datetime(2026, 1, 5, 12, 0, tzinfo=ZoneInfo("America/Toronto"))
    start, end = resolve_period(mode="previous-month", timezone="America/Toronto", now=now)
    assert start == "2025-12-01"
    assert end == "2025-12-31"


def test_resolve_period_previous_month_handles_february_leap_year():
    now = datetime(2024, 3, 15, 12, 0, tzinfo=ZoneInfo("America/Toronto"))
    start, end = resolve_period(mode="previous-month", timezone="America/Toronto", now=now)
    assert start == "2024-02-01"
    assert end == "2024-02-29"


def test_resolve_period_previous_month_runs_at_03_utc_on_first_uses_correct_local_month():
    now = datetime(2026, 5, 1, 9, 0, tzinfo=ZoneInfo("UTC"))
    start, end = resolve_period(mode="previous-month", timezone="America/Toronto", now=now)
    assert start == "2026-04-01"
    assert end == "2026-04-30"


def test_resolve_period_explicit_passes_through():
    start, end = resolve_period(mode="explicit", explicit_start="2025-11-01", explicit_end="2025-11-30")
    assert start == "2025-11-01"
    assert end == "2025-11-30"


def test_resolve_period_explicit_requires_both_dates():
    with pytest.raises(ValueError, match="PERIOD_START"):
        resolve_period(mode="explicit", explicit_start=None, explicit_end="2025-11-30")
    with pytest.raises(ValueError, match="PERIOD_END"):
        resolve_period(mode="explicit", explicit_start="2025-11-01", explicit_end=None)


def test_resolve_period_unknown_mode_raises():
    with pytest.raises(ValueError, match="PERIOD_MODE"):
        resolve_period(mode="bogus")
