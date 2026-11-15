import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.charging_point import Connector, PricingKind
from app.models.vehicle import Vehicle
from app.schemas.simulation import ChargeType, SimulationRequest, SimulationResult
from app.services.tariff_pricing import connector_prices_over

DC_TAPER_KNEE_SOC = Decimal("80")
DC_TAPER_TAIL_FRACTION = Decimal("0.2")


class VehicleNotFound(Exception):
    pass


class ConnectorNotFound(Exception):
    pass


class DCNotSupported(Exception):
    pass


class InvalidConnectorPower(Exception):
    pass


@dataclass(frozen=True)
class ChargeStep:
    """One SoC step: when its energy arrives, measured from the start of the charge."""

    midpoint_minutes: Decimal
    energy_kwh: Decimal


@dataclass(frozen=True)
class ChargePhysics:
    charge_type: ChargeType
    energy_kwh: Decimal
    duration_minutes: Decimal
    peak_power_kw: Decimal
    average_power_kw: Decimal
    steps: tuple[ChargeStep, ...]


def charge_type_for(power_type: str) -> ChargeType:
    """Collapse OCPI's power types (``DC``, ``AC_1_PHASE``, ...) to AC or DC."""
    return "DC" if power_type.upper().startswith("DC") else "AC"


def _power_at_soc(peak_kw: Decimal, charge_type: ChargeType, soc: Decimal) -> Decimal:
    if charge_type == "AC" or soc <= DC_TAPER_KNEE_SOC:
        return peak_kw
    span = Decimal(100) - DC_TAPER_KNEE_SOC
    frac = (soc - DC_TAPER_KNEE_SOC) / span
    return peak_kw * (Decimal(1) - (Decimal(1) - DC_TAPER_TAIL_FRACTION) * frac)


def simulate_charge(
    *,
    battery_kwh: Decimal,
    peak_power_kw: Decimal,
    charge_type: ChargeType,
    soc_from: Decimal,
    soc_to: Decimal,
) -> ChargePhysics:
    """Spec-based charge prediction.

    Power is held at ``peak_power_kw`` (the lesser of vehicle and connector
    rating); DC tapers linearly above ``DC_TAPER_KNEE_SOC`` down to
    ``DC_TAPER_TAIL_FRACTION`` of peak at 100% SoC. Duration integrates the
    SoC window in 1% steps; AC is treated as a flat curve.
    """
    energy_per_pct = battery_kwh / Decimal(100)
    hours = Decimal(0)
    soc = soc_from
    step = Decimal(1)
    steps: list[ChargeStep] = []
    while soc < soc_to:
        nxt = min(soc + step, soc_to)
        midpoint = (soc + nxt) / Decimal(2)
        power = _power_at_soc(peak_power_kw, charge_type, midpoint)
        step_energy = energy_per_pct * (nxt - soc)
        step_hours = step_energy / power
        steps.append(
            ChargeStep(
                midpoint_minutes=(hours + step_hours / Decimal(2)) * Decimal(60),
                energy_kwh=step_energy,
            )
        )
        hours += step_hours
        soc = nxt

    energy_kwh = energy_per_pct * (soc_to - soc_from)
    return ChargePhysics(
        charge_type=charge_type,
        energy_kwh=energy_kwh,
        duration_minutes=hours * Decimal(60),
        peak_power_kw=peak_power_kw,
        average_power_kw=energy_kwh / hours,
        steps=tuple(steps),
    )


async def _load_vehicle(db: AsyncSession, vehicle_id: uuid.UUID) -> Vehicle:
    vehicle = await db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise VehicleNotFound
    return vehicle


async def _load_connector(db: AsyncSession, connector_id: uuid.UUID) -> Connector:
    stmt = select(Connector).where(Connector.id == connector_id)
    connector = (await db.execute(stmt)).scalar_one_or_none()
    if connector is None:
        raise ConnectorNotFound
    return connector


async def _price_window(
    db: AsyncSession,
    connector: Connector,
    physics: ChargePhysics,
    started_at: datetime,
) -> tuple[Decimal | None, Decimal | None]:
    """Cost and effective per-kWh price for the charge, or ``(None, None)``.

    Each SoC step is priced by the band covering the moment its energy arrives,
    so a charge that runs from a day band into a cheaper night one is billed at
    both. The effective price is what the driver would divide by, not a band:
    quoting one band for a charge that crossed two would be a number no meter
    ever reads.

    A connector with no published energy price gets no cost rather than an
    estimate: a plausible number attributed to someone else's charger reads as
    a quoted one.
    """
    if connector.pricing_kind is PricingKind.FREE:
        return Decimal(0), Decimal(0)
    if connector.pricing_kind is not PricingKind.ENERGY:
        return None, None

    # The series is generated a minute at a time, so both ends and every lookup
    # have to sit on the same minute boundary or nothing ever matches.
    window_start = started_at.replace(second=0, microsecond=0)
    ends_at = window_start + timedelta(minutes=float(physics.duration_minutes))
    prices = await connector_prices_over(db, connector.id, window_start, ends_at)
    if not prices:
        return None, None

    cost = Decimal(0)
    for step in physics.steps:
        minute = window_start + timedelta(minutes=int(step.midpoint_minutes))
        price = prices.get(minute)
        # A cost covering part of the session reads as covering all of it, and
        # understating one is the same failure as inventing one. Guards a
        # tariff whose bands leave a hole in the day.
        if price is None:
            return None, None
        cost += step.energy_kwh * price

    return cost, cost / physics.energy_kwh


async def run_simulation(
    db: AsyncSession,
    request: SimulationRequest,
    *,
    at: datetime | None = None,
) -> SimulationResult:
    vehicle = await _load_vehicle(db, request.vehicle_id)
    connector = await _load_connector(db, request.connector_id)

    charge_type = charge_type_for(connector.power_type)
    if charge_type == "DC":
        vehicle_limit = vehicle.max_dc_kw
        if vehicle_limit is None:
            raise DCNotSupported
    else:
        vehicle_limit = vehicle.max_ac_kw

    connector_power_kw = Decimal(connector.max_electric_power or 0) / Decimal(1000)
    if connector_power_kw <= 0:
        raise InvalidConnectorPower
    peak_power_kw = min(vehicle_limit, connector_power_kw)

    physics = simulate_charge(
        battery_kwh=vehicle.battery_kwh,
        peak_power_kw=peak_power_kw,
        charge_type=charge_type,
        soc_from=Decimal(str(request.soc_from)),
        soc_to=Decimal(str(request.soc_to)),
    )

    started_at = at or datetime.now(UTC)
    cost_eur, price_per_kwh = await _price_window(db, connector, physics, started_at)

    return SimulationResult(
        charge_type=charge_type,
        soc_from=request.soc_from,
        soc_to=request.soc_to,
        energy_kwh=float(physics.energy_kwh),
        duration_minutes=float(physics.duration_minutes),
        peak_power_kw=float(physics.peak_power_kw),
        average_power_kw=float(physics.average_power_kw),
        cost_eur=float(cost_eur) if cost_eur is not None else None,
        price_per_kwh=float(price_per_kwh) if price_per_kwh is not None else None,
    )
