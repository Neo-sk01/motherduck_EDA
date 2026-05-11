from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import date

import azure.functions as func

log = logging.getLogger(__name__)


@dataclass
class ValidatedRequest:
    period: str
    start: str
    end: str
    api_cache_mode: str


def parse_and_validate(body: dict, now: date | None = None) -> ValidatedRequest:
    now = now or date.today()
    period = body.get("period", "month")
    if period != "month":
        raise ValueError(f"period must be 'month' in v1 (got {period!r})")
    api_cache_mode = body.get("api_cache_mode", "auto")
    if api_cache_mode not in {"auto", "refresh", "reuse"}:
        raise ValueError(f"api_cache_mode must be auto|refresh|reuse (got {api_cache_mode!r})")
    start_str = body.get("start")
    end_str = body.get("end")
    try:
        start = date.fromisoformat(start_str)
        end = date.fromisoformat(end_str)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"start and end must be ISO YYYY-MM-DD dates: {exc}") from exc
    if start > end:
        raise ValueError("start <= end is required")
    if end > now:
        raise ValueError("end must not be in the future")
    if (end - start).days > 92:
        raise ValueError("window exceeds 92 days")
    return ValidatedRequest(period=period, start=start_str, end=end_str, api_cache_mode=api_cache_mode)


def main(req: func.HttpRequest) -> func.HttpResponse:
    expected_key = os.environ.get("ADMIN_API_KEY")
    provided_key = req.headers.get("x-admin-key")
    if not expected_key or not provided_key or provided_key != expected_key:
        log.info("admin key mismatch from %s", req.headers.get("x-forwarded-for", "?"))
        return func.HttpResponse("unauthorized", status_code=401)
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse("body must be JSON", status_code=400)
    try:
        validated = parse_and_validate(body)
    except ValueError as exc:
        return func.HttpResponse(str(exc), status_code=400)
    log.info(
        "validated request: period=%s start=%s end=%s cache=%s",
        validated.period, validated.start, validated.end, validated.api_cache_mode,
    )
    return func.HttpResponse(
        json.dumps({"execution_name": "stub-not-yet-implemented"}),
        status_code=501,
        mimetype="application/json",
    )
