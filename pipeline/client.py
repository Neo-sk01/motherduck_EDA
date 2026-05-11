"""Versature API client."""

from __future__ import annotations

import time
import os
import sys
from collections.abc import Callable
from typing import Any

import httpx
from tenacity import RetryCallState, retry, retry_if_exception, stop_after_attempt


def _is_retryable_http_error(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        return status_code == 429 or status_code >= 500
    return isinstance(exc, httpx.TransportError)


class VersatureClient:
    """Small client for Versature call detail record endpoints."""

    def __init__(
        self,
        base_url: str,
        api_version: str,
        access_token: str,
        refresh_access_token: Callable[[], str] | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._page_spacing_seconds = float(os.getenv("VERSATURE_PAGE_SPACING_SECONDS", "0.5"))
        self._progress_every_pages = int(os.getenv("VERSATURE_PROGRESS_EVERY_PAGES", "25"))
        self._refresh_access_token = refresh_access_token
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": api_version,
            },
            transport=transport,
            timeout=30.0,
        )

    def get_cdr_users(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        params: dict[str, str] = {"start_date": start_date, "end_date": end_date}
        pages = 0

        while True:
            payload = self._get_json("/cdrs/users/", params)
            pages += 1
            rows.extend(payload["result"])
            if self._progress_every_pages > 0 and pages % self._progress_every_pages == 0:
                print(
                    f"Fetched {len(rows)} CDR rows across {pages} pages for {start_date} to {end_date}",
                    file=sys.stderr,
                    flush=True,
                )

            if not payload.get("more"):
                if pages > 1:
                    print(
                        f"Finished {len(rows)} CDR rows across {pages} pages for {start_date} to {end_date}",
                        file=sys.stderr,
                        flush=True,
                    )
                return rows

            cursor = payload.get("cursor")
            if cursor is None or str(cursor).strip() == "":
                raise ValueError("Expected Versature more=true response is missing cursor")
            params["cursor"] = str(cursor)
            time.sleep(self._page_spacing_seconds)

    def get_call_queue_stats(self, queue_id: str, start_date: str, end_date: str) -> dict[str, Any]:
        response = self._get_with_auth_refresh(
            f"/call_queues/{queue_id}/stats/",
            params={"start_date": start_date, "end_date": end_date},
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, list) and payload:
            row = payload[0]
            if isinstance(row, dict):
                return row
        raise ValueError(f"Expected stats response for queue {queue_id} to include one object")

    @retry(
        retry=retry_if_exception(_is_retryable_http_error),
        stop=stop_after_attempt(8),
        wait=lambda retry_state: _retry_wait_seconds(retry_state),
        reraise=True,
    )
    def _get_json(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        response = self._get_with_auth_refresh(path, params=params)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or "result" not in payload:
            raise ValueError("Expected Versature response to include top-level result")
        if not isinstance(payload["result"], list):
            raise ValueError("Expected Versature response result to be a list")
        return payload

    def _get_with_auth_refresh(self, path: str, params: dict[str, Any]) -> httpx.Response:
        response = self._client.get(path, params=params)
        if response.status_code != 401 or self._refresh_access_token is None:
            return response
        self._set_access_token(self._refresh_access_token())
        return self._client.get(path, params=params)

    def _set_access_token(self, access_token: str) -> None:
        self._client.headers["Authorization"] = f"Bearer {access_token}"


def fetch_client_credentials_token(
    base_url: str,
    client_id: str,
    client_secret: str,
    transport: httpx.BaseTransport | None = None,
) -> str:
    client = httpx.Client(base_url=base_url.rstrip("/"), transport=transport, timeout=30.0)
    response = client.post(
        "/oauth/token/",
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )
    response.raise_for_status()
    payload = response.json()
    access_token = payload.get("access_token") if isinstance(payload, dict) else None
    if not isinstance(access_token, str) or not access_token:
        raise ValueError("Expected Versature token response to include access_token")
    return access_token


def _retry_wait_seconds(retry_state: RetryCallState) -> float:
    exception = retry_state.outcome.exception() if retry_state.outcome else None
    if isinstance(exception, httpx.HTTPStatusError):
        retry_after = exception.response.headers.get("Retry-After")
        if retry_after is not None:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                pass
    return min(30.0, float(2 ** max(0, retry_state.attempt_number - 1)))
