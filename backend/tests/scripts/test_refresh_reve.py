from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from app.etl.cursor import read_cursor
from app.integrations.reve import ReveClient
from app.models.etl import ReveEtlCursor
from pytest_httpx import HTTPXMock
from scripts.refresh_reve import LOOKBACK, _run_tick
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

BASE_URL = "https://reve.test/api/v1"
API_KEY = "secret-key"


@pytest.fixture
def reve_client() -> ReveClient:
    return ReveClient(api_key=API_KEY, base_url=BASE_URL, max_retries=0)


async def _seed_tariff_cursor(db: AsyncSession, watermark: datetime) -> None:
    await db.execute(update(ReveEtlCursor).values(completed_at=watermark))
    await db.execute(
        update(ReveEtlCursor)
        .where(ReveEtlCursor.endpoint == "/connectors/tariffs")
        .values(refresh_watermark=watermark, refresh_cycle_end=None, next_page=1)
    )
    await db.commit()


def _tariff_row() -> dict[str, Any]:
    return {"tariffs": None}


async def test_stale_watermark_504_jumps_to_recent(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    watermark = datetime.now(UTC) - timedelta(hours=100)
    await _seed_tariff_cursor(db_session, watermark)
    httpx_mock.add_response(status_code=504)

    async with reve_client as client:
        exit_code = await _run_tick(db_session, client, budget=5)

    assert exit_code == 0
    cursor = await read_cursor(db_session, "/connectors/tariffs")
    expected = datetime.now(UTC) - LOOKBACK
    assert cursor.refresh_watermark is not None
    assert abs((cursor.refresh_watermark - expected).total_seconds()) < 120
    assert cursor.last_error is not None


async def test_recent_watermark_504_is_left_for_retry(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    watermark = datetime.now(UTC) - timedelta(minutes=30)
    await _seed_tariff_cursor(db_session, watermark)
    httpx_mock.add_response(status_code=504)

    async with reve_client as client:
        exit_code = await _run_tick(db_session, client, budget=5)

    assert exit_code == 0
    cursor = await read_cursor(db_session, "/connectors/tariffs")
    assert cursor.refresh_watermark == watermark
    assert cursor.last_error is not None


async def test_drain_advances_watermark_to_now(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    watermark = datetime.now(UTC) - timedelta(minutes=90)
    await _seed_tariff_cursor(db_session, watermark)
    httpx_mock.add_response(json=[])

    async with reve_client as client:
        exit_code = await _run_tick(db_session, client, budget=5)

    assert exit_code == 0
    cursor = await read_cursor(db_session, "/connectors/tariffs")
    assert cursor.refresh_cycle_end is None
    assert cursor.next_page == 1
    assert cursor.refresh_watermark is not None
    assert cursor.refresh_watermark >= datetime.now(UTC) - timedelta(minutes=2)


async def test_budget_exhausted_mid_pagination_resumes(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    watermark = datetime.now(UTC) - timedelta(minutes=90)
    await _seed_tariff_cursor(db_session, watermark)
    httpx_mock.add_response(json=[_tariff_row() for _ in range(100)])

    async with reve_client as client:
        exit_code = await _run_tick(db_session, client, budget=1)

    assert exit_code == 0
    cursor = await read_cursor(db_session, "/connectors/tariffs")
    assert cursor.next_page == 2
    assert cursor.refresh_cycle_end is not None
    assert cursor.refresh_watermark == watermark


async def test_rate_limit_stops_without_change(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    watermark = datetime.now(UTC) - timedelta(hours=100)
    await _seed_tariff_cursor(db_session, watermark)
    httpx_mock.add_response(status_code=429, headers={"Retry-After": "0"})

    async with reve_client as client:
        exit_code = await _run_tick(db_session, client, budget=5)

    assert exit_code == 0
    cursor = await read_cursor(db_session, "/connectors/tariffs")
    assert cursor.refresh_watermark == watermark


async def test_unexpected_error_surfaces_exit_1(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    watermark = datetime.now(UTC) - timedelta(minutes=90)
    await _seed_tariff_cursor(db_session, watermark)
    httpx_mock.add_response(status_code=500)

    async with reve_client as client:
        exit_code = await _run_tick(db_session, client, budget=5)

    assert exit_code == 1
    cursor = await read_cursor(db_session, "/connectors/tariffs")
    assert cursor.refresh_watermark == watermark
    assert cursor.last_error is not None
