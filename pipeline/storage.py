from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from pipeline.config import QueueConfig

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
        self.connection.execute(
            """
            create table if not exists queue_dim (
                queue_id varchar,
                queue_name varchar,
                language varchar,
                role varchar
            )
            """
        )
        self.connection.execute(
            """
            create table if not exists report_runs (
                period_start date,
                period_end date,
                period varchar,
                source_mode varchar,
                status varchar,
                validation_json json,
                generated_at timestamp
            )
            """
        )
        self.connection.execute(
            """
            create table if not exists raw_call_legs (
                period_start date,
                period_end date,
                source_mode varchar,
                queue_id varchar,
                call_id varchar,
                source_file varchar,
                raw_json json
            )
            """
        )
        self.connection.execute(
            """
            create table if not exists queue_period_metrics (
                period_start date,
                period_end date,
                queue_id varchar,
                metrics_json json
            )
            """
        )
        self.connection.execute(
            """
            create table if not exists queue_daily_metrics (
                period_start date,
                period_end date,
                queue_id varchar,
                date date,
                calls integer
            )
            """
        )
        self.connection.execute(
            """
            create table if not exists queue_hourly_metrics (
                period_start date,
                period_end date,
                queue_id varchar,
                hour integer,
                calls integer,
                no_answer_count integer,
                no_answer_rate double
            )
            """
        )
        self.connection.execute(
            """
            create table if not exists queue_dow_metrics (
                period_start date,
                period_end date,
                queue_id varchar,
                dow varchar,
                calls integer
            )
            """
        )
        self.connection.execute(
            """
            create table if not exists agent_queue_metrics (
                period_start date,
                period_end date,
                queue_id varchar,
                agent_name varchar,
                calls integer,
                metrics_json json
            )
            """
        )
        self.connection.execute(
            """
            create table if not exists caller_queue_metrics (
                period_start date,
                period_end date,
                queue_id varchar,
                caller_number_norm varchar,
                calls integer
            )
            """
        )
        self.connection.execute(
            """
            create table if not exists release_reason_metrics (
                period_start date,
                period_end date,
                queue_id varchar,
                reason_type varchar,
                reason varchar,
                calls integer
            )
            """
        )
        self.connection.execute(
            """
            create table if not exists funnel_language_metrics (
                period_start date,
                period_end date,
                language varchar,
                metrics_json json
            )
            """
        )
        self.connection.execute(
            """
            create table if not exists crossqueue_agent_metrics (
                period_start date,
                period_end date,
                agent_name varchar,
                total_calls integer,
                metrics_json json
            )
            """
        )
        self.connection.execute(
            """
            create table if not exists crossqueue_caller_metrics (
                period_start date,
                period_end date,
                caller_number_norm varchar,
                total_calls integer,
                metrics_json json
            )
            """
        )
        self.connection.execute(
            """
            create table if not exists comparative_series (
                period_start date,
                period_end date,
                series_name varchar,
                queue_id varchar,
                bucket varchar,
                metrics_json json
            )
            """
        )
        self.connection.execute(
            """
            create table if not exists anomalies (
                period_start date,
                period_end date,
                kind varchar,
                severity varchar,
                target_json json,
                anomaly_json json
            )
            """
        )

    def replace_queue_dimension(self, queues: tuple[QueueConfig, ...]) -> None:
        self.initialize_schema()
        rows = [(q.queue_id, q.name, q.language, q.role) for q in queues]
        self.connection.execute("delete from queue_dim")
        if rows:
            self.connection.executemany("insert into queue_dim values (?, ?, ?, ?)", rows)

    def replace_raw_call_legs(self, start: str, end: str, df: pd.DataFrame, source_mode: str) -> None:
        self.initialize_schema()
        self.connection.execute("begin transaction")
        try:
            self.connection.execute(
                "delete from raw_call_legs where period_start = ? and period_end = ? and source_mode = ?",
                [start, end, source_mode],
            )
            rows = [
                (
                    start,
                    end,
                    source_mode,
                    _nullable(row.get("source_queue_id")),
                    _nullable(row.get("Orig CallID")),
                    _nullable(row.get("source_file")),
                    _json_dumps(row),
                )
                for row in df.to_dict("records")
            ]
            if rows:
                self.connection.executemany(
                    "insert into raw_call_legs values (?, ?, ?, ?, ?, ?, ?)",
                    rows,
                )
            self.connection.execute("commit")
        except Exception:
            self.connection.execute("rollback")
            raise

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

    def replace_report_outputs(
        self,
        start: str,
        end: str,
        period: str,
        source_mode: str,
        queue_metrics: dict[str, dict[str, Any]],
        crossqueue: dict[str, Any],
        anomalies: list[dict[str, Any]],
        validation: dict[str, Any] | None = None,
    ) -> None:
        self.initialize_schema()
        metric_tables = [
            "report_runs",
            "queue_period_metrics",
            "queue_daily_metrics",
            "queue_hourly_metrics",
            "queue_dow_metrics",
            "agent_queue_metrics",
            "caller_queue_metrics",
            "release_reason_metrics",
            "funnel_language_metrics",
            "crossqueue_agent_metrics",
            "crossqueue_caller_metrics",
            "comparative_series",
            "anomalies",
        ]
        self.connection.execute("begin transaction")
        try:
            for table in metric_tables:
                self.connection.execute(
                    f"delete from {table} where period_start = ? and period_end = ?",
                    [start, end],
                )
            self.connection.execute(
                "insert into report_runs values (?, ?, ?, ?, ?, ?, current_timestamp)",
                [start, end, period, source_mode, "success", _json_dumps(validation or {"status": "success"})],
            )
            for queue_id, metrics in queue_metrics.items():
                self.connection.execute(
                    "insert into queue_period_metrics values (?, ?, ?, ?)",
                    [start, end, queue_id, _json_dumps(metrics)],
                )
                for row in metrics.get("daily_volume", []):
                    self.connection.execute(
                        "insert into queue_daily_metrics values (?, ?, ?, ?, ?)",
                        [start, end, queue_id, row["date"], row["calls"]],
                    )
                for row in metrics.get("hourly_volume", []):
                    self.connection.execute(
                        "insert into queue_hourly_metrics values (?, ?, ?, ?, ?, ?, ?)",
                        [start, end, queue_id, row["hour"], row["calls"], row["no_answer_count"], row["no_answer_rate"]],
                    )
                for row in metrics.get("dow_volume", []):
                    self.connection.execute(
                        "insert into queue_dow_metrics values (?, ?, ?, ?, ?)",
                        [start, end, queue_id, row["dow"], row["calls"]],
                    )
                for row in metrics.get("agent_leaderboard", []):
                    self.connection.execute(
                        "insert into agent_queue_metrics values (?, ?, ?, ?, ?, ?)",
                        [start, end, queue_id, row["agent_name"], row["calls"], _json_dumps(row)],
                    )
                for row in metrics.get("top_callers", []):
                    self.connection.execute(
                        "insert into caller_queue_metrics values (?, ?, ?, ?, ?)",
                        [start, end, queue_id, row["caller_number_norm"], row["calls"]],
                    )
                for reason_type, rows in metrics.get("release_reasons", {}).items():
                    for row in rows:
                        self.connection.execute(
                            "insert into release_reason_metrics values (?, ?, ?, ?, ?, ?)",
                            [start, end, queue_id, reason_type, row["reason"], row["calls"]],
                        )
            for language, metrics in crossqueue.get("funnels", {}).items():
                self.connection.execute(
                    "insert into funnel_language_metrics values (?, ?, ?, ?)",
                    [start, end, language, _json_dumps(metrics)],
                )
            for row in crossqueue.get("agents", []):
                self.connection.execute(
                    "insert into crossqueue_agent_metrics values (?, ?, ?, ?, ?)",
                    [start, end, row["agent_name"], row["total_calls"], _json_dumps(row)],
                )
            for row in crossqueue.get("callers", []):
                self.connection.execute(
                    "insert into crossqueue_caller_metrics values (?, ?, ?, ?, ?)",
                    [start, end, row["caller_number_norm"], row["total_calls"], _json_dumps(row)],
                )
            for series_name in ("same_hour_no_answer", "same_day_volume"):
                for row in crossqueue.get(series_name, []):
                    self.connection.execute(
                        "insert into comparative_series values (?, ?, ?, ?, ?, ?)",
                        [
                            start,
                            end,
                            series_name,
                            row.get("queue_id"),
                            str(row.get("hour", row.get("date"))),
                            _json_dumps(row),
                        ],
                    )
            for row in anomalies:
                self.connection.execute(
                    "insert into anomalies values (?, ?, ?, ?, ?, ?)",
                    [
                        start,
                        end,
                        row.get("kind"),
                        row.get("severity"),
                        _json_dumps(row.get("target", {})),
                        _json_dumps(row),
                    ],
                )
            self.connection.execute("commit")
        except Exception:
            self.connection.execute("rollback")
            raise


def _nullable(value: Any) -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return str(value)


def _json_dumps(value: Any) -> str:
    return json.dumps(_json_ready(value), allow_nan=False, sort_keys=True, default=str)


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_ready(v) for v in value]
    if isinstance(value, tuple):
        return [_json_ready(v) for v in value]
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value
