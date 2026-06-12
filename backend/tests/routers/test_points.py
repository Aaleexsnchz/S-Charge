import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.charging_point import ChargingPoint, ChargingPointSource, Connector, Evse
from app.models.tariff import Tariff

NOW = datetime(2026, 6, 1, tzinfo=UTC)


def make_point(**overrides: Any) -> ChargingPoint:
    defaults: dict[str, Any] = {
        "source": ChargingPointSource.REVE_SEED,
        "source_id": str(uuid.uuid4()),
        "name": "Punto de prueba",
        "cpo_name": "CPO Test",
        "address": "Calle Falsa 123",
        "city": "Madrid",
        "country_code": "ESP",
        "latitude": Decimal("40.416800"),
        "longitude": Decimal("-3.703800"),
        "time_zone": "Europe/Madrid",
        "opening_24_7": True,
        "source_last_updated_at": NOW,
    }
    defaults.update(overrides)
    return ChargingPoint(**defaults)


def make_evse(**overrides: Any) -> Evse:
    defaults: dict[str, Any] = {
        "source_id": str(uuid.uuid4()),
        "source_last_updated_at": NOW,
    }
    defaults.update(overrides)
    return Evse(**defaults)


def make_connector(**overrides: Any) -> Connector:
    defaults: dict[str, Any] = {
        "source_id": str(uuid.uuid4()),
        "standard": "IEC_62196_T2",
        "format": "SOCKET",
        "power_type": "AC_3_PHASE",
        "max_voltage": 400,
        "max_amperage": 32,
        "source_last_updated_at": NOW,
    }
    defaults.update(overrides)
    return Connector(**defaults)


def make_tariff(price: str | None, **overrides: Any) -> Tariff:
    defaults: dict[str, Any] = {
        "source_id": str(uuid.uuid4()),
        "currency": "EUR",
        "price_per_kwh": Decimal(price) if price is not None else None,
        "raw_data": {},
        "source_last_updated_at": NOW,
        "last_refreshed_at": NOW,
    }
    defaults.update(overrides)
    return Tariff(**defaults)


async def test_list_points_returns_nested_shape(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    point = make_point()
    evse = make_evse()
    evse.connectors.append(make_connector(tariff=make_tariff("0.4200")))
    point.evses.append(evse)
    db_session.add(point)
    await db_session.commit()

    response = await client.get("/api/points")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    item = body[0]
    assert item["id"] == str(point.id)
    assert item["city"] == "Madrid"
    assert item["latitude"] == 40.4168
    assert item["aggregate_status"] == "unknown"
    connector = item["evses"][0]["connectors"][0]
    assert connector["standard"] == "IEC_62196_T2"
    assert connector["tariff"]["price_per_kwh"] == 0.42
    assert connector["tariff"]["currency"] == "EUR"


async def test_list_points_excludes_archived(client: AsyncClient, db_session: AsyncSession) -> None:
    active = make_point()
    archived = make_point(archived_at=NOW)
    db_session.add_all([active, archived])
    await db_session.commit()

    response = await client.get("/api/points")

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()]
    assert ids == [str(active.id)]


async def test_list_points_bbox_filter(client: AsyncClient, db_session: AsyncSession) -> None:
    madrid = make_point()
    barcelona = make_point(
        city="Barcelona", latitude=Decimal("41.385100"), longitude=Decimal("2.173400")
    )
    db_session.add_all([madrid, barcelona])
    await db_session.commit()

    response = await client.get("/api/points", params={"bbox": "-4.5,39.5,-3.0,41.0"})

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()]
    assert ids == [str(madrid.id)]


async def test_list_points_invalid_bbox_returns_422(client: AsyncClient) -> None:
    response = await client.get("/api/points", params={"bbox": "1,2,3"})
    assert response.status_code == 422

    response = await client.get("/api/points", params={"bbox": "a,b,c,d"})
    assert response.status_code == 422


async def test_list_points_connector_standard_filter(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    type2 = make_point()
    type2_evse = make_evse()
    type2_evse.connectors.append(make_connector())
    type2.evses.append(type2_evse)

    chademo = make_point()
    chademo_evse = make_evse()
    chademo_evse.connectors.append(make_connector(standard="CHADEMO", power_type="DC"))
    chademo.evses.append(chademo_evse)

    db_session.add_all([type2, chademo])
    await db_session.commit()

    response = await client.get("/api/points", params={"connector_standard": "CHADEMO"})

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()]
    assert ids == [str(chademo.id)]


async def test_list_points_max_price_filter(client: AsyncClient, db_session: AsyncSession) -> None:
    cheap = make_point()
    cheap_evse = make_evse()
    cheap_evse.connectors.append(make_connector(tariff=make_tariff("0.3000")))
    cheap.evses.append(cheap_evse)

    pricey = make_point()
    pricey_evse = make_evse()
    pricey_evse.connectors.append(make_connector(tariff=make_tariff("0.5500")))
    pricey.evses.append(pricey_evse)

    unpriced = make_point()
    unpriced_evse = make_evse()
    unpriced_evse.connectors.append(make_connector())
    unpriced.evses.append(unpriced_evse)

    db_session.add_all([cheap, pricey, unpriced])
    await db_session.commit()

    response = await client.get("/api/points", params={"max_price_per_kwh": "0.40"})

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()]
    assert ids == [str(cheap.id)]


async def test_get_point_returns_nested_shape(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    point = make_point(
        opening_24_7=False,
        opening_hours=[{"weekday": 1, "period_begin": "09:00", "period_end": "18:00"}],
    )
    operational = make_evse(is_operational=True)
    operational.connectors.append(make_connector(tariff=make_tariff("0.4200")))
    broken = make_evse(is_operational=False)
    broken.connectors.append(make_connector())
    point.evses.extend([operational, broken])
    db_session.add(point)
    await db_session.commit()

    response = await client.get(f"/api/points/{point.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(point.id)
    assert body["aggregate_status"] == "partial"
    assert body["opening_hours"] == [{"weekday": 1, "period_begin": "09:00", "period_end": "18:00"}]
    assert len(body["evses"]) == 2
    standards = {
        connector["standard"] for evse in body["evses"] for connector in evse["connectors"]
    }
    assert standards == {"IEC_62196_T2"}


async def test_map_returns_feature_collection(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    point = make_point()
    type2_evse = make_evse(is_operational=True)
    type2_evse.connectors.append(
        make_connector(tariff=make_tariff("0.4200"), max_electric_power=22000)
    )
    ccs_evse = make_evse(is_operational=True)
    ccs_evse.connectors.append(
        make_connector(
            standard="IEC_62196_T2_COMBO",
            power_type="DC",
            tariff=make_tariff("0.3000"),
            max_electric_power=150000,
        )
    )
    point.evses.extend([type2_evse, ccs_evse])

    bare = make_point()
    archived = make_point(archived_at=NOW)
    db_session.add_all([point, bare, archived])
    await db_session.commit()

    response = await client.get("/api/points/map")

    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "FeatureCollection"
    features = {f["properties"]["id"]: f for f in body["features"]}
    assert set(features) == {str(point.id), str(bare.id)}

    rich = features[str(point.id)]
    assert rich["geometry"] == {"type": "Point", "coordinates": [-3.7038, 40.4168]}
    assert rich["properties"]["aggregate_status"] == "operational"
    assert rich["properties"]["standards"] == ["IEC_62196_T2", "IEC_62196_T2_COMBO"]
    assert rich["properties"]["max_power_w"] == 150000
    assert rich["properties"]["min_price_per_kwh"] == 0.30

    empty = features[str(bare.id)]
    assert empty["properties"]["aggregate_status"] == "unknown"
    assert empty["properties"]["standards"] == []
    assert empty["properties"]["min_price_per_kwh"] is None


async def test_map_aggregate_status_rollup(client: AsyncClient, db_session: AsyncSession) -> None:
    partial = make_point()
    partial.evses.extend([make_evse(is_operational=True), make_evse(is_operational=False)])
    inoperative = make_point()
    inoperative.evses.append(make_evse(is_operational=False))
    db_session.add_all([partial, inoperative])
    await db_session.commit()

    response = await client.get("/api/points/map")

    statuses = {
        f["properties"]["id"]: f["properties"]["aggregate_status"]
        for f in response.json()["features"]
    }
    assert statuses[str(partial.id)] == "partial"
    assert statuses[str(inoperative.id)] == "inoperative"


async def test_get_point_unknown_returns_reve_error_shape(client: AsyncClient) -> None:
    response = await client.get(f"/api/points/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json() == {
        "status_code": 404,
        "status_message": "Charging point not found",
    }
