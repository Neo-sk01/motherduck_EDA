from __future__ import annotations

from pathlib import Path

import pandas as pd

from pipeline.config import QueueConfig


def find_queue_csv(csv_dir: Path, queue_id: str) -> Path:
    matches = sorted(csv_dir.glob(f"*_{queue_id}_*.csv"))
    if not matches:
        raise FileNotFoundError(f"No CSV found for queue {queue_id} in {csv_dir}")
    if len(matches) > 1:
        names = ", ".join(path.name for path in matches)
        raise ValueError(f"Multiple CSV files found for queue {queue_id}: {names}")
    return matches[0]


def load_queue_csv(path: Path, queue: QueueConfig) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["source_queue_id"] = queue.queue_id
    df["source_queue_name"] = queue.name
    df["source_language"] = queue.language
    df["source_role"] = queue.role
    df["source_file"] = str(path)
    return df
