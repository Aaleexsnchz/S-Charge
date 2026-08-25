from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from app.models.price import ElectricityPrice
from app.services.price_suggestion import (
    MARGIN_AC_EUR_PER_KWH,
    MARGIN_DC_EUR_PER_KWH,
    estimate_price,
    margin_for_power_type,
)
from sqlalchemy.ext.asyncio import AsyncSession

MADRID = ZoneInfo("Europe/Madrid")


@pytest.mark.parametrize(
    ("power_type", "expected"),
    [
        ("AC_1_PHASE", MARGIN_AC_EUR_PER_KWH),
        ("AC_3_PHASE", MARGIN_AC_EUR_PER_KWH),
        ("DC", MARGIN_DC_EUR_PER_KWH),
        ("dc", MARGIN_DC_EUR_PER_KWH),
    ],
)
def test_margin_for_power_type(power_type: str, expected: Decimal) -> None:
    assert margin_for_power_type(power_type) == expected


async def test_estimate_price_prefers_real_tariff(db_session: AsyncSession) -> None:
    estimate = await estimate_price(
        db_session,
        power_type="DC",
        tariff_price=Decimal("0.45"),
        hour=datetime(2026, 6, 26, 12, 0, tzinfo=MADRID),
    )

    assert estimate is not None
    assert estimate.source == "reve_tariff"
    assert estimate.price_per_kwh == Decimal("0.45")
    assert estimate.margin_per_kwh is None


async def test_estimate_price_falls_back_to_pvpc_plus_margin(
    db_session: AsyncSession,
) -> None:
    slot = datetime(2026, 6, 26, 12, 0, tzinfo=MADRID)
    db_session.add(ElectricityPrice(hour_start=slot, price_per_kwh=Decimal("0.18000")))
    await db_session.flush()

    estimate = await estimate_price(
        db_session,
        power_type="DC",
        tariff_price=None,
        hour=slot.replace(minute=37),
    )

    assert estimate is not None
    assert estimate.source == "pvpc_plus_margin"
    assert estimate.pvpc_per_kwh == Decimal("0.18000")
    assert estimate.margin_per_kwh == MARGIN_DC_EUR_PER_KWH
    assert estimate.price_per_kwh == Decimal("0.18000") + MARGIN_DC_EUR_PER_KWH


async def test_estimate_price_none_without_tariff_or_pvpc(
    db_session: AsyncSession,
) -> None:
    estimate = await estimate_price(
        db_session,
        power_type="AC_3_PHASE",
        tariff_price=None,
        hour=datetime(2030, 1, 1, 3, 0, tzinfo=MADRID),
    )

    assert estimate is None
