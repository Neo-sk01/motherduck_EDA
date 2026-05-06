from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pandas as pd

CURATED_COLUMNS = [
    "queue_id",
    "queue_name",
    "language",
    "role",
    "call_id",
    "call_time",
    "call_datetime",
    "date",
    "hour",
    "dow",
    "caller_name",
    "caller_number",
    "caller_number_norm",
    "dnis",
    "agent_extension",
    "agent_phone",
    "agent_name",
    "queue_sec",
    "agent_sec",
    "hold_sec",
    "agent_release_reason",
    "queue_release_reason",
    "handled_flag",
]


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
                queue_name varchar,
                language varchar,
                role varchar,
                call_id varchar,
                call_time varchar,
                call_datetime timestamp,
                date date,
                hour integer,
                dow varchar,
                caller_name varchar,
                caller_number varchar,
                caller_number_norm varchar,
                dnis varchar,
                agent_extension varchar,
                agent_phone varchar,
                agent_name varchar,
                queue_sec double,
                agent_sec double,
                hold_sec double,
                agent_release_reason varchar,
                queue_release_reason varchar,
                handled_flag varchar
            )
            """
        )

    def replace_curated_calls(self, start: str, end: str, df: pd.DataFrame) -> None:
        self.initialize_schema()
        to_write = df.copy()
        for column in CURATED_COLUMNS:
            if column not in to_write.columns:
                to_write[column] = None
        to_write = to_write[CURATED_COLUMNS]
        to_write.insert(0, "period_end", end)
        to_write.insert(0, "period_start", start)
        columns = ["period_start", "period_end", *CURATED_COLUMNS]
        quoted_columns = ", ".join(columns)
        self.connection.execute("begin transaction")
        try:
            self.connection.execute(
                "delete from curated_calls where period_start = ? and period_end = ?",
                [start, end],
            )
            self.connection.register("curated_input", to_write)
            self.connection.execute(
                f"insert into curated_calls ({quoted_columns}) select {quoted_columns} from curated_input"
            )
            self.connection.unregister("curated_input")
            self.connection.execute("commit")
        except Exception:
            self.connection.execute("rollback")
            try:
                self.connection.unregister("curated_input")
            except duckdb.InvalidInputException:
                pass
            raise
