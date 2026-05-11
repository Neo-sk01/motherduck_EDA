from __future__ import annotations

import hmac
import json
import logging
import os
from dataclasses import dataclass
from datetime import date

import azure.functions as func
import httpx
from azure.identity import ManagedIdentityCredential

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
    expected_key = os.environ.get("ADMIN_API_KEY") or ""
    provided_key = req.headers.get("x-admin-key") or ""
    if not expected_key or not hmac.compare_digest(provided_key, expected_key):
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
        "validated: period=%s start=%s end=%s cache=%s source_ip=%s",
        validated.period, validated.start, validated.end, validated.api_cache_mode,
        req.headers.get("x-forwarded-for", "?"),
    )

    try:
        execution_name = _start_job(validated)
    except httpx.HTTPStatusError as exc:
        log.error(
            "job start failed: status=%s reason=%s",
            exc.response.status_code, exc.response.reason_phrase,
        )
        return func.HttpResponse(
            f"job start failed: HTTP {exc.response.status_code}", status_code=502,
        )
    except Exception as exc:
        log.error("job start failed: %s: %s", type(exc).__name__, exc)
        return func.HttpResponse(
            f"job start failed: {type(exc).__name__}", status_code=502,
        )
    return func.HttpResponse(
        json.dumps({"execution_name": execution_name}),
        status_code=202,
        mimetype="application/json",
    )


@dataclass
class JobUrls:
    get_template: str
    start: str


ARM_BASE = "https://management.azure.com"
API_VERSION = "2024-03-01"


def build_job_urls(subscription_id: str, resource_group: str, job_name: str) -> JobUrls:
    base = (
        f"{ARM_BASE}/subscriptions/{subscription_id}/resourceGroups/{resource_group}"
        f"/providers/Microsoft.App/jobs/{job_name}"
    )
    return JobUrls(
        get_template=f"{base}?api-version={API_VERSION}",
        start=f"{base}/start?api-version={API_VERSION}",
    )


def mutate_template(template: dict, env_overrides: dict[str, str]) -> dict:
    """Return a new JobExecutionTemplate dict with env_overrides applied."""
    out = json.loads(json.dumps(template))
    containers = out.get("containers") or []
    if not containers:
        raise ValueError("template has no containers")
    container = containers[0]
    env = container.get("env") or []
    by_name = {item["name"]: dict(item) for item in env}
    for name, value in env_overrides.items():
        by_name[name] = {"name": name, "value": value}
    container["env"] = list(by_name.values())
    out["containers"] = [container] + containers[1:]
    out["initContainers"] = out.get("initContainers") or []
    return out


def _start_job(validated: ValidatedRequest) -> str:
    subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]
    resource_group = os.environ["AZURE_RESOURCE_GROUP"]
    job_name = os.environ["CONTAINER_APP_JOB_NAME"]
    client_id = os.environ["AZURE_CLIENT_ID"]

    credential = ManagedIdentityCredential(client_id=client_id)
    token = credential.get_token("https://management.azure.com/.default").token
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    urls = build_job_urls(subscription_id, resource_group, job_name)

    with httpx.Client(timeout=30.0) as http:
        get_resp = http.get(urls.get_template, headers=headers)
        get_resp.raise_for_status()
        template = get_resp.json()["properties"]["template"]
        mutated = mutate_template(template, {
            "PERIOD_MODE": "explicit",
            "PERIOD_TYPE": validated.period,
            "PERIOD_START": validated.start,
            "PERIOD_END": validated.end,
            "API_CACHE_MODE": validated.api_cache_mode,
        })
        start_resp = http.post(urls.start, headers=headers, json=mutated)
        start_resp.raise_for_status()
    location = start_resp.headers.get("location", "")
    return location.rsplit("/", 1)[-1] if location else "unknown"
