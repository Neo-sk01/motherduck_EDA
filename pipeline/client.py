"""Versature API client."""

from __future__ import annotations

import time
from typing import Any

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_fixed


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
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._page_spacing_seconds = 0.0
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

        while True:
            payload = self._get_json("/cdrs/users/", params)
            rows.extend(payload["result"])

            if not payload.get("more"):
                return rows

            cursor = payload.get("cursor")
            if cursor is None or str(cursor).strip() == "":
                raise ValueError("Expected Versature more=true response is missing cursor")
            params["cursor"] = str(cursor)
            time.sleep(self._page_spacing_seconds)

    @retry(
        retry=retry_if_exception(_is_retryable_http_error),
        stop=stop_after_attempt(3),
        wait=wait_fixed(0),
        reraise=True,
    )
    def _get_json(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        response = self._client.get(path, params=params)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or "result" not in payload:
            raise ValueError("Expected Versature response to include top-level result")
        if not isinstance(payload["result"], list):
            raise ValueError("Expected Versature response result to be a list")
        return payload
