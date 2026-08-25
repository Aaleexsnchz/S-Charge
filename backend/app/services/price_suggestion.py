"""PVPC plus a calibrated CPO margin: a price to *suggest*, never to attribute.

No caller today, deliberately. The simulator used to fall back to this when REVE
published no tariff, which presented an estimate as the operator's price; it now
reports no cost instead. What survives is the recommendation an owner is offered
when pricing their own point in Phase 7, where a suggested number is the point
rather than a claim about someone else's charger.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.pvpc import price_for_hour

MARGIN_AC_EUR_PER_KWH = Decimal("0.22")
MARGIN_DC_EUR_PER_KWH = Decimal("0.32")

PriceSource = Literal["reve_tariff", "pvpc_plus_margin"]


@dataclass(frozen=True)
class PriceEstimate:
    price_per_kwh: Decimal
    source: PriceSource
    pvpc_per_kwh: Decimal | None = None
    margin_per_kwh: Decimal | None = None


def margin_for_power_type(power_type: str) -> Decimal:
    if power_type.upper().startswith("DC"):
        return MARGIN_DC_EUR_PER_KWH
    return MARGIN_AC_EUR_PER_KWH


async def estimate_price(
    db: AsyncSession,
    *,
    power_type: str,
    tariff_price: Decimal | None,
    hour: datetime,
) -> PriceEstimate | None:
    """Price a kWh: the real REVE tariff if known, else PVPC(hour) + margin.

    Returns ``None`` when there is no real tariff and no PVPC slot for the hour.
    """
    if tariff_price is not None:
        return PriceEstimate(price_per_kwh=tariff_price, source="reve_tariff")

    pvpc = await price_for_hour(db, hour)
    if pvpc is None:
        return None

    margin = margin_for_power_type(power_type)
    return PriceEstimate(
        price_per_kwh=pvpc + margin,
        source="pvpc_plus_margin",
        pvpc_per_kwh=pvpc,
        margin_per_kwh=margin,
    )
