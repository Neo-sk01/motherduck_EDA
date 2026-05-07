from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv() -> None:
        path = Path(".env")
        if not path.exists():
            return
        for line in path.read_text().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

SourceMode = Literal["csv", "api", "hybrid"]
QueueRole = Literal["primary", "overflow"]


@dataclass(frozen=True)
class QueueConfig:
    queue_id: str
    name: str
    language: str
    role: QueueRole


@dataclass(frozen=True)
class AppConfig:
    motherduck_database: str
    source: SourceMode
    csv_dir: Path
    data_dir: Path
    timezone: str
    queues: tuple[QueueConfig, ...]

    @classmethod
    def from_env(cls) -> "AppConfig":
        load_dotenv(Path.cwd() / ".env")
        return cls(
            motherduck_database=os.getenv("MOTHERDUCK_DATABASE", "csh_analytics_v2"),
            source=parse_source_mode(os.getenv("SOURCE", "csv")),
            csv_dir=Path(os.getenv("CSV_DIR", "./data/csv-uploads")),
            data_dir=Path(os.getenv("DATA_DIR", "./data")),
            timezone=os.getenv("TIMEZONE", "America/Toronto"),
            queues=tuple(build_default_queues()),
        )


def parse_source_mode(value: str) -> SourceMode:
    if value in {"csv", "api", "hybrid"}:
        return value  # type: ignore[return-value]
    raise ValueError("SOURCE must be one of: csv, api, hybrid")


def build_default_queues() -> list[QueueConfig]:
    return [
        QueueConfig(os.getenv("QUEUE_ENGLISH", "8020"), "CSR English", "English", "primary"),
        QueueConfig(os.getenv("QUEUE_FRENCH", "8021"), "CSR French", "French", "primary"),
        QueueConfig(os.getenv("QUEUE_AI_OVERFLOW_EN", "8030"), "CSR Overflow English", "English", "overflow"),
        QueueConfig(os.getenv("QUEUE_AI_OVERFLOW_FR", "8031"), "CSR Overflow French", "French", "overflow"),
    ]
