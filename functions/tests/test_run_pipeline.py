from datetime import date

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_module_path = Path(__file__).resolve().parents[1] / "run-pipeline" / "__init__.py"
spec = importlib.util.spec_from_file_location("run_pipeline_main", _module_path)
run_pipeline_main = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = run_pipeline_main
spec.loader.exec_module(run_pipeline_main)


parse_and_validate = run_pipeline_main.parse_and_validate


def test_parse_and_validate_accepts_valid_month_request():
    body = {"period": "month", "start": "2026-04-01", "end": "2026-04-30", "api_cache_mode": "auto"}
    result = parse_and_validate(body, now=date(2026, 5, 11))
    assert result.start == "2026-04-01"
    assert result.end == "2026-04-30"
    assert result.api_cache_mode == "auto"
    assert result.period == "month"


def test_parse_and_validate_rejects_non_month_period():
    body = {"period": "day", "start": "2026-04-01", "end": "2026-04-01"}
    with pytest.raises(ValueError, match="month"):
        parse_and_validate(body, now=date(2026, 5, 11))


def test_parse_and_validate_rejects_future_end_date():
    body = {"period": "month", "start": "2026-06-01", "end": "2026-06-30"}
    with pytest.raises(ValueError, match="future"):
        parse_and_validate(body, now=date(2026, 5, 11))


def test_parse_and_validate_rejects_window_over_92_days():
    body = {"period": "month", "start": "2025-01-01", "end": "2025-05-01"}
    with pytest.raises(ValueError, match="92"):
        parse_and_validate(body, now=date(2026, 5, 11))


def test_parse_and_validate_rejects_bad_api_cache_mode():
    body = {"period": "month", "start": "2026-04-01", "end": "2026-04-30", "api_cache_mode": "bogus"}
    with pytest.raises(ValueError, match="api_cache_mode"):
        parse_and_validate(body, now=date(2026, 5, 11))


def test_parse_and_validate_defaults_period_to_month_and_cache_to_auto():
    body = {"start": "2026-04-01", "end": "2026-04-30"}
    result = parse_and_validate(body, now=date(2026, 5, 11))
    assert result.period == "month"
    assert result.api_cache_mode == "auto"


def test_parse_and_validate_rejects_inverted_dates():
    body = {"period": "month", "start": "2026-04-30", "end": "2026-04-01"}
    with pytest.raises(ValueError, match="start <= end"):
        parse_and_validate(body, now=date(2026, 5, 11))


mutate_template = run_pipeline_main.mutate_template
build_job_urls = run_pipeline_main.build_job_urls


def test_mutate_template_overwrites_period_env_vars():
    fetched = {
        "containers": [{
            "name": "pipeline",
            "image": "acr.io/pipeline:abc",
            "command": ["python", "-m", "pipeline.azure_run"],
            "env": [
                {"name": "PERIOD_MODE", "value": "previous-month"},
                {"name": "PERIOD_TYPE", "value": "month"},
                {"name": "API_CACHE_MODE", "value": "auto"},
                {"name": "DATA_DIR", "value": "/data"},
            ],
        }],
        "initContainers": [],
    }
    overrides = {
        "PERIOD_MODE": "explicit",
        "PERIOD_TYPE": "month",
        "PERIOD_START": "2026-04-01",
        "PERIOD_END": "2026-04-30",
        "API_CACHE_MODE": "refresh",
    }
    mutated = mutate_template(fetched, overrides)
    env = {item["name"]: item["value"] for item in mutated["containers"][0]["env"]}
    assert env["PERIOD_MODE"] == "explicit"
    assert env["PERIOD_START"] == "2026-04-01"
    assert env["PERIOD_END"] == "2026-04-30"
    assert env["API_CACHE_MODE"] == "refresh"
    assert env["DATA_DIR"] == "/data"


def test_mutate_template_preserves_other_container_fields():
    fetched = {
        "containers": [{
            "name": "pipeline",
            "image": "acr.io/pipeline:abc",
            "command": ["python", "-m", "pipeline.azure_run"],
            "resources": {"cpu": 1.0, "memory": "2Gi"},
            "env": [{"name": "FOO", "value": "bar"}],
        }],
        "initContainers": [{"name": "init", "image": "init:1"}],
    }
    mutated = mutate_template(fetched, {"PERIOD_MODE": "explicit"})
    assert mutated["containers"][0]["image"] == "acr.io/pipeline:abc"
    assert mutated["containers"][0]["resources"] == {"cpu": 1.0, "memory": "2Gi"}
    assert mutated["initContainers"] == [{"name": "init", "image": "init:1"}]


def test_build_job_urls_constructs_arm_paths():
    urls = build_job_urls(
        subscription_id="11111111-1111-1111-1111-111111111111",
        resource_group="rg-x",
        job_name="my-job",
    )
    assert urls.get_template.endswith(
        "/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/rg-x/providers/Microsoft.App/jobs/my-job?api-version=2024-03-01"
    )
    assert urls.start.endswith(
        "/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/rg-x/providers/Microsoft.App/jobs/my-job/start?api-version=2024-03-01"
    )


class FakeHttpRequest:
    def __init__(self, headers=None, body=None):
        self.headers = headers or {}
        self._body = body or {}

    def get_json(self):
        return self._body


def test_handler_returns_401_when_admin_key_missing(monkeypatch):
    monkeypatch.setenv("ADMIN_API_KEY", "secret")
    resp = run_pipeline_main.main(FakeHttpRequest(headers={}, body={}))
    assert resp.status_code == 401


def test_handler_starts_job_on_valid_request(monkeypatch):
    monkeypatch.setenv("ADMIN_API_KEY", "secret")
    monkeypatch.setenv("AZURE_SUBSCRIPTION_ID", "sub")
    monkeypatch.setenv("AZURE_RESOURCE_GROUP", "rg")
    monkeypatch.setenv("CONTAINER_APP_JOB_NAME", "job")
    monkeypatch.setenv("AZURE_CLIENT_ID", "cid")

    fake_template = {
        "properties": {"template": {"containers": [{"name": "p", "image": "i", "env": []}], "initContainers": []}}
    }
    fake_get = MagicMock(status_code=200, json=MagicMock(return_value=fake_template), raise_for_status=MagicMock())
    fake_post = MagicMock(status_code=200, raise_for_status=MagicMock())
    fake_post.headers = {"location": "https://x/.../jobs/job/executions/exec-abc"}
    fake_http = MagicMock()
    fake_http.__enter__.return_value = fake_http
    fake_http.get.return_value = fake_get
    fake_http.post.return_value = fake_post

    with patch("run_pipeline_main.httpx.Client", return_value=fake_http), \
         patch("run_pipeline_main.ManagedIdentityCredential", create=True) as fake_cred:
        fake_cred.return_value.get_token.return_value.token = "tok"
        resp = run_pipeline_main.main(FakeHttpRequest(
            headers={"x-admin-key": "secret"},
            body={"period": "month", "start": "2026-04-01", "end": "2026-04-30"},
        ))
    assert resp.status_code == 202
    assert b"exec-abc" in resp.get_body()
