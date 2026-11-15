import uuid
from datetime import UTC, datetime, time
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
from app.models.tariff import Tariff, TariffElement
from app.models.vehicle import Vehicle
from app.schemas.simulation import SimulationRequest
from app.services.simulation import (
    DCNotSupported,
    _power_at_soc,
    charge_type_for,
    run_simulation,
    simulate_charge,
)
from sqlalchemy.ext.asyncio import AsyncSession

MADRID = ZoneInfo("Europe/Madrid")
SEED_DT = datetime(2026, 4, 1, tzinfo=UTC)


@pytest.mark.parametrize(
    ("power_type", "expected"),
    [("AC_1_PHASE", "AC"), ("AC_3_PHASE", "AC"), ("DC", "DC"), ("dc", "DC")],
)
def test_charge_type_for(power_type: str, expected: str) -> None:
    assert charge_type_for(power_type) == expected


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
    bands: list[tuple[time, time, str]] | None = None,
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

    tariff = None
    elements = bands if bands is not None else []
    if tariff_price is not None and not elements:
        elements = [(time(0, 0), time(23, 59), str(tariff_price))]
    if elements:
        tariff = Tariff(
            source_id=str(uuid.uuid4()),
            currency="EUR",
            raw_data={},
            source_last_updated_at=SEED_DT,
            last_refreshed_at=SEED_DT,
        )
        db.add(tariff)
        await db.flush()
        for index, (start, end, price) in enumerate(elements):
            db.add(
                TariffElement(
                    tariff_id=tariff.id,
                    element_index=index,
                    component_type="ENERGY",
                    price=Decimal(price),
                    start_time=start,
                    end_time=end,
                )
            )

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
        tariff_id=tariff.id if tariff else None,
        source_last_updated_at=SEED_DT,
    )
    db.add(connector)
    await db.flush()
    return connector


async def test_run_simulation_prices_from_the_bands(db_session: AsyncSession) -> None:
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
        at=datetime(2026, 6, 26, 12, 0, tzinfo=MADRID),
    )

    assert result.charge_type == "DC"
    assert result.peak_power_kw == pytest.approx(50.0)
    assert result.energy_kwh == pytest.approx(30.0)
    assert result.price_per_kwh == pytest.approx(0.45)
    assert result.cost_eur == pytest.approx(30.0 * 0.45)


async def test_charge_crossing_a_boundary_is_priced_by_both_bands(
    db_session: AsyncSession,
) -> None:
    """An 11 kW charge for 30 kWh runs nearly three hours, so it cannot be one band."""
    vehicle = await _make_vehicle(db_session)
    connector = await _make_connector(
        db_session,
        power_type="AC",
        max_electric_power=22000,
        tariff_price=Decimal("0.20"),
        bands=[
            (time(0, 0), time(6, 59), "0.20"),
            (time(7, 0), time(23, 59), "0.40"),
        ],
    )

    result = await run_simulation(
        db_session,
        SimulationRequest(
            vehicle_id=vehicle.id, connector_id=connector.id, soc_from=20, soc_to=80
        ),
        at=datetime(2026, 6, 26, 6, 30, tzinfo=MADRID),
    )

    assert result.price_per_kwh is not None
    assert 0.20 < result.price_per_kwh < 0.40
    assert result.cost_eur == pytest.approx(result.energy_kwh * result.price_per_kwh)


async def test_charge_wholly_inside_one_band_pays_that_band(
    db_session: AsyncSession,
) -> None:
    vehicle = await _make_vehicle(db_session)
    connector = await _make_connector(
        db_session,
        power_type="AC",
        max_electric_power=22000,
        tariff_price=Decimal("0.20"),
        bands=[
            (time(0, 0), time(6, 59), "0.20"),
            (time(7, 0), time(23, 59), "0.40"),
        ],
    )

    result = await run_simulation(
        db_session,
        SimulationRequest(
            vehicle_id=vehicle.id, connector_id=connector.id, soc_from=20, soc_to=80
        ),
        at=datetime(2026, 6, 26, 9, 0, tzinfo=MADRID),
    )

    assert result.price_per_kwh == pytest.approx(0.40)


async def test_unpriced_connector_reports_time_and_energy_but_no_cost(
    db_session: AsyncSession,
) -> None:
    """No estimate stands in for a price the operator never published."""
    vehicle = await _make_vehicle(db_session)
    connector = await _make_connector(
        db_session, power_type="DC", max_electric_power=150000, tariff_price=None
    )

    result = await run_simulation(
        db_session,
        SimulationRequest(
            vehicle_id=vehicle.id, connector_id=connector.id, soc_from=20, soc_to=80
        ),
        at=datetime(2026, 6, 26, 12, 0, tzinfo=MADRID),
    )

    assert result.cost_eur is None
    assert result.price_per_kwh is None
    assert result.energy_kwh == pytest.approx(30.0)
    assert result.duration_minutes > 0


async def test_free_connector_costs_nothing(db_session: AsyncSession) -> None:
    vehicle = await _make_vehicle(db_session)
    connector = await _make_connector(
        db_session, power_type="AC", max_electric_power=22000, tariff_price=None
    )
    connector.pricing_kind = PricingKind.FREE
    await db_session.flush()

    result = await run_simulation(
        db_session,
        SimulationRequest(
            vehicle_id=vehicle.id, connector_id=connector.id, soc_from=20, soc_to=80
        ),
        at=datetime(2026, 6, 26, 12, 0, tzinfo=MADRID),
    )

    assert result.price_per_kwh == pytest.approx(0.0)
    assert result.cost_eur == pytest.approx(0.0)


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


async def test_charge_crossing_an_unpriced_gap_reports_no_cost(
    db_session: AsyncSession,
) -> None:
    """A tariff leaving an hour unpriced yields no cost, not a cost for the rest."""
    vehicle = await _make_vehicle(db_session)
    connector = await _make_connector(
        db_session,
        power_type="AC",
        max_electric_power=22000,
        tariff_price=Decimal("0.20"),
        bands=[
            (time(0, 0), time(6, 59), "0.20"),
            (time(8, 0), time(23, 59), "0.40"),
        ],
    )

    result = await run_simulation(
        db_session,
        SimulationRequest(
            vehicle_id=vehicle.id, connector_id=connector.id, soc_from=20, soc_to=80
        ),
        at=datetime(2026, 6, 26, 6, 30, tzinfo=MADRID),
    )

    assert result.cost_eur is None
    assert result.price_per_kwh is None
    assert result.energy_kwh == pytest.approx(30.0)
