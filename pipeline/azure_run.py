from __future__ import annotations

import calendar
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def resolve_period(
    mode: str,
    *,
    timezone: str = "America/Toronto",
    now: datetime | None = None,
    explicit_start: str | None = None,
    explicit_end: str | None = None,
) -> tuple[str, str]:
    """Return (start, end) ISO-date strings for the requested period."""
    if mode == "previous-month":
        tz = ZoneInfo(timezone)
        anchor = (now or datetime.now(tz)).astimezone(tz)
        first_of_this = anchor.replace(day=1)
        last_of_prev = first_of_this.replace(hour=0, minute=0, second=0, microsecond=0) - _one_day()
        year = last_of_prev.year
        month = last_of_prev.month
        last_day = calendar.monthrange(year, month)[1]
        start = f"{year:04d}-{month:02d}-01"
        end = f"{year:04d}-{month:02d}-{last_day:02d}"
        return start, end

    if mode == "explicit":
        if not explicit_start:
            raise ValueError("PERIOD_START is required when PERIOD_MODE=explicit")
        if not explicit_end:
            raise ValueError("PERIOD_END is required when PERIOD_MODE=explicit")
        return explicit_start, explicit_end

    raise ValueError(f"PERIOD_MODE must be 'previous-month' or 'explicit', got: {mode!r}")


def _one_day():
    return timedelta(days=1)
