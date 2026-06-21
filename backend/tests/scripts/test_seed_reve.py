from datetime import UTC, datetime
from typing import Any

import pytest
from app.etl.cursor import read_cursor, record_progress
from app.integrations.reve import ReveClient
from pytest_httpx import HTTPXMock
from scripts.seed_reve import _run_tick
from sqlalchemy.ext.asyncio import AsyncSession

BASE_URL = "https://reve.test/api/v1"
API_KEY = "secret-key"


def _cpo(idx: int) -> dict[str, Any]:
    return {
        "id": f"cpo-{idx}",
        "cif": f"B{idx:08d}",
        "party_id": f"ES*P{idx:03d}",
        "name": f"Operator {idx}",
        "address": "Calle Mayor 1",
        "country": "ES",
        "city": "Madrid",
        "city_code": "28079",
        "postal_code": "28001",
        "last_updated": "2026-04-01T00:00:00Z",
    }


@pytest.fixture
def reve_client() -> ReveClient:
    return ReveClient(api_key=API_KEY, base_url=BASE_URL)


async def test_run_tick_advances_cursor_when_more_pages_remain(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    full_page = [_cpo(i) for i in range(1, 101)]
    httpx_mock.add_response(url=f"{BASE_URL}/cpos?page=1&limit=100", json=full_page)

    async with reve_client as client:
        exit_code = await _run_tick(db_session, client, budget=1)

    assert exit_code == 0
    cursor = await read_cursor(db_session, "/cpos")
    assert cursor.next_page == 2
    assert cursor.completed_at is None
    assert cursor.last_attempted_at is not None
    assert cursor.last_error is None


async def test_run_tick_marks_completed_on_short_page(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=f"{BASE_URL}/cpos?page=1&limit=100", json=[_cpo(1)])

    async with reve_client as client:
        exit_code = await _run_tick(db_session, client, budget=1)

    assert exit_code == 0
    cursor = await read_cursor(db_session, "/cpos")
    assert cursor.completed_at is not None


async def test_run_tick_walks_endpoints_in_priority_order(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    # /cpos: 1 short page (completes immediately, uses 1 call)
    httpx_mock.add_response(url=f"{BASE_URL}/cpos?page=1&limit=100", json=[_cpo(1)])
    # /locations: 1 short page (completes, uses 1 call)
    httpx_mock.add_response(url=f"{BASE_URL}/locations?page=1&limit=100", json=[])

    async with reve_client as client:
        exit_code = await _run_tick(db_session, client, budget=2)

    assert exit_code == 0
    cpos_cursor = await read_cursor(db_session, "/cpos")
    locs_cursor = await read_cursor(db_session, "/locations")
    assert cpos_cursor.completed_at is not None
    assert locs_cursor.completed_at is not None


async def test_run_tick_skips_endpoints_already_completed(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    await record_progress(
        db_session,
        "/cpos",
        next_page=99,
        exhausted=True,
        attempted_at=datetime(2026, 5, 1, tzinfo=UTC),
    )
    httpx_mock.add_response(url=f"{BASE_URL}/locations?page=1&limit=100", json=[])

    async with reve_client as client:
        exit_code = await _run_tick(db_session, client, budget=1)

    assert exit_code == 0
    # /cpos should not have been hit
    requested_urls = [str(r.url) for r in httpx_mock.get_requests()]
    assert all("/cpos" not in u for u in requested_urls)


async def test_run_tick_records_error_on_runtime_error(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=f"{BASE_URL}/cpos?page=1&limit=100", status_code=500)

    async with reve_client as client:
        exit_code = await _run_tick(db_session, client, budget=1)

    assert exit_code == 1
    cursor = await read_cursor(db_session, "/cpos")
    assert cursor.next_page == 1
    assert cursor.last_error is not None
    assert "500" in cursor.last_error or "HTTPStatusError" in cursor.last_error


async def test_run_tick_handles_rate_limit_cleanly(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}/cpos?page=1&limit=100",
        status_code=429,
        headers={"Retry-After": "0"},
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}/cpos?page=1&limit=100",
        status_code=429,
        headers={"Retry-After": "0"},
    )

    async with reve_client as client:
        exit_code = await _run_tick(db_session, client, budget=1)

    assert exit_code == 0
    cursor = await read_cursor(db_session, "/cpos")
    assert cursor.next_page == 1
    assert cursor.last_error is None
