import base64

import httpx
import pytest
from app.integrations.acn import AcnClient
from pytest_httpx import HTTPXMock

BASE_URL = "https://acn.test/api/v1"
TOKEN = "acn-test-token"


async def test_sends_basic_auth_with_token_as_username(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}/sessions/caltech?page=1&max_results=100&sort=connectionTime",
        json={"_items": []},
    )

    async with AcnClient(token=TOKEN, base_url=BASE_URL) as client:
        items, total_pages = await client.get_sessions("caltech")

    assert items == []
    assert total_pages is None
    request = httpx_mock.get_requests()[0]
    expected = base64.b64encode(f"{TOKEN}:".encode()).decode()
    assert request.headers["Authorization"] == f"Basic {expected}"


async def test_computes_total_pages_from_meta(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}/sessions/jpl?page=1&max_results=100&sort=connectionTime",
        json={
            "_items": [{"_id": "x"}],
            "_meta": {"page": 1, "max_results": 100, "total": 250},
        },
    )

    async with AcnClient(token=TOKEN, base_url=BASE_URL) as client:
        items, total_pages = await client.get_sessions("jpl", per_page=100)

    assert len(items) == 1
    assert total_pages == 3


async def test_raises_on_http_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}/sessions/caltech?page=1&max_results=100&sort=connectionTime",
        status_code=401,
    )

    async with AcnClient(token=TOKEN, base_url=BASE_URL) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_sessions("caltech")


def test_requires_token() -> None:
    with pytest.raises(RuntimeError):
        AcnClient(token="", base_url=BASE_URL)
