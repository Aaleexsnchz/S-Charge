import uuid
from datetime import UTC, datetime
from decimal import Decimal

from app.models.charging_point import (
    ChargingPoint,
    ChargingPointSource,
    Connector,
    Evse,
    PricingKind,
)
from app.models.vehicle import Vehicle
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

SEED_DT = datetime(2026, 4, 1, tzinfo=UTC)


async def _seed_chain(db: AsyncSession) -> tuple[uuid.UUID, uuid.UUID]:
    vehicle = Vehicle(
        make="Test",
        model=str(uuid.uuid4()),
        battery_kwh=Decimal("60"),
        max_ac_kw=Decimal("11"),
        max_dc_kw=Decimal("150"),
    )
    cp = ChargingPoint(
        source=ChargingPointSource.REVE_SEED,
        source_id=str(uuid.uuid4()),
        address="Calle Mayor 1",
        city="Madrid",
        country_code="ES",
        latitude=Decimal("40.4"),
        longitude=Decimal("-3.7"),
        time_zone="Europe/Madrid",
        opening_24_7=True,
        source_last_updated_at=SEED_DT,
    )
    db.add_all([vehicle, cp])
    await db.flush()
    evse = Evse(
        charging_point_id=cp.id,
        source_id=str(uuid.uuid4()),
        source_last_updated_at=SEED_DT,
    )
    db.add(evse)
    await db.flush()
    connector = Connector(
        evse_id=evse.id,
        source_id=str(uuid.uuid4()),
        standard="IEC_62196_T2",
        format="SOCKET",
        power_type="DC",
        max_electric_power=50000,
        max_voltage=400,
        max_amperage=125,
        pricing_kind=PricingKind.ENERGY,
        current_price_per_kwh=Decimal("0.50"),
        source_last_updated_at=SEED_DT,
    )
    db.add(connector)
    await db.flush()
    return vehicle.id, connector.id


async def test_simulate_returns_prediction(
    auth_client: AsyncClient, db_session: AsyncSession
) -> None:
    vehicle_id, connector_id = await _seed_chain(db_session)

    response = await auth_client.post(
        "/api/simulate",
        json={
            "vehicle_id": str(vehicle_id),
            "connector_id": str(connector_id),
            "soc_from": 20,
            "soc_to": 80,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["charge_type"] == "DC"
    assert body["peak_power_kw"] == 50.0
    assert body["energy_kwh"] == 36.0
    assert body["cost_eur"] == 18.0
    assert body["price_source"] == "reve_tariff"


async def test_simulate_unknown_vehicle_returns_404(
    auth_client: AsyncClient, db_session: AsyncSession
) -> None:
    _, connector_id = await _seed_chain(db_session)

    response = await auth_client.post(
        "/api/simulate",
        json={
            "vehicle_id": str(uuid.uuid4()),
            "connector_id": str(connector_id),
        },
    )

    assert response.status_code == 404


async def test_simulate_rejects_inverted_soc(
    auth_client: AsyncClient, db_session: AsyncSession
) -> None:
    vehicle_id, connector_id = await _seed_chain(db_session)

    response = await auth_client.post(
        "/api/simulate",
        json={
            "vehicle_id": str(vehicle_id),
            "connector_id": str(connector_id),
            "soc_from": 80,
            "soc_to": 20,
        },
    )

    assert response.status_code == 422
