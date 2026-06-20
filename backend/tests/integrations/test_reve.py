import logging

import httpx
import pytest
from app.integrations.reve import ReveClient
from pytest_httpx import HTTPXMock

BASE_URL = "https://reve.test/api/v1"
API_KEY = "secret-key-do-not-leak"


async def test_get_returns_parsed_json(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}/cpos",
        json={"data": [{"party_id": "ES*ABC"}], "page": 1},
    )

    async with ReveClient(api_key=API_KEY, base_url=BASE_URL) as client:
        result = await client.get("/cpos")

    assert result == {"data": [{"party_id": "ES*ABC"}], "page": 1}


async def test_get_sends_api_key_header(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=f"{BASE_URL}/cpos", json={})

    async with ReveClient(api_key=API_KEY, base_url=BASE_URL) as client:
        await client.get("/cpos")

    sent = httpx_mock.get_requests()[0]
    assert sent.headers["x-api-key"] == API_KEY


async def test_get_retries_once_on_429(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}/cpos", status_code=429, headers={"Retry-After": "0"}
    )
    httpx_mock.add_response(url=f"{BASE_URL}/cpos", json={"data": []})

    async with ReveClient(api_key=API_KEY, base_url=BASE_URL) as client:
        result = await client.get("/cpos")

    assert result == {"data": []}
    assert len(httpx_mock.get_requests()) == 2


async def test_get_raises_after_second_429(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}/cpos", status_code=429, headers={"Retry-After": "0"}
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}/cpos", status_code=429, headers={"Retry-After": "0"}
    )

    async with ReveClient(api_key=API_KEY, base_url=BASE_URL) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await client.get("/cpos")


async def test_get_raises_on_other_4xx(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=f"{BASE_URL}/cpos", status_code=404)

    async with ReveClient(api_key=API_KEY, base_url=BASE_URL) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await client.get("/cpos")


async def test_api_key_never_appears_in_audit_log(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}/cpos", status_code=429, headers={"Retry-After": "0"}
    )
    httpx_mock.add_response(url=f"{BASE_URL}/cpos", status_code=500)

    captured: list[logging.LogRecord] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured.append(record)

    handler = _Capture()
    audit_logger = logging.getLogger("audit")
    audit_logger.addHandler(handler)
    try:
        async with ReveClient(api_key=API_KEY, base_url=BASE_URL) as client:
            with pytest.raises(httpx.HTTPStatusError):
                await client.get("/cpos")
    finally:
        audit_logger.removeHandler(handler)

    rendered = "\n".join(r.getMessage() + str(r.__dict__) for r in captured)
    assert API_KEY not in rendered
    assert "reve_rate_limited_retry" in rendered
    assert "reve_request_failed" in rendered


async def test_get_paginated_yields_items_across_pages(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}/cpos?page=1&limit=2",
        json=[{"id": "a"}, {"id": "b"}],
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}/cpos?page=2&limit=2",
        json=[{"id": "c"}],
    )

    async with ReveClient(api_key=API_KEY, base_url=BASE_URL) as client:
        items = [item async for item in client.get_paginated("/cpos", page_size=2)]

    assert items == [{"id": "a"}, {"id": "b"}, {"id": "c"}]


async def test_get_paginated_stops_on_empty_first_page(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=f"{BASE_URL}/cpos?page=1&limit=100", json=[])

    async with ReveClient(api_key=API_KEY, base_url=BASE_URL) as client:
        items = [item async for item in client.get_paginated("/cpos")]

    assert items == []
    assert len(httpx_mock.get_requests()) == 1


async def test_get_paginated_rejects_oversized_page_size() -> None:
    async with ReveClient(api_key=API_KEY, base_url=BASE_URL) as client:
        with pytest.raises(ValueError, match="REVE caps limit"):
            [_ async for _ in client.get_paginated("/cpos", page_size=200)]


async def test_missing_api_key_raises() -> None:
    with pytest.raises(RuntimeError, match="REVE_API_KEY"):
        ReveClient(api_key="", base_url=BASE_URL)
