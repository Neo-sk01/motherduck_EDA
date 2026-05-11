from datetime import datetime
from contextlib import nullcontext
from unittest.mock import patch
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


def test_main_explicit_mode_invokes_run_api_then_upload(monkeypatch, tmp_path):
    monkeypatch.setenv("PERIOD_MODE", "explicit")
    monkeypatch.setenv("PERIOD_TYPE", "month")
    monkeypatch.setenv("PERIOD_START", "2026-04-01")
    monkeypatch.setenv("PERIOD_END", "2026-04-30")
    monkeypatch.setenv("API_CACHE_MODE", "auto")
    monkeypatch.setenv("WRITE_STORE", "1")
    monkeypatch.setenv("SOURCE", "api")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("MOTHERDUCK_TOKEN_RW", "fake-token")
    monkeypatch.delenv("REPORTS_STORAGE_ACCOUNT_URL", raising=False)

    calls: list[str] = []
    with patch("pipeline.azure_run.run_api", create=True) as mock_run_api, \
         patch("pipeline.azure_run.upload_reports", create=True) as mock_upload, \
         patch("pipeline.azure_run._acquire_period_lease", create=True) as mock_lease, \
         patch("pipeline.azure_run.build_versature_client_from_env", create=True) as mock_client, \
         patch("pipeline.azure_run.AnalyticsStore.motherduck", create=True) as mock_store:
        mock_lease.return_value = nullcontext()
        mock_run_api.side_effect = lambda *a, **kw: calls.append("run_api") or tmp_path
        mock_upload.side_effect = lambda *a, **kw: calls.append("upload")
        mock_client.return_value = object()
        mock_store.return_value = object()

        from pipeline.azure_run import main
        rc = main()

    assert rc == 0
    assert calls == ["run_api", "upload"]
    mock_run_api.assert_called_once()
    kwargs = mock_run_api.call_args.kwargs
    assert kwargs.get("start") == "2026-04-01"
    assert kwargs.get("end") == "2026-04-30"


def test_main_skips_upload_when_run_api_raises(monkeypatch, tmp_path):
    monkeypatch.setenv("PERIOD_MODE", "explicit")
    monkeypatch.setenv("PERIOD_TYPE", "month")
    monkeypatch.setenv("PERIOD_START", "2026-04-01")
    monkeypatch.setenv("PERIOD_END", "2026-04-30")
    monkeypatch.setenv("SOURCE", "api")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("MOTHERDUCK_TOKEN_RW", "fake-token")
    monkeypatch.setenv("WRITE_STORE", "1")

    with patch("pipeline.azure_run.run_api", create=True) as mock_run_api, \
         patch("pipeline.azure_run.upload_reports", create=True) as mock_upload, \
         patch("pipeline.azure_run._acquire_period_lease", create=True) as mock_lease, \
         patch("pipeline.azure_run.build_versature_client_from_env", create=True) as mock_client, \
         patch("pipeline.azure_run.AnalyticsStore.motherduck", create=True) as mock_store:
        mock_lease.return_value = nullcontext()
        mock_client.return_value = object()
        mock_store.return_value = object()
        mock_run_api.side_effect = RuntimeError("API blew up")

        from pipeline.azure_run import main
        with pytest.raises(RuntimeError, match="API blew up"):
            main()

    mock_upload.assert_not_called()
