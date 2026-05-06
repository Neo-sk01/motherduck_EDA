from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd

from pipeline.anomaly import detect_anomalies
from pipeline.config import AppConfig
from pipeline.crossqueue import compute_crossqueue_metrics
from pipeline.curate import curate_csv_calls
from pipeline.dedup import deduplicate_csv
from pipeline.ingest_csv import find_queue_csv, load_queue_csv
from pipeline.metrics_queue import compute_queue_metrics
from pipeline.parse import parse_csv_call_time
from pipeline.report import write_report_bundle
from pipeline.storage import AnalyticsStore

NON_CSV_MESSAGE = (
    "Only CSV orchestration is executable at this milestone; API and hybrid modules are "
    "implemented separately."
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=("csv", "api", "hybrid"), required=True)
    parser.add_argument("--period", choices=("day", "week", "month"), required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--write-store", action="store_true")
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
        curated_queues.append(curate_csv_calls(deduped))

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
        )
        missing = ", ".join(gap["queue_id"] for gap in source_gaps)
        raise FileNotFoundError(f"Missing required queue CSVs for {missing}; source gap report written to {out_dir}")

    curated = pd.concat(curated_queues, ignore_index=True)
    queue_metrics = {
        queue.queue_id: compute_queue_metrics(curated, queue.queue_id)
        for queue in config.queues
    }
    crossqueue = compute_crossqueue_metrics(curated)
    anomalies = detect_anomalies(queue_metrics, crossqueue)
    out_dir = write_report_bundle(
        config.data_dir,
        period,
        start,
        end,
        queue_metrics,
        crossqueue,
        anomalies,
    )
    if store is not None:
        store.replace_queue_dimension(config.queues)
        store.replace_raw_call_legs(start, end, pd.concat(raw_queues, ignore_index=True), source_mode="csv")
        store.replace_curated_calls(start, end, curated)
        store.replace_report_outputs(start, end, period, "csv", queue_metrics, crossqueue, anomalies)
    return out_dir


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.source != "csv":
        raise SystemExit(NON_CSV_MESSAGE)

    config = AppConfig.from_env()
    store = None
    if args.write_store:
        if not os.getenv("MOTHERDUCK_TOKEN_RW"):
            raise SystemExit("MOTHERDUCK_TOKEN_RW is required when --write-store is set.")
        store = AnalyticsStore.motherduck(config.motherduck_database)
    run_csv(config, args.period, args.start, args.end, store=store)
    return 0


def _filter_raw_date_range(raw: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    start_date = pd.Timestamp(start).normalize()
    end_date = pd.Timestamp(end).normalize()
    call_dates = parse_csv_call_time(raw["Call Time"]).dt.normalize()
    return raw.loc[call_dates.between(start_date, end_date)].reset_index(drop=True)


if __name__ == "__main__":
    raise SystemExit(main())
