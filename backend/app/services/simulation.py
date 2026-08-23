import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.charging_point import Connector
from app.models.vehicle import Vehicle
from app.schemas.simulation import ChargeType, SimulationRequest, SimulationResult
from app.services.pricing import estimate_price

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
class ChargePhysics:
    charge_type: ChargeType
    energy_kwh: Decimal
    duration_minutes: Decimal
    peak_power_kw: Decimal
    average_power_kw: Decimal


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
    while soc < soc_to:
        nxt = min(soc + step, soc_to)
        midpoint = (soc + nxt) / Decimal(2)
        power = _power_at_soc(peak_power_kw, charge_type, midpoint)
        hours += energy_per_pct * (nxt - soc) / power
        soc = nxt

    energy_kwh = energy_per_pct * (soc_to - soc_from)
    return ChargePhysics(
        charge_type=charge_type,
        energy_kwh=energy_kwh,
        duration_minutes=hours * Decimal(60),
        peak_power_kw=peak_power_kw,
        average_power_kw=energy_kwh / hours,
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


async def run_simulation(
    db: AsyncSession,
    request: SimulationRequest,
    *,
    at: datetime | None = None,
) -> SimulationResult:
    vehicle = await _load_vehicle(db, request.vehicle_id)
    connector = await _load_connector(db, request.connector_id)

    charge_type: ChargeType = (
        "DC" if connector.power_type.upper().startswith("DC") else "AC"
    )

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

    estimate = await estimate_price(
        db,
        power_type=connector.power_type,
        tariff_price=connector.current_price_per_kwh,
        hour=at or datetime.now(UTC),
    )
    cost_eur = (
        float(physics.energy_kwh * estimate.price_per_kwh)
        if estimate is not None
        else None
    )

    return SimulationResult(
        charge_type=charge_type,
        soc_from=request.soc_from,
        soc_to=request.soc_to,
        energy_kwh=float(physics.energy_kwh),
        duration_minutes=float(physics.duration_minutes),
        peak_power_kw=float(physics.peak_power_kw),
        average_power_kw=float(physics.average_power_kw),
        cost_eur=cost_eur,
        price_per_kwh=float(estimate.price_per_kwh) if estimate else None,
        price_source=estimate.source if estimate else None,
        pvpc_per_kwh=float(estimate.pvpc_per_kwh)
        if estimate and estimate.pvpc_per_kwh is not None
        else None,
        margin_per_kwh=float(estimate.margin_per_kwh)
        if estimate and estimate.margin_per_kwh is not None
        else None,
    )
