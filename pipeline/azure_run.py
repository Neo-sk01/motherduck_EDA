from __future__ import annotations

import calendar
import logging
import os
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from pipeline.blob_upload import upload_reports
from pipeline.config import AppConfig
from pipeline.main import build_versature_client_from_env, run_api, run_csv
from pipeline.report import _month_label
from pipeline.storage import AnalyticsStore

log = logging.getLogger(__name__)


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


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    mode = os.environ.get("PERIOD_MODE", "previous-month")
    period_type = os.environ.get("PERIOD_TYPE", "month")
    source = os.environ.get("SOURCE", "api")
    api_cache_mode = os.environ.get("API_CACHE_MODE", "auto")
    write_store = os.environ.get("WRITE_STORE", "1") == "1"

    config = AppConfig.from_env()
    start, end = resolve_period(
        mode=mode,
        timezone=config.timezone,
        explicit_start=os.environ.get("PERIOD_START"),
        explicit_end=os.environ.get("PERIOD_END"),
    )
    log.info("resolved period: mode=%s type=%s start=%s end=%s", mode, period_type, start, end)

    period_dir_name = f"{period_type}_{start}_{end}"
    manifest_entry = {
        "key": start[:7],
        "label": _month_label(start),
        "start": start,
        "end": end,
        "path": f"{period_dir_name}/metrics.json",
        "source": source,
        "validation_status": "success",
    }

    store = None
    if write_store:
        if not os.environ.get("MOTHERDUCK_TOKEN_RW"):
            raise SystemExit("MOTHERDUCK_TOKEN_RW is required when WRITE_STORE=1")
        store = AnalyticsStore.motherduck(config.motherduck_database)

    with _acquire_period_lease(period_dir_name):
        if source == "api":
            run_api(
                config=config,
                period=period_type,
                start=start,
                end=end,
                store=store,
                client=build_versature_client_from_env(),
                api_cache_mode=api_cache_mode,
            )
        elif source == "csv":
            run_csv(config=config, period=period_type, start=start, end=end, store=store)
        else:
            raise SystemExit(f"SOURCE must be 'api' or 'csv', got: {source!r}")

        upload_reports(Path(config.data_dir), period_dir_name, manifest_entry)
    return 0


@contextmanager
def _acquire_period_lease(period_dir_name: str):
    """Acquire a blob lease on .locks/<period_dir_name>.lock to serialize concurrent runs."""
    account_url = os.environ.get("REPORTS_STORAGE_ACCOUNT_URL")
    if not account_url:
        yield
        return

    from azure.storage.blob import BlobServiceClient
    from pipeline.blob_upload import _build_credential

    container_name = os.environ.get("REPORTS_CONTAINER", "reports")
    service = BlobServiceClient(account_url=account_url, credential=_build_credential())
    blob = service.get_blob_client(container=container_name, blob=f".locks/{period_dir_name}.lock")
    try:
        blob.upload_blob(b"", overwrite=False)
    except Exception:
        pass
    lease = blob.acquire_lease(lease_duration=60)
    try:
        yield
    finally:
        try:
            lease.release()
        except Exception:
            log.warning("failed to release lease on %s", period_dir_name)


if __name__ == "__main__":
    raise SystemExit(main())
