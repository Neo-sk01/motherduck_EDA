import json

import pytest
from azure.core.exceptions import ResourceModifiedError, ResourceNotFoundError

from pipeline.blob_upload import compute_merged_manifest
from pipeline.blob_upload import upload_period_files
from pipeline.blob_upload import upload_manifest_with_cas


def _entry(key, start, end, source="api", status="success"):
    return {
        "key": key,
        "label": f"{key} label",
        "start": start,
        "end": end,
        "path": f"month_{start}_{end}/metrics.json",
        "source": source,
        "validation_status": status,
    }


def test_compute_merged_manifest_seeds_empty():
    new = _entry("2026-04", "2026-04-01", "2026-04-30")
    merged = compute_merged_manifest(existing={"reports": []}, new_entry=new)
    assert merged == {"reports": [new]}


def test_compute_merged_manifest_appends_new_period():
    march = _entry("2026-03", "2026-03-01", "2026-03-31")
    april = _entry("2026-04", "2026-04-01", "2026-04-30")
    merged = compute_merged_manifest(existing={"reports": [march]}, new_entry=april)
    assert [r["key"] for r in merged["reports"]] == ["2026-04", "2026-03"]


def test_compute_merged_manifest_replaces_same_key():
    april_csv = _entry("2026-04", "2026-04-01", "2026-04-30", source="csv")
    april_api = _entry("2026-04", "2026-04-01", "2026-04-30", source="api")
    merged = compute_merged_manifest(existing={"reports": [april_csv]}, new_entry=april_api)
    assert len(merged["reports"]) == 1
    assert merged["reports"][0]["source"] == "api"


def test_compute_merged_manifest_handles_none_existing():
    new = _entry("2026-04", "2026-04-01", "2026-04-30")
    merged = compute_merged_manifest(existing=None, new_entry=new)
    assert merged == {"reports": [new]}


def test_compute_merged_manifest_tolerates_malformed_existing():
    new = _entry("2026-04", "2026-04-01", "2026-04-30")
    merged = compute_merged_manifest(existing={"reports": "not-a-list"}, new_entry=new)
    assert merged == {"reports": [new]}


class FakeManifestBlob:
    """In-memory fake of azure.storage.blob.BlobClient for manifest CAS testing."""

    def __init__(self, initial: bytes | None = None, etag: str = "etag-0"):
        self._body = initial
        self._etag = etag
        self.upload_calls: list[tuple[bytes, str | None]] = []
        self.fail_next_uploads: int = 0

    def download_blob(self):
        if self._body is None:
            raise ResourceNotFoundError("not found")
        return _FakeDownload(self._body, self._etag)

    def upload_blob(self, data, overwrite=True, etag=None, match_condition=None):
        if self.fail_next_uploads > 0:
            self.fail_next_uploads -= 1
            self._etag = f"{self._etag}-concurrent"
            raise ResourceModifiedError("If-Match precondition failed")
        body = data if isinstance(data, bytes) else data.encode("utf-8") if isinstance(data, str) else bytes(data)
        self._body = body
        self._etag = f"etag-{len(self.upload_calls) + 1}"
        self.upload_calls.append((body, etag))


class _FakeDownload:
    def __init__(self, body: bytes, etag: str):
        self._body = body
        self.properties = type("Props", (), {"etag": etag})()

    def readall(self) -> bytes:
        return self._body


def _new_entry():
    return {
        "key": "2026-04",
        "label": "April 2026",
        "start": "2026-04-01",
        "end": "2026-04-30",
        "path": "month_2026-04-01_2026-04-30/metrics.json",
        "source": "api",
        "validation_status": "success",
    }


def test_upload_manifest_with_cas_first_writer():
    blob = FakeManifestBlob(initial=None)
    upload_manifest_with_cas(blob, _new_entry())
    assert len(blob.upload_calls) == 1
    body, sent_etag = blob.upload_calls[0]
    payload = json.loads(body)
    assert payload["reports"][0]["key"] == "2026-04"
    assert sent_etag is None


def test_upload_manifest_with_cas_merges_existing():
    existing = {"reports": [{
        "key": "2026-03", "label": "March 2026", "start": "2026-03-01", "end": "2026-03-31",
        "path": "month_2026-03-01_2026-03-31/metrics.json", "source": "api",
        "validation_status": "success"
    }]}
    blob = FakeManifestBlob(initial=json.dumps(existing).encode())
    upload_manifest_with_cas(blob, _new_entry())
    body, sent_etag = blob.upload_calls[0]
    payload = json.loads(body)
    keys = [r["key"] for r in payload["reports"]]
    assert keys == ["2026-04", "2026-03"]
    assert sent_etag == "etag-0"


def test_upload_manifest_with_cas_retries_on_412():
    blob = FakeManifestBlob(initial=b'{"reports": []}')
    blob.fail_next_uploads = 2
    upload_manifest_with_cas(blob, _new_entry(), max_attempts=5)
    assert len(blob.upload_calls) == 1


def test_upload_manifest_with_cas_gives_up_after_max_attempts():
    blob = FakeManifestBlob(initial=b'{"reports": []}')
    blob.fail_next_uploads = 10
    with pytest.raises(RuntimeError, match="manifest"):
        upload_manifest_with_cas(blob, _new_entry(), max_attempts=3)


class FakeContainer:
    def __init__(self):
        self.uploads: list[tuple[str, bytes]] = []

    def upload_blob(self, name, data, overwrite=True):
        body = data.read() if hasattr(data, "read") else data
        self.uploads.append((name, body))


def test_upload_period_files_uploads_every_file(tmp_path):
    period = "month_2026-04-01_2026-04-30"
    period_dir = tmp_path / "reports" / period
    period_dir.mkdir(parents=True)
    (period_dir / "metrics.json").write_text('{"a": 1}')
    (period_dir / "metrics_8020.json").write_text('{"b": 2}')
    container = FakeContainer()
    count = upload_period_files(container, tmp_path, period)
    assert count == 2
    names = sorted(name for name, _ in container.uploads)
    assert names == [f"{period}/metrics.json", f"{period}/metrics_8020.json"]


def test_upload_period_files_errors_when_dir_missing(tmp_path):
    container = FakeContainer()
    with pytest.raises(FileNotFoundError):
        upload_period_files(container, tmp_path, "month_2026-04-01_2026-04-30")


def test_upload_reports_skips_when_env_unset(tmp_path, monkeypatch):
    monkeypatch.delenv("REPORTS_STORAGE_ACCOUNT_URL", raising=False)
    from pipeline.blob_upload import upload_reports

    upload_reports(tmp_path, "month_2026-04-01_2026-04-30", _new_entry())
