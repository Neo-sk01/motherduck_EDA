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
    return parser.parse_args(argv)


def run_csv(
    config: AppConfig,
    period: str,
    start: str,
    end: str,
    store: AnalyticsStore | None = None,
) -> Path:
    curated_queues = []
    for queue in config.queues:
        csv_path = find_queue_csv(config.csv_dir, queue.queue_id)
        raw = load_queue_csv(csv_path, queue)
        deduped = deduplicate_csv(raw)
        curated_queues.append(curate_csv_calls(deduped))

    curated = pd.concat(curated_queues, ignore_index=True)
    if store is not None:
        store.replace_curated_calls(start, end, curated)

    queue_metrics = {
        queue.queue_id: compute_queue_metrics(curated, queue.queue_id)
        for queue in config.queues
    }
    crossqueue = compute_crossqueue_metrics(curated)
    anomalies = detect_anomalies(queue_metrics, crossqueue)
    return write_report_bundle(
        config.data_dir,
        period,
        start,
        end,
        queue_metrics,
        crossqueue,
        anomalies,
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config = AppConfig.from_env()
    if args.source != "csv":
        raise SystemExit(NON_CSV_MESSAGE)

    store = None
    if os.getenv("MOTHERDUCK_TOKEN_RW"):
        store = AnalyticsStore.motherduck(config.motherduck_database)
    run_csv(config, args.period, args.start, args.end, store=store)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
