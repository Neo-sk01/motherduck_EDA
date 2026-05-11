from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pandas as pd

from pipeline.anomaly import detect_anomalies
from pipeline.api_extract import api_extract_exists, load_api_extract, write_api_extract
from pipeline.api_stats import apply_api_queue_stats
from pipeline.client import VersatureClient, fetch_client_credentials_token
from pipeline.config import AppConfig
from pipeline.crossqueue import compute_crossqueue_metrics
from pipeline.curate import curate_csv_calls
from pipeline.dedup import deduplicate_csv
from pipeline.ingest_api import curate_api_records
from pipeline.ingest_csv import find_queue_csv, load_queue_csv
from pipeline.metrics_queue import compute_queue_metrics
from pipeline.parse import parse_csv_call_time
from pipeline.report import write_report_bundle
from pipeline.storage import AnalyticsStore

API_AUTH_MESSAGE = (
    "API mode requires VERSATURE_ACCESS_TOKEN or both VERSATURE_CLIENT_ID and "
    "VERSATURE_CLIENT_SECRET."
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=("csv", "api", "hybrid"), required=True)
    parser.add_argument("--period", choices=("day", "week", "month"), required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--write-store", action="store_true")
    parser.add_argument("--api-cache-mode", choices=("auto", "refresh", "reuse"), default="auto")
    return parser.parse_args(argv)


def run_csv(
    config: AppConfig,
    period: str,
    start: str,
    end: str,
    store: AnalyticsStore | None = None,
) -> Path:
    curated_queues = []
    raw_queues = []
    queue_count_validation = {}
    source_gaps = []
    for queue in config.queues:
        try:
            csv_path = find_queue_csv(config.csv_dir, queue.queue_id)
        except FileNotFoundError as exc:
            source_gaps.append({"queue_id": queue.queue_id, "reason": "missing_csv", "message": str(exc)})
            continue
        raw = load_queue_csv(csv_path, queue)
        raw = _filter_raw_date_range(raw, start, end)
        raw_queues.append(raw)
        deduped = deduplicate_csv(raw)
        curated_queue = curate_csv_calls(deduped)
        curated_queues.append(curated_queue)
        queue_count_validation[queue.queue_id] = _queue_validation_counts(
            raw_rows=len(raw),
            cleaned_calls=len(deduped),
            metrics=compute_queue_metrics(curated_queue, queue.queue_id),
            calculation_source="csv_cleaned_queue_level_calls",
            dedupe_key="Orig CallID; keep last row after date filtering",
        )

    if source_gaps:
        out_dir = write_report_bundle(
            config.data_dir,
            period,
            start,
            end,
            {},
            {},
            [],
            source_gaps=source_gaps,
            validation={"status": "source_gap"},
            source_mode="csv",
        )
        missing = ", ".join(gap["queue_id"] for gap in source_gaps)
        raise FileNotFoundError(f"Missing required queue CSVs for {missing}; source gap report written to {out_dir}")

    curated = pd.concat(curated_queues, ignore_index=True)
    queue_metrics = {
        queue.queue_id: compute_queue_metrics(curated, queue.queue_id)
        for queue in config.queues
    }
    for queue_id, counts in queue_count_validation.items():
        if queue_id in queue_metrics:
            queue_metrics[queue_id].update(
                {
                    "raw_rows": counts["raw_rows"],
                    "cleaned_calls": counts["cleaned_calls"],
                    "duplicate_rows_removed": counts["duplicate_rows_removed"],
                    "answered_no_agent_reconciled": counts["answered_no_agent_reconciled"],
                    "dedupe_key": counts["dedupe_key"],
                    "calculation_source": counts["calculation_source"],
                }
            )
    crossqueue = compute_crossqueue_metrics(curated)
    anomalies = detect_anomalies(queue_metrics, crossqueue)
    validation = _report_validation(
        start=start,
        end=end,
        timezone=config.timezone,
        queues_included=[queue.queue_id for queue in config.queues],
        queue_counts=queue_count_validation,
        calculation_source="csv_cleaned_queue_level_calls",
        dedupe_key="Orig CallID; keep last row after date filtering",
    )
    out_dir = write_report_bundle(
        config.data_dir,
        period,
        start,
        end,
        queue_metrics,
        crossqueue,
        anomalies,
        validation=validation,
        source_mode="csv",
    )
    if store is not None:
        store.replace_queue_dimension(config.queues)
        store.replace_raw_call_legs(start, end, pd.concat(raw_queues, ignore_index=True), source_mode="csv")
        store.replace_curated_calls(start, end, curated)
        store.replace_report_outputs(start, end, period, "csv", queue_metrics, crossqueue, anomalies)
    return out_dir


def run_api(
    config: AppConfig,
    period: str,
    start: str,
    end: str,
    store: AnalyticsStore | None = None,
    client: VersatureClient | None = None,
    api_cache_mode: str = "auto",
) -> Path:
    api_client = client or build_versature_client_from_env()
    records, stats_by_queue = _get_or_create_api_extract(
        config=config,
        period=period,
        start=start,
        end=end,
        client=api_client,
        api_cache_mode=api_cache_mode,
    )
    result = curate_api_records(records, queues=config.queues, timezone=config.timezone, start=start, end=end)
    _write_api_inventory(config.data_dir, start, end, result.field_inventory, result.validation)
    if result.validation.get("status") != "success":
        out_dir = write_report_bundle(
            config.data_dir,
            period,
            start,
            end,
            {},
            {},
            [],
            source_gaps=result.source_gaps,
            validation=result.validation,
            source_mode="api",
        )
        raise ValueError(f"API source gap report written to {out_dir}: {result.source_gaps}")

    queue_metrics = {
        queue.queue_id: compute_queue_metrics(result.curated, queue.queue_id)
        for queue in config.queues
    }
    crossqueue = compute_crossqueue_metrics(result.curated)
    apply_api_queue_stats(queue_metrics, crossqueue, stats_by_queue, config.queues)
    result.validation["api_stats_diagnostic"] = True
    result.validation["api_stats_overlay"] = False
    result.validation["calculation_source"] = "api_cdr_cleaned_queue_level_calls"
    anomalies = detect_anomalies(queue_metrics, crossqueue)
    out_dir = write_report_bundle(
        config.data_dir,
        period,
        start,
        end,
        queue_metrics,
        crossqueue,
        anomalies,
        source_gaps=result.source_gaps,
        validation=result.validation,
        source_mode="api",
    )
    if store is not None:
        _write_api_outputs_to_store(
            config=config,
            period=period,
            start=start,
            end=end,
            store=store,
            raw_flat=result.raw_flat,
            curated=result.curated,
            queue_metrics=queue_metrics,
            crossqueue=crossqueue,
            anomalies=anomalies,
            validation=result.validation,
        )
    return out_dir


def _get_or_create_api_extract(
    config: AppConfig,
    period: str,
    start: str,
    end: str,
    client: VersatureClient,
    api_cache_mode: str,
) -> tuple[list[dict], dict[str, dict]]:
    if api_cache_mode not in {"auto", "refresh", "reuse"}:
        raise ValueError("api_cache_mode must be one of: auto, refresh, reuse")

    if api_cache_mode in {"auto", "reuse"} and api_extract_exists(config.data_dir, start, end):
        extract = load_api_extract(config.data_dir, start, end)
        return extract.records, extract.stats_by_queue

    if api_cache_mode == "reuse":
        raise FileNotFoundError(f"No complete API extract exists for {start} to {end}")

    records = client.get_cdr_users(start_date=start, end_date=end)
    stats_by_queue = {
        queue.queue_id: client.get_call_queue_stats(queue.queue_id, start, end)
        for queue in config.queues
    }
    write_api_extract(
        config.data_dir,
        period=period,
        start=start,
        end=end,
        records=records,
        stats_by_queue=stats_by_queue,
        queues=config.queues,
    )
    return records, stats_by_queue


def _write_api_outputs_to_store(
    config: AppConfig,
    period: str,
    start: str,
    end: str,
    store: AnalyticsStore,
    raw_flat: pd.DataFrame,
    curated: pd.DataFrame,
    queue_metrics: dict[str, dict],
    crossqueue: dict,
    anomalies: list[dict],
    validation: dict,
) -> None:
    use_motherduck = bool(os.getenv("MOTHERDUCK_TOKEN_RW"))
    attempts = 3 if use_motherduck else 1
    for attempt in range(attempts):
        active_store = AnalyticsStore.motherduck(config.motherduck_database) if use_motherduck else store
        try:
            active_store.replace_queue_dimension(config.queues)
            active_store.replace_raw_call_legs(start, end, raw_flat, source_mode="api")
            active_store.replace_curated_calls(start, end, curated)
            active_store.replace_report_outputs(
                start,
                end,
                period,
                "api",
                queue_metrics,
                crossqueue,
                anomalies,
                validation=validation,
            )
            return
        except Exception as exc:
            if attempt == attempts - 1 or not _is_retryable_motherduck_write_error(exc):
                raise


def _is_retryable_motherduck_write_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        "remote catalog has changed" in message
        or "lease expired" in message
        or "connection error" in message
        or "transaction already rolled back" in message
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    config = AppConfig.from_env()
    store = None
    if args.write_store:
        if not os.getenv("MOTHERDUCK_TOKEN_RW"):
            raise SystemExit("MOTHERDUCK_TOKEN_RW is required when --write-store is set.")
        store = AnalyticsStore.motherduck(config.motherduck_database)
    if args.source == "csv":
        run_csv(config, args.period, args.start, args.end, store=store)
    elif args.source == "api":
        run_api(
            config,
            args.period,
            args.start,
            args.end,
            store=store,
            client=build_versature_client_from_env(),
            api_cache_mode=args.api_cache_mode,
        )
    else:
        raise SystemExit("Hybrid mode is not executable yet; run csv or api.")
    return 0


def _filter_raw_date_range(raw: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    start_date = pd.Timestamp(start).normalize()
    end_date = pd.Timestamp(end).normalize()
    call_dates = parse_csv_call_time(raw["Call Time"]).dt.normalize()
    return raw.loc[call_dates.between(start_date, end_date)].reset_index(drop=True)


def _queue_validation_counts(
    raw_rows: int,
    cleaned_calls: int,
    metrics: dict,
    calculation_source: str,
    dedupe_key: str,
) -> dict:
    answered = int(metrics.get("handled_calls", 0))
    no_agent = int(metrics.get("no_agent_calls", 0))
    return {
        "raw_rows": int(raw_rows),
        "cleaned_calls": int(cleaned_calls),
        "duplicate_rows_removed": int(raw_rows - cleaned_calls),
        "answered_calls": answered,
        "no_agent_calls": no_agent,
        "answered_plus_no_agent": int(answered + no_agent),
        "answered_no_agent_reconciled": bool(answered + no_agent == cleaned_calls),
        "dedupe_key": dedupe_key,
        "calculation_source": calculation_source,
    }


def _report_validation(
    start: str,
    end: str,
    timezone: str,
    queues_included: list[str],
    queue_counts: dict[str, dict],
    calculation_source: str,
    dedupe_key: str,
) -> dict:
    raw_rows = sum(int(row["raw_rows"]) for row in queue_counts.values())
    cleaned_calls = sum(int(row["cleaned_calls"]) for row in queue_counts.values())
    answered = sum(int(row["answered_calls"]) for row in queue_counts.values())
    no_agent = sum(int(row["no_agent_calls"]) for row in queue_counts.values())
    return {
        "status": "success",
        "raw_row_count": raw_rows,
        "cleaned_row_count": cleaned_calls,
        "duplicate_rows_removed": raw_rows - cleaned_calls,
        "answered_count": answered,
        "no_agent_count": no_agent,
        "answered_plus_no_agent": answered + no_agent,
        "answered_plus_no_agent_reconciles": answered + no_agent == cleaned_calls,
        "date_range_used": f"{start} 00:00:00 through {end} 23:59:59",
        "timezone_used": timezone,
        "queues_included": queues_included,
        "dedupe_key_used": dedupe_key,
        "calculation_source_used": calculation_source,
        "queue_counts": queue_counts,
    }


def build_versature_client_from_env() -> VersatureClient:
    base_url = os.getenv("VERSATURE_BASE_URL", "https://integrate.versature.com/api")
    api_version = os.getenv("VERSATURE_API_VERSION", "application/vnd.integrate.v1.10.0+json")
    access_token = os.getenv("VERSATURE_ACCESS_TOKEN")
    client_id = os.getenv("VERSATURE_CLIENT_ID")
    client_secret = os.getenv("VERSATURE_CLIENT_SECRET")
    refresh_access_token = None
    if client_id and client_secret:
        refresh_access_token = lambda: fetch_client_credentials_token(base_url, client_id, client_secret)
    if not access_token:
        if not client_id or not client_secret:
            raise SystemExit(API_AUTH_MESSAGE)
        access_token = fetch_client_credentials_token(base_url, client_id, client_secret)
    return VersatureClient(
        base_url=base_url,
        api_version=api_version,
        access_token=access_token,
        refresh_access_token=refresh_access_token,
    )


def _write_api_inventory(
    data_dir: Path,
    start: str,
    end: str,
    field_inventory: list[str],
    validation: dict,
) -> None:
    out_dir = data_dir / "api_inventory"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "date_range": {"start": start, "end": end},
        "field_count": len(field_inventory),
        "fields": field_inventory,
        "validation": validation,
    }
    (out_dir / f"cdrs_field_inventory_{start}_{end}.json").write_text(
        json.dumps(payload, allow_nan=False, indent=2, sort_keys=True)
    )
    (out_dir / "cdrs_field_inventory_latest.json").write_text(
        json.dumps(payload, allow_nan=False, indent=2, sort_keys=True)
    )


if __name__ == "__main__":
    raise SystemExit(main())
