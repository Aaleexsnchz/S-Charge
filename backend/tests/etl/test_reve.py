from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from app.etl.reve import (
    _tariff_changed_in_window,
    import_cpos,
    import_locations,
    import_tariffs,
    seed_backlog_from_ledger,
)
from app.integrations.reve import ReveClient
from app.models.charging_point import (
    ChargingPoint,
    ChargingPointSource,
    Connector,
    Evse,
)
from app.models.cpo import Cpo
from app.models.etl import ReveUnmirroredConnector
from app.models.tariff import Tariff, TariffElement
from pytest_httpx import HTTPXMock
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

BASE_URL = "https://reve.test/api/v1"
API_KEY = "secret-key"


def _cpo(**overrides: Any) -> dict[str, Any]:
    return {
        "id": "cpo-1",
        "cif": "B12345678",
        "party_id": "ES*ABC",
        "name": "Cargas Iberica",
        "address": "Calle Mayor 1",
        "country": "ES",
        "city": "Madrid",
        "city_code": "28079",
        "postal_code": "28001",
        "last_updated": "2026-04-01T00:00:00Z",
        **overrides,
    }


def _location(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "loc-1",
        "country_code": "ES",
        "party_id": "ES*ABC",
        "cpo_name": "Cargas Iberica",
        "version": "V221",
        "name": "Plaza Castilla",
        "address": "Plaza de Castilla 1",
        "city": "Madrid",
        "country": "ESP",
        "coordinates": {"latitude": "40.466667", "longitude": "-3.703333"},
        "evses": [
            {
                "id": "evse-1",
                "evse_id": "ES*ABC*E1",
                "accessibility": "SI",
                "coordinates": {"latitude": "40.466667", "longitude": "-3.703333"},
                "connectors": [
                    {
                        "id": "conn-1",
                        "standard": "IEC_62196_T2",
                        "format": "SOCKET",
                        "power_type": "AC_3_PHASE",
                        "max_voltage": 400,
                        "max_amperage": 32,
                        "last_static_updated": "2026-04-01T00:00:00Z",
                    }
                ],
                "last_static_updated": "2026-04-01T00:00:00Z",
            }
        ],
        "time_zone": "Europe/Madrid",
        "last_updated": "2026-04-01T00:00:00Z",
    }
    base.update(overrides)
    return base


@pytest.fixture
def reve_client() -> ReveClient:
    return ReveClient(api_key=API_KEY, base_url=BASE_URL)


async def test_import_cpos_initial_bootstrap(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=f"{BASE_URL}/cpos?page=1&limit=100", json=[_cpo()])

    async with reve_client as client:
        rows, last_page, exhausted = await import_cpos(client, db_session)

    assert rows == 1
    assert last_page == 1
    assert exhausted is True
    cpo = (await db_session.execute(select(Cpo))).scalar_one()
    assert cpo.party_id == "ES*ABC"
    assert cpo.name == "Cargas Iberica"
    assert cpo.raw_data is not None
    assert cpo.raw_data["id"] == "cpo-1"


async def test_import_cpos_idempotent(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=f"{BASE_URL}/cpos?page=1&limit=100", json=[_cpo()])
    httpx_mock.add_response(
        url=f"{BASE_URL}/cpos?page=1&limit=100",
        json=[_cpo(name="Cargas Iberica SA")],
    )

    async with reve_client as client:
        await import_cpos(client, db_session)
        await import_cpos(client, db_session)

    rows = (await db_session.execute(select(Cpo))).scalars().all()
    assert len(rows) == 1
    assert rows[0].name == "Cargas Iberica SA"


async def test_import_cpos_resumes_from_start_page(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    page_1 = [_cpo(id=f"cpo-{i}", party_id=f"ES*P{i:03d}") for i in range(1, 101)]
    page_2 = [_cpo(id="cpo-101", party_id="ES*P101")]
    httpx_mock.add_response(url=f"{BASE_URL}/cpos?page=1&limit=100", json=page_1)
    httpx_mock.add_response(url=f"{BASE_URL}/cpos?page=2&limit=100", json=page_2)

    async with reve_client as client:
        rows1, last1, exhausted1 = await import_cpos(client, db_session, max_pages=1)
        assert (rows1, last1, exhausted1) == (100, 1, False)

        rows2, last2, exhausted2 = await import_cpos(
            client, db_session, start_page=last1 + 1, max_pages=1
        )
        assert (rows2, last2, exhausted2) == (1, 2, True)

    total = (
        await db_session.execute(select(func.count()).select_from(Cpo))
    ).scalar_one()
    assert total == 101


async def test_import_locations_creates_full_chain(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=f"{BASE_URL}/cpos?page=1&limit=100", json=[_cpo()])
    httpx_mock.add_response(
        url=f"{BASE_URL}/locations?page=1&limit=100", json=[_location()]
    )

    async with reve_client as client:
        await import_cpos(client, db_session)
        await import_locations(client, db_session)

    cp = (await db_session.execute(select(ChargingPoint))).scalar_one()
    assert cp.source == ChargingPointSource.REVE_SEED
    assert cp.name == "Plaza Castilla"
    assert cp.party_id == "ES*ABC"
    assert cp.latitude == Decimal("40.466667")
    assert cp.longitude == Decimal("-3.703333")

    evse = (
        await db_session.execute(select(Evse).where(Evse.charging_point_id == cp.id))
    ).scalar_one()
    assert evse.evse_id == "ES*ABC*E1"
    assert evse.wheelchair_accessibility == "SI"

    connector = (
        await db_session.execute(select(Connector).where(Connector.evse_id == evse.id))
    ).scalar_one()
    assert connector.standard == "IEC_62196_T2"
    assert connector.max_voltage == 400


async def test_import_locations_preserves_null_name(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    nameless = _location()
    nameless.pop("name")
    httpx_mock.add_response(url=f"{BASE_URL}/cpos?page=1&limit=100", json=[_cpo()])
    httpx_mock.add_response(
        url=f"{BASE_URL}/locations?page=1&limit=100", json=[nameless]
    )

    async with reve_client as client:
        await import_cpos(client, db_session)
        await import_locations(client, db_session)

    cp = (await db_session.execute(select(ChargingPoint))).scalar_one()
    assert cp.name is None
    assert cp.cpo_name == "Cargas Iberica"


async def test_import_tariffs_stores_every_band(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=f"{BASE_URL}/cpos?page=1&limit=100", json=[_cpo()])
    httpx_mock.add_response(
        url=f"{BASE_URL}/locations?page=1&limit=100", json=[_location()]
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}/connectors/tariffs?page=1&limit=100",
        json=[
            {
                "evse_id": "evse-1",
                "connector_id": "conn-1",
                "tariffs": [
                    {
                        "id": "tariff-1",
                        "currency": "EUR",
                        "elements": [
                            {
                                "price_components": [
                                    {
                                        "type": "FLAT",
                                        "price": 0.8265,
                                        "vat": 21.0,
                                        "step_size": 1,
                                    }
                                ],
                                "restrictions": {"reservation": "RESERVATION_EXPIRES"},
                            },
                            {
                                "price_components": [
                                    {
                                        "type": "ENERGY",
                                        "price": 0.42,
                                        "vat": 21.0,
                                        "step_size": 1,
                                    }
                                ]
                            },
                        ],
                        "last_tariff_updated": "2026-04-20T12:00:00Z",
                    }
                ],
                "last_tariff_updated": "2026-04-20T12:00:00Z",
            }
        ],
    )

    async with reve_client as client:
        await import_cpos(client, db_session)
        await import_locations(client, db_session)
        rows, _, exhausted = await import_tariffs(client, db_session)

    assert rows == 1
    assert exhausted is True
    tariff = (await db_session.execute(select(Tariff))).scalar_one()
    assert tariff.currency == "EUR"

    elements = (
        (
            await db_session.execute(
                select(TariffElement).order_by(TariffElement.element_index)
            )
        )
        .scalars()
        .all()
    )
    assert [(e.component_type, e.price) for e in elements] == [
        ("FLAT", Decimal("0.8265")),
        ("ENERGY", Decimal("0.4200")),
    ]
    assert elements[0].reservation == "RESERVATION_EXPIRES"
    assert elements[1].reservation is None
    assert elements[1].vat == Decimal("21.00")
    assert elements[1].step_size == 1

    connector = (await db_session.execute(select(Connector))).scalar_one()
    assert connector.tariff_id == tariff.id


def _tariff_payload(*prices: float) -> list[dict[str, Any]]:
    return [
        {
            "evse_id": "evse-1",
            "connector_id": "conn-1",
            "tariffs": [
                {
                    "id": "tariff-1",
                    "currency": "EUR",
                    "elements": [
                        {
                            "price_components": [
                                {"type": "ENERGY", "price": price, "step_size": 1}
                            ]
                        }
                        for price in prices
                    ],
                    "last_tariff_updated": "2026-04-20T12:00:00Z",
                }
            ],
            "last_tariff_updated": "2026-04-20T12:00:00Z",
        }
    ]


async def test_reimporting_a_shorter_tariff_drops_the_old_bands(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=f"{BASE_URL}/cpos?page=1&limit=100", json=[_cpo()])
    httpx_mock.add_response(
        url=f"{BASE_URL}/locations?page=1&limit=100", json=[_location()]
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}/connectors/tariffs?page=1&limit=100",
        json=_tariff_payload(0.25, 0.29, 0.47),
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}/connectors/tariffs?page=1&limit=100",
        json=_tariff_payload(0.31),
    )

    async with reve_client as client:
        await import_cpos(client, db_session)
        await import_locations(client, db_session)
        await import_tariffs(client, db_session)
        await import_tariffs(client, db_session)

    prices = (await db_session.execute(select(TariffElement.price))).scalars().all()
    assert prices == [Decimal("0.3100")]


async def test_zero_restriction_bounds_are_stored_as_absent(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    """REVE writes 0 for "not set". Stored literally, `max_power = 0` would match
    no connector at all and `min_duration = 0` would look session-gated."""
    httpx_mock.add_response(url=f"{BASE_URL}/cpos?page=1&limit=100", json=[_cpo()])
    httpx_mock.add_response(
        url=f"{BASE_URL}/locations?page=1&limit=100", json=[_location()]
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}/connectors/tariffs?page=1&limit=100",
        json=[
            {
                "evse_id": "evse-1",
                "connector_id": "conn-1",
                "tariffs": [
                    {
                        "id": "tariff-zeros",
                        "currency": "EUR",
                        "elements": [
                            {
                                "price_components": [
                                    {"type": "ENERGY", "price": 0.37, "step_size": 1}
                                ],
                                "restrictions": {
                                    "start_time": "08:00",
                                    "end_time": "20:00",
                                    "min_power": 0,
                                    "max_power": 0,
                                    "min_current": 0,
                                    "max_current": 0,
                                    "min_kwh": 0,
                                    "max_kwh": 0,
                                    "min_duration": 0,
                                    "max_duration": 0,
                                },
                            }
                        ],
                        "last_tariff_updated": "2026-04-20T12:00:00Z",
                    }
                ],
                "last_tariff_updated": "2026-04-20T12:00:00Z",
            }
        ],
    )

    async with reve_client as client:
        await import_cpos(client, db_session)
        await import_locations(client, db_session)
        await import_tariffs(client, db_session)

    element = (await db_session.execute(select(TariffElement))).scalar_one()
    assert element.price == Decimal("0.3700")
    assert element.start_time is not None
    for bound in (
        element.min_power_kw,
        element.max_power_kw,
        element.min_current,
        element.max_current,
        element.min_kwh,
        element.max_kwh,
        element.min_duration_s,
        element.max_duration_s,
    ):
        assert bound is None


async def test_a_tariff_for_an_unknown_connector_is_recorded_not_dropped(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    """The price arrives once and does not come round again for ~243 days, so a
    repair pass needs it kept, not logged."""
    httpx_mock.add_response(
        url=f"{BASE_URL}/connectors/tariffs?page=1&limit=100",
        json=[
            {
                "evse_id": "ES*ABC*GHOST",
                "connector_id": "ghost",
                "tariffs": [
                    {
                        "id": "tariff-ghost",
                        "currency": "EUR",
                        "elements": [
                            {
                                "price_components": [
                                    {"type": "ENERGY", "price": 0.42, "step_size": 1}
                                ]
                            }
                        ],
                        "last_tariff_updated": "2026-04-20T12:00:00Z",
                    }
                ],
                "last_tariff_updated": "2026-04-20T12:00:00Z",
            }
        ],
    )

    async with reve_client as client:
        await import_tariffs(client, db_session)

    row = (await db_session.execute(select(ReveUnmirroredConnector))).scalar_one()
    assert row.evse_id == "ES*ABC*GHOST"
    assert row.connector_id == "ghost"
    assert row.tariff_raw["id"] == "tariff-ghost"
    assert row.tariff_raw["elements"][0]["price_components"][0]["price"] == 0.42


async def test_seeing_the_same_unknown_connector_twice_keeps_one_row(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    """It reappears on every cycle until repaired; the backlog must not inflate."""
    for price in (0.42, 0.55):
        httpx_mock.add_response(
            url=f"{BASE_URL}/connectors/tariffs?page=1&limit=100",
            json=[
                {
                    "evse_id": "ES*ABC*GHOST",
                    "connector_id": "ghost",
                    "tariffs": [
                        {
                            "id": "tariff-ghost",
                            "currency": "EUR",
                            "elements": [
                                {
                                    "price_components": [
                                        {
                                            "type": "ENERGY",
                                            "price": price,
                                            "step_size": 1,
                                        }
                                    ]
                                }
                            ],
                            "last_tariff_updated": "2026-04-20T12:00:00Z",
                        }
                    ],
                    "last_tariff_updated": "2026-04-20T12:00:00Z",
                }
            ],
        )

    async with reve_client as client:
        await import_tariffs(client, db_session)
        await import_tariffs(client, db_session)

    row = (await db_session.execute(select(ReveUnmirroredConnector))).scalar_one()
    # The newest price wins: the repair should import what REVE serves today.
    assert row.tariff_raw["elements"][0]["price_components"][0]["price"] == 0.55


async def test_import_tariffs_skips_unknown_connector(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}/connectors/tariffs?page=1&limit=100",
        json=[
            {
                "evse_id": "ES*ABC*GHOST",
                "connector_id": "ghost",
                "tariffs": [
                    {
                        "id": "tariff-ghost",
                        "currency": "EUR",
                        "elements": [
                            {
                                "price_components": [
                                    {"type": "ENERGY", "price": 0.5, "step_size": 1}
                                ]
                            }
                        ],
                        "last_tariff_updated": "2026-04-20T12:00:00Z",
                    }
                ],
                "last_tariff_updated": "2026-04-20T12:00:00Z",
            }
        ],
    )

    async with reve_client as client:
        await import_tariffs(client, db_session)

    tariff_count = (
        await db_session.execute(select(func.count()).select_from(Tariff))
    ).scalar_one()
    assert tariff_count == 0
    connector_count = (
        await db_session.execute(select(func.count()).select_from(Connector))
    ).scalar_one()
    assert connector_count == 0


async def test_import_tariffs_stores_the_source_price_verbatim(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=f"{BASE_URL}/cpos?page=1&limit=100", json=[_cpo()])
    httpx_mock.add_response(
        url=f"{BASE_URL}/locations?page=1&limit=100", json=[_location()]
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}/connectors/tariffs?page=1&limit=100",
        json=[
            {
                "evse_id": "evse-1",
                "connector_id": "conn-1",
                "tariffs": [
                    {
                        "id": "tariff-outlier",
                        "currency": "EUR",
                        "elements": [
                            {
                                "price_components": [
                                    {"type": "ENERGY", "price": 8676.82, "step_size": 1}
                                ]
                            }
                        ],
                        "last_tariff_updated": "2026-04-20T12:00:00Z",
                    }
                ],
                "last_tariff_updated": "2026-04-20T12:00:00Z",
            }
        ],
    )

    async with reve_client as client:
        await import_cpos(client, db_session)
        await import_locations(client, db_session)
        await import_tariffs(client, db_session)

    tariff = (await db_session.execute(select(Tariff))).scalar_one()
    assert tariff.source_id == "tariff-outlier"

    # The mirror stores what REVE published; rejecting an implausible price is
    # the resolver's job, not the ETL's.
    element = (await db_session.execute(select(TariffElement))).scalar_one()
    assert element.price == Decimal("8676.8200")

    connector = (await db_session.execute(select(Connector))).scalar_one()
    assert connector.tariff_id == tariff.id


def _tariff_row(last_tariff_updated: str | None) -> dict[str, Any]:
    return {"tariffs": [{"id": "t", "last_tariff_updated": last_tariff_updated}]}


@pytest.mark.parametrize(
    ("updated", "expected"),
    [
        ("2026-06-21T10:00:00Z", True),
        ("2026-06-20T23:59:59Z", False),
        ("2026-06-21T12:00:01Z", False),
        (None, False),
    ],
)
def test_tariff_changed_in_window(updated: str | None, expected: bool) -> None:
    window_start = datetime(2026, 6, 21, 0, 0, tzinfo=UTC)
    window_end = datetime(2026, 6, 21, 12, 0, tzinfo=UTC)
    assert (
        _tariff_changed_in_window(_tariff_row(updated), window_start, window_end)
        is expected
    )


def test_tariff_changed_in_window_no_tariff() -> None:
    window_start = datetime(2026, 6, 21, 0, 0, tzinfo=UTC)
    assert _tariff_changed_in_window({"tariffs": []}, window_start, None) is False


async def test_the_backlog_prices_a_station_the_moment_it_arrives(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    """The tariff arrives before the station and is banked; the station arrives
    later and the banked price is applied then.

    That ordering is the normal case, not an edge one: the refresh only fetches
    `/connectors/tariffs`, so it meets stations built since the seed before the
    catalogue pass can create them. Without the replay they would land unpriced
    and stay so for the ~243 days until their price next changes.
    """
    httpx_mock.add_response(
        url=f"{BASE_URL}/connectors/tariffs?page=1&limit=100",
        json=_tariff_payload(0.37),
    )
    httpx_mock.add_response(url=f"{BASE_URL}/cpos?page=1&limit=100", json=[_cpo()])
    httpx_mock.add_response(
        url=f"{BASE_URL}/locations?page=1&limit=100", json=[_location()]
    )

    async with reve_client as client:
        await import_tariffs(client, db_session)
        banked = (
            await db_session.execute(select(ReveUnmirroredConnector))
        ).scalar_one()
        assert banked.evse_id == "evse-1"

        await import_cpos(client, db_session)
        await import_locations(client, db_session)

    assert await seed_backlog_from_ledger(db_session) == 1

    connector = (await db_session.execute(select(Connector))).scalar_one()
    assert connector.tariff_id is not None, "the station must arrive priced"
    element = (await db_session.execute(select(TariffElement))).scalar_one()
    assert element.price == Decimal("0.3700")

    remaining = await db_session.scalar(
        select(func.count()).select_from(ReveUnmirroredConnector)
    )
    assert remaining == 0, "a consumed row is gone; the table size is the backlog"


async def test_the_backlog_keeps_rows_whose_station_never_arrives(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    """Whatever the catalogue pass cannot resolve stays, and its count is the
    measurement: connectors REVE serves tariffs for that it does not publish."""
    httpx_mock.add_response(
        url=f"{BASE_URL}/connectors/tariffs?page=1&limit=100",
        json=_tariff_payload(0.37),
    )

    async with reve_client as client:
        await import_tariffs(client, db_session)

    assert await seed_backlog_from_ledger(db_session) == 0
    remaining = await db_session.scalar(
        select(func.count()).select_from(ReveUnmirroredConnector)
    )
    assert remaining == 1
