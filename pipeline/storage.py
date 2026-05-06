from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pandas as pd


class AnalyticsStore:
    def __init__(self, connection: duckdb.DuckDBPyConnection):
        self.connection = connection

    @classmethod
    def local(cls, path: Path) -> "AnalyticsStore":
        return cls(duckdb.connect(str(path)))

    @classmethod
    def motherduck(cls, database: str, token_env: str = "MOTHERDUCK_TOKEN_RW") -> "AnalyticsStore":
        token = os.environ[token_env]
        conn = duckdb.connect(f"md:{database}?motherduck_token={token}")
        return cls(conn)

    def initialize_schema(self) -> None:
        self.connection.execute(
            """
            create table if not exists curated_calls (
                period_start date,
                period_end date,
                queue_id varchar,
                call_id varchar,
                date date,
                agent_name varchar
            )
            """
        )

    def replace_curated_calls(self, start: str, end: str, df: pd.DataFrame) -> None:
        self.initialize_schema()
        self.connection.execute(
            "delete from curated_calls where period_start = ? and period_end = ?",
            [start, end],
        )
        to_write = df.copy()
        to_write.insert(0, "period_end", end)
        to_write.insert(0, "period_start", start)
        self.connection.register("curated_input", to_write)
        self.connection.execute("insert into curated_calls select * from curated_input")
        self.connection.unregister("curated_input")
