import uuid
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
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
from app.services.tariff_pricing import recompute_connector_prices
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

MADRID = ZoneInfo("Europe/Madrid")
NOW = datetime(2026, 6, 1, tzinfo=UTC)

NIGHT = (time(0, 0), time(6, 59))
DAY = (time(7, 0), time(22, 59))
LATE = (time(23, 0), time(23, 59))

# The real nine-element tariff measured on 2026-08-22: three time bands crossed
# with three connector-power bands. One `price_per_kwh` on the tariff row cannot
# describe it, which is the whole reason this table exists.
NINE_ELEMENT_TARIFF: list[dict[str, Any]] = [
    {"band": NIGHT, "max_power_kw": 22, "price": "0.25"},
    {"band": DAY, "max_power_kw": 22, "price": "0.29"},
    {"band": LATE, "max_power_kw": 22, "price": "0.25"},
    {"band": NIGHT, "max_power_kw": 100, "price": "0.31"},
    {"band": DAY, "max_power_kw": 100, "price": "0.37"},
    {"band": LATE, "max_power_kw": 100, "price": "0.31"},
    {"band": NIGHT, "max_power_kw": 450, "price": "0.40"},
    {"band": DAY, "max_power_kw": 450, "price": "0.47"},
    {"band": LATE, "max_power_kw": 450, "price": "0.40"},
]


async def _connector_on(
    db: AsyncSession,
    elements: list[dict[str, Any]],
    *,
    max_electric_power: int | None = 22000,
    time_zone: str = "Europe/Madrid",
) -> uuid.UUID:
    """A point/evse/connector wired to a tariff built from ``elements``."""
    tariff = None
    if elements is not None:
        tariff = Tariff(
            id=uuid.uuid4(),
            source_id=str(uuid.uuid4()),
            currency="EUR",
            raw_data={},
            source_last_updated_at=NOW,
            last_refreshed_at=NOW,
        )
        db.add(tariff)
        for index, spec in enumerate(elements):
            band = spec.get("band")
            db.add(
                TariffElement(
                    tariff_id=tariff.id,
                    element_index=index,
                    component_type=spec.get("component_type", "ENERGY"),
                    price=Decimal(spec["price"]),
                    start_time=band[0] if band else None,
                    end_time=band[1] if band else None,
                    max_power_kw=(
                        Decimal(str(spec["max_power_kw"]))
                        if spec.get("max_power_kw") is not None
                        else None
                    ),
                    days_of_week=spec.get("days_of_week"),
                    start_date=spec.get("start_date"),
                    end_date=spec.get("end_date"),
                    min_kwh=spec.get("min_kwh"),
                    reservation=spec.get("reservation"),
                )
            )

    point = ChargingPoint(
        source=ChargingPointSource.REVE_SEED,
        source_id=str(uuid.uuid4()),
        address="Calle Falsa 123",
        city="Madrid",
        country_code="ESP",
        latitude=Decimal("40.416800"),
        longitude=Decimal("-3.703800"),
        time_zone=time_zone,
        opening_24_7=True,
        source_last_updated_at=NOW,
    )
    evse = Evse(source_id=str(uuid.uuid4()), source_last_updated_at=NOW)
    connector = Connector(
        source_id=str(uuid.uuid4()),
        standard="IEC_62196_T2",
        format="SOCKET",
        power_type="AC_3_PHASE",
        max_voltage=400,
        max_amperage=32,
        max_electric_power=max_electric_power,
        tariff_id=tariff.id if tariff else None,
        source_last_updated_at=NOW,
    )
    evse.connectors.append(connector)
    point.evses.append(evse)
    db.add(point)
    await db.flush()
    return connector.id


async def _resolve(
    db: AsyncSession, connector_id: uuid.UUID, at: datetime
) -> Connector:
    await recompute_connector_prices(db, at)
    db.expire_all()
    return (
        await db.execute(select(Connector).where(Connector.id == connector_id))
    ).scalar_one()


def _madrid(hour: int, minute: int = 0) -> datetime:
    """The instant at which a Madrid clock reads ``hour:minute`` on a Wednesday."""
    return datetime(2026, 6, 10, hour, minute, tzinfo=MADRID).astimezone(UTC)


@pytest.mark.parametrize(
    ("power_w", "hour", "expected"),
    [
        (22_000, 20, "0.29"),
        (100_000, 20, "0.37"),
        (450_000, 20, "0.47"),
        (450_000, 3, "0.40"),
        (100_000, 23, "0.31"),
        (22_000, 3, "0.25"),
    ],
)
async def test_price_resolves_by_hour_and_connector_power(
    db_session: AsyncSession, power_w: int, hour: int, expected: str
) -> None:
    connector_id = await _connector_on(
        db_session, NINE_ELEMENT_TARIFF, max_electric_power=power_w
    )
    connector = await _resolve(db_session, connector_id, _madrid(hour))

    assert connector.pricing_kind == PricingKind.ENERGY
    assert connector.current_price_per_kwh == Decimal(expected)


async def test_power_band_upper_bound_is_inclusive(db_session: AsyncSession) -> None:
    """A 22 kW connector belongs in the "up to 22 kW" band, not the next one up."""
    connector_id = await _connector_on(
        db_session, NINE_ELEMENT_TARIFF, max_electric_power=22_000
    )
    connector = await _resolve(db_session, connector_id, _madrid(12))

    assert connector.current_price_per_kwh == Decimal("0.29")


async def test_band_end_minute_is_inclusive(db_session: AsyncSession) -> None:
    """06:59 is still the night band; an exclusive end would price it as unknown."""
    connector_id = await _connector_on(db_session, NINE_ELEMENT_TARIFF)
    connector = await _resolve(db_session, connector_id, _madrid(6, 59))

    assert connector.current_price_per_kwh == Decimal("0.25")


async def test_bands_are_read_in_the_points_own_timezone(
    db_session: AsyncSession,
) -> None:
    """07:30 in Madrid is 06:30 in the Canaries, still inside the night band."""
    peninsula = await _connector_on(db_session, NINE_ELEMENT_TARIFF)
    canaries = await _connector_on(
        db_session, NINE_ELEMENT_TARIFF, time_zone="Atlantic/Canary"
    )
    at = _madrid(7, 30)

    assert (await _resolve(db_session, peninsula, at)).current_price_per_kwh == Decimal(
        "0.29"
    )
    assert (await _resolve(db_session, canaries, at)).current_price_per_kwh == Decimal(
        "0.25"
    )


async def test_a_restricted_band_beats_the_unrestricted_fallback(
    db_session: AsyncSession,
) -> None:
    """127 tariffs list an unrestricted band first and the real windows after it.

    Taking them in source order hands the driver the fallback price during a
    window that is meant to be cheaper.
    """
    connector_id = await _connector_on(
        db_session,
        [
            {"price": "0.4959"},
            {"band": (time(8, 0), time(20, 0)), "price": "0.3719"},
        ],
    )

    assert (
        await _resolve(db_session, connector_id, _madrid(12))
    ).current_price_per_kwh == Decimal("0.3719")
    assert (
        await _resolve(db_session, connector_id, _madrid(22))
    ).current_price_per_kwh == Decimal("0.4959")


async def test_an_explicit_zero_energy_price_is_free(db_session: AsyncSession) -> None:
    """Free is a claim the source made: energy, priced at zero."""
    connector_id = await _connector_on(
        db_session, [{"component_type": "ENERGY", "price": "0.0"}]
    )
    connector = await _resolve(db_session, connector_id, _madrid(12))

    assert connector.pricing_kind == PricingKind.FREE
    assert connector.current_price_per_kwh is None


async def test_a_zeroed_flat_template_is_unknown_not_free(
    db_session: AsyncSession,
) -> None:
    """1,144 connectors carry a lone `FLAT 0` with no vat, step_size 0 and no
    energy band — an unfilled record, not a free charger. Labelling those
    *gratis* would send a driver to a charger that bills them."""
    connector_id = await _connector_on(
        db_session, [{"component_type": "FLAT", "price": "0.0"}]
    )
    connector = await _resolve(db_session, connector_id, _madrid(12))

    assert connector.pricing_kind == PricingKind.UNKNOWN
    assert connector.current_price_per_kwh is None


async def test_time_priced_connector_says_so(db_session: AsyncSession) -> None:
    connector_id = await _connector_on(
        db_session, [{"component_type": "TIME", "price": "3.85"}]
    )
    connector = await _resolve(db_session, connector_id, _madrid(12))

    assert connector.pricing_kind == PricingKind.TIME
    assert connector.current_price_per_kwh is None


async def test_energy_beats_a_flat_session_fee(db_session: AsyncSession) -> None:
    connector_id = await _connector_on(
        db_session,
        [
            {"component_type": "FLAT", "price": "0.50"},
            {"component_type": "ENERGY", "price": "0.42"},
        ],
    )
    connector = await _resolve(db_session, connector_id, _madrid(12))

    assert connector.pricing_kind == PricingKind.ENERGY
    assert connector.current_price_per_kwh == Decimal("0.42")


async def test_implausible_source_price_is_rejected(db_session: AsyncSession) -> None:
    """One connector carries ENERGY 9110.66 — bad data at source, not a price."""
    connector_id = await _connector_on(
        db_session, [{"component_type": "ENERGY", "price": "9110.66"}]
    )
    connector = await _resolve(db_session, connector_id, _madrid(12))

    assert connector.pricing_kind == PricingKind.UNKNOWN
    assert connector.current_price_per_kwh is None


async def test_an_expired_tariff_does_not_price(db_session: AsyncSession) -> None:
    """2,138 connectors carry a tariff past its own validity window, and those
    average a third of the live price — ended promotions, not stale defaults."""
    connector_id = await _connector_on(db_session, [{"price": "0.1129"}])
    await db_session.execute(
        update(Tariff).values(
            valid_from=datetime(2026, 1, 1, tzinfo=UTC),
            valid_to=datetime(2026, 3, 31, tzinfo=UTC),
        )
    )

    assert (
        await _resolve(db_session, connector_id, _madrid(12))
    ).pricing_kind == PricingKind.UNKNOWN
    assert (
        await _resolve(db_session, connector_id, datetime(2026, 2, 1, tzinfo=UTC))
    ).current_price_per_kwh == Decimal("0.1129")


async def test_connector_without_a_tariff_is_unknown(db_session: AsyncSession) -> None:
    connector_id = await _connector_on(db_session, [])
    connector = await _resolve(db_session, connector_id, _madrid(12))

    assert connector.pricing_kind == PricingKind.UNKNOWN
    assert connector.current_price_per_kwh is None


async def test_single_day_dated_band_applies_on_its_own_day(
    db_session: AsyncSession,
) -> None:
    """CPOs publish dated schedules with start_date = end_date for one day."""
    day = date(2026, 6, 10)
    connector_id = await _connector_on(
        db_session, [{"price": "0.43", "start_date": day, "end_date": day}]
    )

    assert (
        await _resolve(db_session, connector_id, _madrid(12))
    ).current_price_per_kwh == Decimal("0.43")
    assert (
        await _resolve(db_session, connector_id, _madrid(12) + timedelta(days=1))
    ).pricing_kind == PricingKind.UNKNOWN


async def test_weekday_restriction_is_honoured(db_session: AsyncSession) -> None:
    """2026-06-10 is a Wednesday."""
    connector_id = await _connector_on(
        db_session,
        [
            {"price": "0.20", "days_of_week": ["SATURDAY", "SUNDAY"]},
            {"price": "0.35", "days_of_week": ["WEDNESDAY"]},
        ],
    )
    connector = await _resolve(db_session, connector_id, _madrid(12))

    assert connector.current_price_per_kwh == Decimal("0.35")


async def test_reservation_and_session_gated_bands_do_not_price_now(
    db_session: AsyncSession,
) -> None:
    """A reservation fee is not a charging price, and a band behind min_kwh is
    not yet active when the session has drawn nothing."""
    connector_id = await _connector_on(
        db_session,
        [
            {"component_type": "FLAT", "price": "2.00", "reservation": "RESERVATION"},
            {"price": "0.19", "min_kwh": Decimal("20")},
            {"price": "0.31"},
        ],
    )
    connector = await _resolve(db_session, connector_id, _madrid(12))

    assert connector.pricing_kind == PricingKind.ENERGY
    assert connector.current_price_per_kwh == Decimal("0.31")
