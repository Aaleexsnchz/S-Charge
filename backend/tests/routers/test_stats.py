import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.acn import AcnSession


def make_session(**overrides: Any) -> AcnSession:
    defaults: dict[str, Any] = {
        "source_id": str(uuid.uuid4()),
        "site": "caltech",
        "connection_time": datetime(2018, 4, 25, 18, 8, tzinfo=UTC),
        "disconnect_time": datetime(2018, 4, 25, 20, 8, tzinfo=UTC),
        "kwh_delivered": Decimal("10.0"),
        "time_zone": "America/Los_Angeles",
        "raw_data": {},
    }
    defaults.update(overrides)
    return AcnSession(**defaults)


async def test_overview_totals_and_sites(client: AsyncClient, db_session: AsyncSession) -> None:
    db_session.add_all(
        [
            make_session(kwh_delivered=Decimal("10.0")),
            make_session(kwh_delivered=Decimal("20.0")),
            make_session(site="jpl", kwh_delivered=Decimal("5.0")),
        ]
    )
    await db_session.commit()

    response = await client.get("/api/stats/overview")

    assert response.status_code == 200
    body = response.json()
    assert body["sessions"] == 3
    assert body["total_kwh"] == 35.0
    assert body["avg_duration_min"] == 120.0
    assert [site["site"] for site in body["sites"]] == ["caltech", "jpl"]
    assert body["sites"][0]["sessions"] == 2
    assert body["sites"][1]["total_kwh"] == 5.0


async def test_overview_empty_db(client: AsyncClient) -> None:
    response = await client.get("/api/stats/overview")

    assert response.status_code == 200
    body = response.json()
    assert body["sessions"] == 0
    assert body["total_kwh"] == 0.0
    assert body["avg_kwh"] is None
    assert body["sites"] == []


async def test_energy_monthly_groups_local_months(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    db_session.add_all(
        [
            # 2018-05-01 02:00 UTC is still 2018-04-30 in Los Angeles
            make_session(
                connection_time=datetime(2018, 5, 1, 2, 0, tzinfo=UTC),
                kwh_delivered=Decimal("7.5"),
            ),
            make_session(
                connection_time=datetime(2018, 5, 10, 12, 0, tzinfo=UTC),
                kwh_delivered=Decimal("4.5"),
            ),
            make_session(site="jpl", kwh_delivered=Decimal("3.0")),
        ]
    )
    await db_session.commit()

    response = await client.get("/api/stats/energy-monthly")
    assert response.status_code == 200
    assert response.json() == [
        {"month": "2018-04", "sessions": 2, "kwh": 10.5},
        {"month": "2018-05", "sessions": 1, "kwh": 4.5},
    ]

    response = await client.get("/api/stats/energy-monthly", params={"site": "jpl"})
    assert response.status_code == 200
    assert response.json() == [{"month": "2018-04", "sessions": 1, "kwh": 3.0}]


async def test_arrivals_heatmap_uses_local_weekday_and_hour(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    # Wed 2018-04-25 18:08 UTC = Wed 11:08 in Los Angeles → weekday 2, hour 11
    db_session.add_all([make_session(), make_session()])
    await db_session.commit()

    response = await client.get("/api/stats/arrivals-heatmap")

    assert response.status_code == 200
    assert response.json() == [{"weekday": 2, "hour": 11, "sessions": 2}]
