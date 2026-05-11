from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

import pandas as pd

from pipeline.config import QueueConfig
from pipeline.dedup import deduplicate_api
from pipeline.flatten import flatten_record, inventory_field_paths
from pipeline.parse import normalize_caller_number, to_seconds


@dataclass(frozen=True)
class ApiCuratedResult:
    raw_flat: pd.DataFrame
    curated: pd.DataFrame
    field_inventory: list[str]
    source_gaps: list[dict[str, str]]
    validation: dict[str, Any]


CALL_ID_FIELD = "from.call_id"
START_TIME_FIELD = "start_time"

QUEUE_FIELD_CANDIDATES = (
    "by.user",
    "by.username",
    "by.value",
    "call_queue.id",
    "call_queue.queue",
    "call_queue.number",
    "call_queue.extension",
    "queue.id",
    "queue.queue",
    "queue.number",
    "queue.extension",
    "to.call_queue.id",
    "to.call_queue.queue",
    "to.queue.id",
    "to.queue",
)
CALLER_FIELD_CANDIDATES = (
    "from.number",
    "from.user.number",
    "from.uri",
    "from.user",
    "caller.number",
    "caller_number",
)
DNIS_FIELD_CANDIDATES = (
    "dnis",
    "dialled_number",
    "dialed_number",
    "to.number",
    "to.uri",
)
AGENT_NAME_FIELD_CANDIDATES = (
    "agent.name",
    "to.user.name",
    "to.name",
    "to.user",
    "user.name",
    "answered_by.name",
    "to.username",
)
AGENT_EXTENSION_FIELD_CANDIDATES = (
    "agent.extension",
    "to.user.extension",
    "to.user",
    "user.extension",
    "to.extension",
)
AGENT_PHONE_FIELD_CANDIDATES = (
    "agent.phone",
    "to.user.phone",
    "user.phone",
    "to.number",
)
ANSWER_TIME_FIELD_CANDIDATES = ("answer_time", "answered_at")
QUEUE_SECONDS_FIELD_CANDIDATES = ("queue_time", "wait_time", "time_in_queue", "queue_duration")
AGENT_SECONDS_FIELD_CANDIDATES = ("agent_time", "talk_time", "duration", "call_duration")
HOLD_SECONDS_FIELD_CANDIDATES = ("hold_time", "hold_duration")
RELEASE_REASON_FIELD_CANDIDATES = (
    "queue_release_reason",
    "release_reason",
    "disposition",
    "termination_reason",
)
AGENT_RELEASE_REASON_FIELD_CANDIDATES = (
    "agent_release_reason",
    "release_reason",
    "disposition",
    "termination_reason",
)


def curate_api_records(
    records: list[dict[str, Any]],
    queues: tuple[QueueConfig, ...],
    timezone: str,
    start: str | None = None,
    end: str | None = None,
) -> ApiCuratedResult:
    raw_flat = pd.DataFrame([flatten_record(record) for record in records])
    field_inventory = inventory_field_paths(records)
    if raw_flat.empty:
        return ApiCuratedResult(
            raw_flat=raw_flat,
            curated=_empty_curated_frame(),
            field_inventory=field_inventory,
            source_gaps=[],
            validation={"status": "success", "record_count": 0, "deduped_count": 0},
        )

    missing = [field for field in (CALL_ID_FIELD, START_TIME_FIELD) if field not in raw_flat.columns]
    if missing:
        message = f"Missing required API fields: {', '.join(missing)}"
        return ApiCuratedResult(
            raw_flat=raw_flat,
            curated=_empty_curated_frame(),
            field_inventory=field_inventory,
            source_gaps=[{"queue_id": "all", "reason": "missing_api_fields", "message": message}],
            validation={"status": "source_gap", "missing_required_fields": missing},
        )

    deduped = deduplicate_api(raw_flat)
    queue_by_id = {str(queue.queue_id): queue for queue in queues}
    rows: list[dict[str, Any]] = []
    unresolved = 0

    for _, row in deduped.iterrows():
        call_id = str(row[CALL_ID_FIELD])
        call_dt = _parse_api_timestamp(row[START_TIME_FIELD], timezone)
        if start is not None and call_dt.normalize() < pd.Timestamp(start).normalize():
            continue
        if end is not None and call_dt.normalize() > pd.Timestamp(end).normalize():
            continue

        queue = _resolve_queue(row, queues)
        if queue is None:
            unresolved += 1
            continue

        caller_number = _extract_caller_number(_first_present(row, CALLER_FIELD_CANDIDATES))
        answer_time = _first_present(row, ANSWER_TIME_FIELD_CANDIDATES)
        agent_name = _clean_text(_first_present(row, AGENT_NAME_FIELD_CANDIDATES))
        handled = _has_value(answer_time) or _has_value(agent_name)
        rows.append(
            {
                "queue_id": str(queue.queue_id),
                "queue_name": queue.name,
                "language": queue.language,
                "role": queue.role,
                "call_id": call_id,
                "call_time": str(row[START_TIME_FIELD]),
                "call_datetime": call_dt,
                "date": call_dt.strftime("%Y-%m-%d"),
                "hour": int(call_dt.hour),
                "dow": call_dt.day_name(),
                "caller_name": _clean_text(row.get("from.name")),
                "caller_number": caller_number,
                "caller_number_norm": normalize_caller_number(caller_number, row_key=call_id),
                "dnis": _clean_text(_first_present(row, DNIS_FIELD_CANDIDATES)),
                "agent_extension": _clean_text(_first_present(row, AGENT_EXTENSION_FIELD_CANDIDATES)),
                "agent_phone": _clean_text(_first_present(row, AGENT_PHONE_FIELD_CANDIDATES)),
                "agent_name": agent_name,
                "queue_sec": _coerce_seconds(_first_present(row, QUEUE_SECONDS_FIELD_CANDIDATES)),
                "agent_sec": _coerce_seconds(_first_present(row, AGENT_SECONDS_FIELD_CANDIDATES)),
                "hold_sec": _coerce_seconds(_first_present(row, HOLD_SECONDS_FIELD_CANDIDATES)),
                "agent_release_reason": _clean_text(_first_present(row, AGENT_RELEASE_REASON_FIELD_CANDIDATES)),
                "queue_release_reason": _clean_text(_first_present(row, RELEASE_REASON_FIELD_CANDIDATES)),
                "handled_flag": "Handled" if handled else "No Agent",
                "source_queue_id": str(queue.queue_id),
                "Orig CallID": call_id,
                "source_file": "versature_api",
            }
        )

    curated = pd.DataFrame(rows)
    if curated.empty:
        curated = _empty_curated_frame()

    source_gaps: list[dict[str, str]] = []
    status = "success"
    if unresolved and curated.empty:
        status = "source_gap"
        source_gaps.append(
            {
                "queue_id": "all",
                "reason": "unmapped_queue",
                "message": f"{unresolved} API CDR rows could not be mapped to tracked queue IDs.",
            }
        )

    raw_flat = raw_flat.copy()
    raw_flat["source_queue_id"] = [_resolve_queue_id_for_raw(row, queues) for _, row in raw_flat.iterrows()]
    raw_flat["Orig CallID"] = raw_flat[CALL_ID_FIELD]
    raw_flat["source_file"] = "versature_api"

    return ApiCuratedResult(
        raw_flat=raw_flat,
        curated=curated,
        field_inventory=field_inventory,
        source_gaps=source_gaps,
        validation={
            "status": status,
            "record_count": int(len(raw_flat)),
            "deduped_count": int(len(deduped)),
            "curated_count": int(len(curated)),
            "ignored_unmapped_queue_rows": unresolved,
        },
    )


def _empty_curated_frame() -> pd.DataFrame:
    columns = [
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
        "source_queue_id",
        "Orig CallID",
        "source_file",
    ]
    return pd.DataFrame(columns=columns)


def _resolve_queue(row: pd.Series, queues: tuple[QueueConfig, ...]) -> QueueConfig | None:
    queue_id = _resolve_queue_id_for_raw(row, queues)
    if queue_id is None:
        return None
    return next((queue for queue in queues if str(queue.queue_id) == queue_id), None)


def _resolve_queue_id_for_raw(row: pd.Series, queues: tuple[QueueConfig, ...]) -> str | None:
    queue_ids = {str(queue.queue_id) for queue in queues}
    queue_names = {queue.name.casefold(): str(queue.queue_id) for queue in queues}
    for field in QUEUE_FIELD_CANDIDATES:
        value = _clean_text(row.get(field))
        if value is None:
            continue
        if value in queue_ids:
            return value
        if value.casefold() in queue_names:
            return queue_names[value.casefold()]
    for field, value in row.items():
        field_name = str(field).casefold()
        if "queue" not in field_name and "call_queue" not in field_name:
            continue
        text = _clean_text(value)
        if text is None:
            continue
        if text in queue_ids:
            return text
        for queue in queues:
            if queue.name.casefold() in text.casefold():
                return str(queue.queue_id)
    return None


def _first_present(row: pd.Series, candidates: tuple[str, ...]) -> Any:
    for field in candidates:
        value = row.get(field)
        if _has_value(value):
            return value
    return None


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return text != "" and text.casefold() != "null"


def _clean_text(value: Any) -> str | None:
    if not _has_value(value):
        return None
    return str(value).strip()


def _extract_caller_number(value: Any) -> str | None:
    text = _clean_text(value)
    if text is None:
        return None
    sip_match = re.search(r"sip:([^@;>]+)", text, flags=re.IGNORECASE)
    if sip_match:
        return sip_match.group(1)
    return text


def _parse_api_timestamp(value: Any, timezone: str) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize(timezone)
    else:
        timestamp = timestamp.tz_convert(timezone)
    return timestamp.tz_localize(None)


def _coerce_seconds(value: Any) -> float:
    if not _has_value(value):
        return math.nan
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    text = str(value).strip()
    if re.fullmatch(r"\d+(\.\d+)?", text):
        return float(text)
    return to_seconds(text)
