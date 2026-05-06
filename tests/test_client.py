import httpx

from pipeline.client import VersatureClient
from pipeline.flatten import flatten_record, inventory_field_paths


def test_flatten_record_and_inventory_field_paths():
    records = [
        {
            "from": {"call_id": "from-a", "user": "alice"},
            "to": {"call_id": "to-a"},
            "duration": 42,
        },
        {
            "from": {"call_id": "from-b", "user": "bob"},
            "to": {"call_id": "to-b"},
            "duration": 7,
        },
    ]

    assert flatten_record(records[0]) == {
        "from.call_id": "from-a",
        "from.user": "alice",
        "to.call_id": "to-a",
        "duration": 42,
    }
    assert inventory_field_paths(records) == [
        "duration",
        "from.call_id",
        "from.user",
        "to.call_id",
    ]


def test_get_cdr_users_follows_cursor_pagination():
    seen_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        if "cursor=abc" in str(request.url):
            return httpx.Response(
                200,
                json={"result": [{"id": "second"}], "more": False},
            )
        return httpx.Response(
            200,
            json={"result": [{"id": "first"}], "more": True, "cursor": "abc"},
        )

    client = VersatureClient(
        base_url="https://api.example.test/",
        api_version="application/vnd.versature.v1+json",
        access_token="token",
        transport=httpx.MockTransport(handler),
    )

    rows = client.get_cdr_users(start_date="2026-04-01", end_date="2026-04-30")

    assert rows == [{"id": "first"}, {"id": "second"}]
    assert len(seen_requests) == 2
    assert seen_requests[0].url.path == "/cdrs/users/"
    assert "cursor=abc" in str(seen_requests[1].url)


def test_get_json_requires_top_level_result():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"more": False})

    client = VersatureClient(
        base_url="https://api.example.test/",
        api_version="application/vnd.versature.v1+json",
        access_token="token",
        transport=httpx.MockTransport(handler),
    )

    try:
        client.get_cdr_users(start_date="2026-04-01", end_date="2026-04-30")
    except ValueError as exc:
        assert str(exc) == "Expected Versature response to include top-level result"
    else:
        raise AssertionError("Expected missing top-level result to raise ValueError")
