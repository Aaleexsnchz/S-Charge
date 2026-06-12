from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from pytest_httpx import HTTPXMock
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.etl.acn import import_acn_sessions
from app.integrations.acn import AcnClient
from app.models.acn import AcnSession

BASE_URL = "https://acn.test/api/v1"
TOKEN = "acn-test-token"

PER_PAGE = 250


def _session(source_id: str = "5bc9aabbccdd", **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "_id": source_id,
        "sessionID": f"2_39_78_362_{source_id}",
        "stationID": "2-39-78-362",
        "spaceID": "CA-303",
        "clusterID": "0039",
        "siteID": "0002",
        "connectionTime": "Wed, 25 Apr 2018 11:08:04 GMT",
        "disconnectTime": "Wed, 25 Apr 2018 14:42:26 GMT",
        "doneChargingTime": "Wed, 25 Apr 2018 13:21:10 GMT",
        "kWhDelivered": 9.825,
        "timezone": "America/Los_Angeles",
        "userID": "user-42",
        "userInputs": [
            {
                "kWhRequested": 20.0,
                "minutesAvailable": 120,
                "requestedDeparture": "Wed, 25 Apr 2018 13:08:04 GMT",
                "modifiedAt": "Wed, 25 Apr 2018 11:08:10 GMT",
            },
            {
                "kWhRequested": 11.5,
                "minutesAvailable": 210,
                "requestedDeparture": "Wed, 25 Apr 2018 14:38:04 GMT",
                "modifiedAt": "Wed, 25 Apr 2018 11:09:00 GMT",
            },
        ],
    }
    payload.update(overrides)
    return payload


def _page_url(page: int) -> str:
    return f"{BASE_URL}/sessions/caltech?page={page}&max_results={PER_PAGE}&sort=connectionTime"


def _meta(total: int, page: int) -> dict[str, Any]:
    return {"page": page, "max_results": PER_PAGE, "total": total}


@pytest.fixture
def acn_client() -> AcnClient:
    return AcnClient(token=TOKEN, base_url=BASE_URL)


async def test_import_parses_fields_and_latest_user_input(
    acn_client: AcnClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_page_url(1),
        json={"_items": [_session()], "_meta": _meta(total=1, page=1)},
    )

    async with acn_client as client:
        rows, last_page, exhausted = await import_acn_sessions(client, db_session, "caltech")

    assert (rows, last_page, exhausted) == (1, 1, True)
    session = (await db_session.execute(select(AcnSession))).scalar_one()
    assert session.site == "caltech"
    assert session.connection_time == datetime(2018, 4, 25, 11, 8, 4, tzinfo=UTC)
    assert session.kwh_delivered == Decimal("9.8250")
    assert session.time_zone == "America/Los_Angeles"
    assert session.kwh_requested == Decimal("11.5000")
    assert session.minutes_available == 210
    assert session.requested_departure == datetime(2018, 4, 25, 14, 38, 4, tzinfo=UTC)
    assert session.raw_data["sessionID"] == session.session_id


async def test_import_is_idempotent(
    acn_client: AcnClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_page_url(1),
        json={"_items": [_session()], "_meta": _meta(total=1, page=1)},
    )
    httpx_mock.add_response(
        url=_page_url(1),
        json={
            "_items": [_session(kWhDelivered=12.0)],
            "_meta": _meta(total=1, page=1),
        },
    )

    async with acn_client as client:
        await import_acn_sessions(client, db_session, "caltech")
        await import_acn_sessions(client, db_session, "caltech")

    count = (await db_session.execute(select(func.count()).select_from(AcnSession))).scalar_one()
    assert count == 1
    session = (await db_session.execute(select(AcnSession))).scalar_one()
    assert session.kwh_delivered == Decimal("12.0000")


async def test_import_paginates_until_meta_total(
    acn_client: AcnClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    page_1 = [_session(f"id-{i}") for i in range(PER_PAGE)]
    page_2 = [_session("id-last")]
    httpx_mock.add_response(
        url=_page_url(1),
        json={"_items": page_1, "_meta": _meta(total=PER_PAGE + 1, page=1)},
    )
    httpx_mock.add_response(
        url=_page_url(2),
        json={"_items": page_2, "_meta": _meta(total=PER_PAGE + 1, page=2)},
    )

    async with acn_client as client:
        rows, last_page, exhausted = await import_acn_sessions(client, db_session, "caltech")

    assert (rows, last_page, exhausted) == (PER_PAGE + 1, 2, True)


async def test_import_respects_max_pages(
    acn_client: AcnClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    page_1 = [_session(f"id-{i}") for i in range(PER_PAGE)]
    httpx_mock.add_response(
        url=_page_url(1),
        json={"_items": page_1, "_meta": _meta(total=PER_PAGE * 3, page=1)},
    )

    async with acn_client as client:
        rows, last_page, exhausted = await import_acn_sessions(
            client, db_session, "caltech", max_pages=1
        )

    assert (rows, last_page, exhausted) == (PER_PAGE, 1, False)


async def test_import_handles_missing_optional_fields(
    acn_client: AcnClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    bare = {
        "_id": "bare-1",
        "connectionTime": "Mon, 01 Jan 2024 08:00:00 GMT",
        "userInputs": None,
    }
    httpx_mock.add_response(
        url=_page_url(1),
        json={"_items": [bare], "_meta": _meta(total=1, page=1)},
    )

    async with acn_client as client:
        rows, _, _ = await import_acn_sessions(client, db_session, "caltech")

    assert rows == 1
    session = (await db_session.execute(select(AcnSession))).scalar_one()
    assert session.disconnect_time is None
    assert session.kwh_delivered is None
    assert session.kwh_requested is None
