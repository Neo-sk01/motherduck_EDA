from datetime import date

import importlib.util
import sys
from pathlib import Path

import pytest

_module_path = Path(__file__).resolve().parents[1] / "run-pipeline" / "__init__.py"
spec = importlib.util.spec_from_file_location("run_pipeline_main", _module_path)
run_pipeline_main = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = run_pipeline_main
spec.loader.exec_module(run_pipeline_main)


parse_and_validate = run_pipeline_main.parse_and_validate


def test_parse_and_validate_accepts_valid_month_request():
    body = {"period": "month", "start": "2026-04-01", "end": "2026-04-30", "api_cache_mode": "auto"}
    result = parse_and_validate(body, now=date(2026, 5, 11))
    assert result.start == "2026-04-01"
    assert result.end == "2026-04-30"
    assert result.api_cache_mode == "auto"
    assert result.period == "month"


def test_parse_and_validate_rejects_non_month_period():
    body = {"period": "day", "start": "2026-04-01", "end": "2026-04-01"}
    with pytest.raises(ValueError, match="month"):
        parse_and_validate(body, now=date(2026, 5, 11))


def test_parse_and_validate_rejects_future_end_date():
    body = {"period": "month", "start": "2026-06-01", "end": "2026-06-30"}
    with pytest.raises(ValueError, match="future"):
        parse_and_validate(body, now=date(2026, 5, 11))


def test_parse_and_validate_rejects_window_over_92_days():
    body = {"period": "month", "start": "2025-01-01", "end": "2025-05-01"}
    with pytest.raises(ValueError, match="92"):
        parse_and_validate(body, now=date(2026, 5, 11))


def test_parse_and_validate_rejects_bad_api_cache_mode():
    body = {"period": "month", "start": "2026-04-01", "end": "2026-04-30", "api_cache_mode": "bogus"}
    with pytest.raises(ValueError, match="api_cache_mode"):
        parse_and_validate(body, now=date(2026, 5, 11))


def test_parse_and_validate_defaults_period_to_month_and_cache_to_auto():
    body = {"start": "2026-04-01", "end": "2026-04-30"}
    result = parse_and_validate(body, now=date(2026, 5, 11))
    assert result.period == "month"
    assert result.api_cache_mode == "auto"


def test_parse_and_validate_rejects_inverted_dates():
    body = {"period": "month", "start": "2026-04-30", "end": "2026-04-01"}
    with pytest.raises(ValueError, match="start <= end"):
        parse_and_validate(body, now=date(2026, 5, 11))
