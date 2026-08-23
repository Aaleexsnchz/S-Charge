import uuid
from datetime import UTC, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from app.models.charging_point import (
    ChargingPoint,
    ChargingPointSource,
    Connector,
    Evse,
    PricingKind,
)
from app.models.price import ElectricityPrice
from app.models.vehicle import Vehicle
from app.schemas.simulation import SimulationRequest
from app.services.pricing import MARGIN_DC_EUR_PER_KWH
from app.services.simulation import (
    DCNotSupported,
    _power_at_soc,
    run_simulation,
    simulate_charge,
)
from sqlalchemy.ext.asyncio import AsyncSession

MADRID = ZoneInfo("Europe/Madrid")
SEED_DT = datetime(2026, 4, 1, tzinfo=UTC)


def test_simulate_charge_ac_is_flat() -> None:
    physics = simulate_charge(
        battery_kwh=Decimal("60"),
        peak_power_kw=Decimal("11"),
        charge_type="AC",
        soc_from=Decimal("20"),
        soc_to=Decimal("80"),
    )
    assert physics.charge_type == "AC"
    assert physics.energy_kwh == Decimal("36.0")
    assert physics.peak_power_kw == Decimal("11")
    assert float(physics.average_power_kw) == pytest.approx(11.0)
    assert float(physics.duration_minutes) == pytest.approx(36 / 11 * 60)


def test_simulate_charge_dc_below_knee_is_flat() -> None:
    physics = simulate_charge(
        battery_kwh=Decimal("60"),
        peak_power_kw=Decimal("100"),
        charge_type="DC",
        soc_from=Decimal("10"),
        soc_to=Decimal("50"),
    )
    assert float(physics.average_power_kw) == pytest.approx(100.0)
    assert float(physics.duration_minutes) == pytest.approx(24 / 100 * 60)


def test_simulate_charge_dc_tapers_above_knee() -> None:
    physics = simulate_charge(
        battery_kwh=Decimal("80"),
        peak_power_kw=Decimal("150"),
        charge_type="DC",
        soc_from=Decimal("20"),
        soc_to=Decimal("100"),
    )
    assert 30.0 < float(physics.average_power_kw) < 150.0


def test_power_at_soc_dc_is_monotonic_above_knee() -> None:
    peak = Decimal("150")
    assert _power_at_soc(peak, "DC", Decimal("70")) == peak
    assert _power_at_soc(peak, "DC", Decimal("80")) == peak
    assert _power_at_soc(peak, "DC", Decimal("90")) < peak
    assert _power_at_soc(peak, "DC", Decimal("100")) == peak * Decimal("0.2")


async def _make_vehicle(db: AsyncSession, **overrides: object) -> Vehicle:
    fields: dict[str, object] = {
        "make": "Test",
        "model": str(uuid.uuid4()),
        "battery_kwh": Decimal("50"),
        "max_ac_kw": Decimal("11"),
        "max_dc_kw": Decimal("100"),
        **overrides,
    }
    vehicle = Vehicle(**fields)
    db.add(vehicle)
    await db.flush()
    return vehicle


async def _make_connector(
    db: AsyncSession,
    *,
    power_type: str,
    max_electric_power: int,
    tariff_price: Decimal | None,
) -> Connector:
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
    db.add(cp)
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
        power_type=power_type,
        max_electric_power=max_electric_power,
        max_voltage=400,
        max_amperage=125,
        pricing_kind=(
            PricingKind.ENERGY if tariff_price is not None else PricingKind.UNKNOWN
        ),
        current_price_per_kwh=tariff_price,
        source_last_updated_at=SEED_DT,
    )
    db.add(connector)
    await db.flush()
    return connector


async def test_run_simulation_uses_real_tariff(db_session: AsyncSession) -> None:
    vehicle = await _make_vehicle(db_session)
    connector = await _make_connector(
        db_session,
        power_type="DC",
        max_electric_power=50000,
        tariff_price=Decimal("0.45"),
    )

    result = await run_simulation(
        db_session,
        SimulationRequest(
            vehicle_id=vehicle.id, connector_id=connector.id, soc_from=20, soc_to=80
        ),
    )

    assert result.charge_type == "DC"
    assert result.peak_power_kw == pytest.approx(50.0)
    assert result.energy_kwh == pytest.approx(30.0)
    assert result.price_source == "reve_tariff"
    assert result.price_per_kwh == pytest.approx(0.45)
    assert result.cost_eur == pytest.approx(30.0 * 0.45)


async def test_run_simulation_falls_back_to_pvpc(db_session: AsyncSession) -> None:
    vehicle = await _make_vehicle(db_session)
    connector = await _make_connector(
        db_session, power_type="DC", max_electric_power=150000, tariff_price=None
    )
    slot = datetime(2026, 6, 26, 12, 0, tzinfo=MADRID)
    db_session.add(ElectricityPrice(hour_start=slot, price_per_kwh=Decimal("0.10000")))
    await db_session.flush()

    result = await run_simulation(
        db_session,
        SimulationRequest(
            vehicle_id=vehicle.id, connector_id=connector.id, soc_from=20, soc_to=80
        ),
        at=slot,
    )

    expected_price = float(Decimal("0.10000") + MARGIN_DC_EUR_PER_KWH)
    assert result.price_source == "pvpc_plus_margin"
    assert result.price_per_kwh == pytest.approx(expected_price)
    assert result.margin_per_kwh == pytest.approx(float(MARGIN_DC_EUR_PER_KWH))


async def test_run_simulation_rejects_dc_without_capability(
    db_session: AsyncSession,
) -> None:
    vehicle = await _make_vehicle(db_session, max_dc_kw=None)
    connector = await _make_connector(
        db_session,
        power_type="DC",
        max_electric_power=50000,
        tariff_price=Decimal("0.3"),
    )

    with pytest.raises(DCNotSupported):
        await run_simulation(
            db_session,
            SimulationRequest(
                vehicle_id=vehicle.id, connector_id=connector.id, soc_from=20, soc_to=80
            ),
        )
