from pathlib import Path

import pandas as pd

from pipeline.config import QueueConfig
from pipeline.ingest_csv import find_queue_csv, load_queue_csv


def test_find_queue_csv_matches_queue_id(tmp_path: Path):
    path = tmp_path / "queue_details_2026-04-01_2026-04-30_8020_undefined.csv"
    path.write_text("Call Time,Orig CallID\n04/01/2026 8:33 am,a\n")
    found = find_queue_csv(tmp_path, "8020")
    assert found == path


def test_load_queue_csv_adds_source_metadata(tmp_path: Path):
    path = tmp_path / "queue_details_2026-04-01_2026-04-30_8020_undefined.csv"
    pd.DataFrame([{"Call Time": "04/01/2026 8:33 am", "Orig CallID": "a"}]).to_csv(path, index=False)
    queue = QueueConfig("8020", "CSR English", "English", "primary")
    df = load_queue_csv(path, queue)
    assert df.loc[0, "source_queue_id"] == "8020"
    assert df.loc[0, "source_queue_name"] == "CSR English"
    assert df.loc[0, "source_language"] == "English"
    assert df.loc[0, "source_role"] == "primary"
    assert df.loc[0, "source_file"].endswith("_8020_undefined.csv")
