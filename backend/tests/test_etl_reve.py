from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from pytest_httpx import HTTPXMock
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.etl.reve import (
    import_cpos,
    import_evse_operational_status,
    import_locations,
    import_tariffs,
)
from app.integrations.reve import ReveClient
from app.models.charging_point import ChargingPoint, ChargingPointSource, Connector, Evse
from app.models.cpo import Cpo
from app.models.tariff import Tariff

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
        count = await import_cpos(client, db_session)

    assert count == 1
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


async def test_import_locations_creates_full_chain(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=f"{BASE_URL}/cpos?page=1&limit=100", json=[_cpo()])
    httpx_mock.add_response(url=f"{BASE_URL}/locations?page=1&limit=100", json=[_location()])

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


async def test_import_locations_archives_missing_on_full_refresh(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    first = _location(id="loc-1", name="Keep")
    second = _location(id="loc-2", name="Drop")
    httpx_mock.add_response(url=f"{BASE_URL}/cpos?page=1&limit=100", json=[_cpo()])
    httpx_mock.add_response(url=f"{BASE_URL}/locations?page=1&limit=100", json=[first, second])
    httpx_mock.add_response(url=f"{BASE_URL}/locations?page=1&limit=100", json=[first])

    async with reve_client as client:
        await import_cpos(client, db_session)
        await import_locations(client, db_session)
        await import_locations(client, db_session)

    rows = (
        (await db_session.execute(select(ChargingPoint).order_by(ChargingPoint.source_id)))
        .scalars()
        .all()
    )
    by_id = {cp.source_id: cp for cp in rows}
    assert by_id["loc-1"].archived_at is None
    assert by_id["loc-2"].archived_at is not None


async def test_import_locations_preserves_null_name(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    nameless = _location()
    nameless.pop("name")
    httpx_mock.add_response(url=f"{BASE_URL}/cpos?page=1&limit=100", json=[_cpo()])
    httpx_mock.add_response(url=f"{BASE_URL}/locations?page=1&limit=100", json=[nameless])

    async with reve_client as client:
        await import_cpos(client, db_session)
        await import_locations(client, db_session)

    cp = (await db_session.execute(select(ChargingPoint))).scalar_one()
    assert cp.name is None
    assert cp.cpo_name == "Cargas Iberica"


async def test_import_evse_operational_status_updates_existing(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=f"{BASE_URL}/cpos?page=1&limit=100", json=[_cpo()])
    httpx_mock.add_response(url=f"{BASE_URL}/locations?page=1&limit=100", json=[_location()])
    httpx_mock.add_response(
        url=f"{BASE_URL}/evses/operational_status?page=1&limit=100",
        json=[
            {
                "id": "evse-1",
                "evse_id": "ES*ABC*E1",
                "operational_status": True,
                "last_operational_status_updated": "2026-04-15T10:00:00Z",
            }
        ],
    )

    async with reve_client as client:
        await import_cpos(client, db_session)
        await import_locations(client, db_session)
        count = await import_evse_operational_status(client, db_session)

    assert count == 1
    evse = (await db_session.execute(select(Evse))).scalar_one()
    assert evse.is_operational is True
    assert evse.operational_status_updated_at == datetime(2026, 4, 15, 10, 0, tzinfo=UTC)


async def test_import_tariffs_links_connector_and_extracts_price(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=f"{BASE_URL}/cpos?page=1&limit=100", json=[_cpo()])
    httpx_mock.add_response(url=f"{BASE_URL}/locations?page=1&limit=100", json=[_location()])
    httpx_mock.add_response(
        url=f"{BASE_URL}/connectors/tariffs?page=1&limit=100",
        json=[
            {
                "evse_id": "ES*ABC*E1",
                "connector_id": "conn-1",
                "tariffs": {
                    "id": "tariff-1",
                    "currency": "EUR",
                    "elements": {
                        "price_components": {
                            "type": "ENERGY",
                            "price": "0.4200",
                            "vat": "21.00",
                            "step_size": 1,
                        }
                    },
                    "last_tariff_updated": "2026-04-20T12:00:00Z",
                },
                "last_tariff_updated": "2026-04-20T12:00:00Z",
            }
        ],
    )

    async with reve_client as client:
        await import_cpos(client, db_session)
        await import_locations(client, db_session)
        count = await import_tariffs(client, db_session)

    assert count == 1
    tariff = (await db_session.execute(select(Tariff))).scalar_one()
    assert tariff.currency == "EUR"
    assert tariff.price_per_kwh == Decimal("0.4200")
    assert tariff.vat_percentage == Decimal("21.00")
    assert tariff.price_component_type == "ENERGY"

    connector = (await db_session.execute(select(Connector))).scalar_one()
    assert connector.tariff_id == tariff.id


async def test_import_tariffs_skips_unknown_connector(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}/connectors/tariffs?page=1&limit=100",
        json=[
            {
                "evse_id": "ES*ABC*GHOST",
                "connector_id": "ghost",
                "tariffs": {
                    "id": "tariff-ghost",
                    "currency": "EUR",
                    "elements": {
                        "price_components": {
                            "type": "ENERGY",
                            "price": "0.5",
                            "step_size": 1,
                        }
                    },
                    "last_tariff_updated": "2026-04-20T12:00:00Z",
                },
                "last_tariff_updated": "2026-04-20T12:00:00Z",
            }
        ],
    )

    async with reve_client as client:
        await import_tariffs(client, db_session)

    tariff_count = (await db_session.execute(select(func.count()).select_from(Tariff))).scalar_one()
    assert tariff_count == 1
    connector_count = (
        await db_session.execute(select(func.count()).select_from(Connector))
    ).scalar_one()
    assert connector_count == 0
