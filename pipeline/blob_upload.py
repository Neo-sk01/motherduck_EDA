from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from azure.core import MatchConditions
from azure.core.exceptions import ResourceModifiedError, ResourceNotFoundError
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.storage.blob import BlobServiceClient

log = logging.getLogger(__name__)


def compute_merged_manifest(existing: dict[str, Any] | None, new_entry: dict[str, Any]) -> dict[str, Any]:
    reports: list[dict[str, Any]]
    if existing is None:
        reports = []
    else:
        raw = existing.get("reports")
        reports = list(raw) if isinstance(raw, list) else []
    key = new_entry["key"]
    reports = [row for row in reports if not (isinstance(row, dict) and row.get("key") == key)]
    reports.append(new_entry)
    reports.sort(key=lambda row: str(row.get("start", "")), reverse=True)
    return {"reports": reports}


def upload_manifest_with_cas(
    blob_client,
    new_entry: dict[str, Any],
    max_attempts: int = 5,
    backoff_seconds: float = 0.5,
) -> None:
    """Upload manifest.json with ETag compare-and-swap."""
    for attempt in range(1, max_attempts + 1):
        existing, etag = _download_existing(blob_client)
        merged = compute_merged_manifest(existing, new_entry)
        body = json.dumps(merged, indent=2, sort_keys=True).encode("utf-8")
        try:
            if etag is None:
                blob_client.upload_blob(body, overwrite=True, etag=None, match_condition=MatchConditions.IfMissing)
            else:
                blob_client.upload_blob(body, overwrite=True, etag=etag, match_condition=MatchConditions.IfNotModified)
            return
        except ResourceModifiedError:
            log.warning("manifest CAS collision on attempt %d/%d", attempt, max_attempts)
            time.sleep(backoff_seconds * attempt)
    raise RuntimeError(f"failed to update manifest after {max_attempts} attempts")


def _download_existing(blob_client) -> tuple[dict[str, Any] | None, str | None]:
    try:
        download = blob_client.download_blob()
    except ResourceNotFoundError:
        return None, None
    body = download.readall()
    payload = json.loads(body) if body else None
    etag = getattr(getattr(download, "properties", None), "etag", None)
    return payload, etag


def upload_period_files(container_client, data_dir: Path, period_dir_name: str) -> int:
    """Upload all files under data_dir/reports/<period_dir_name>/ to the container."""
    source = Path(data_dir) / "reports" / period_dir_name
    if not source.is_dir():
        raise FileNotFoundError(f"period directory not found: {source}")
    count = 0
    for file in sorted(source.iterdir()):
        if not file.is_file():
            continue
        blob_name = f"{period_dir_name}/{file.name}"
        with file.open("rb") as fh:
            container_client.upload_blob(name=blob_name, data=fh, overwrite=True)
        count += 1
    return count


def upload_reports(data_dir: Path, period_dir_name: str, manifest_entry: dict[str, Any]) -> None:
    """Top-level uploader called by pipeline.azure_run after a successful run."""
    account_url = os.environ.get("REPORTS_STORAGE_ACCOUNT_URL")
    if not account_url:
        log.info("REPORTS_STORAGE_ACCOUNT_URL unset; skipping blob upload")
        return
    container_name = os.environ.get("REPORTS_CONTAINER", "reports")
    credential = _build_credential()
    service = BlobServiceClient(account_url=account_url, credential=credential)
    container = service.get_container_client(container_name)

    files_uploaded = upload_period_files(container, data_dir, period_dir_name)
    log.info("uploaded %d period files under %s", files_uploaded, period_dir_name)

    manifest_blob = container.get_blob_client("manifest.json")
    upload_manifest_with_cas(manifest_blob, manifest_entry)
    log.info("manifest.json updated with entry %s", manifest_entry["key"])


def _build_credential():
    """Use ManagedIdentityCredential when AZURE_CLIENT_ID is set."""
    client_id = os.environ.get("AZURE_CLIENT_ID")
    if client_id:
        return ManagedIdentityCredential(client_id=client_id)
    return DefaultAzureCredential()
