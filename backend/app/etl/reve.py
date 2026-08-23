import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.reve import ReveClient
from app.models.charging_point import (
    ChargingPoint,
    ChargingPointSource,
    Connector,
    Evse,
)
from app.models.cpo import Cpo
from app.models.tariff import Tariff, TariffElement
from app.utils.audit import audit

logger = logging.getLogger(__name__)

PAGE_SIZE = 100


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _decimal_or_none(value: str | float | None) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(str(value))


def _bound(value: str | float | None) -> Decimal | None:
    """A restriction bound, with REVE's ``0`` placeholder read as "not set".

    A band capped at ``max_power = 0`` would match no connector at all, and one
    gated behind ``min_duration = 0`` is not gated. REVE emits zeros for both
    rather than omitting the field; ``raw_data`` keeps the literal source.
    """
    parsed = _decimal_or_none(value)
    return None if parsed == 0 else parsed


def _int_bound(value: int | None) -> int | None:
    return value or None


def _parse_time(value: str | None) -> time | None:
    if not value:
        return None
    try:
        return time.fromisoformat(value)
    except ValueError:
        return None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _ensure_list(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _element_rows(tariff_pk: uuid.UUID, elements: Any) -> list[dict[str, Any]]:
    """Flatten an OCPI ``elements`` array to one row per price component.

    REVE follows OCPI, where ``elements`` and ``price_components`` are arrays;
    accept the single-object shape too so older fixtures keep working.
    """
    rows: list[dict[str, Any]] = []
    for index, element in enumerate(_ensure_list(elements)):
        restrictions = element.get("restrictions") or {}
        days = restrictions.get("day_of_week")
        for component in _ensure_list(element.get("price_components")):
            component_type = component.get("type")
            if not component_type:
                continue
            rows.append(
                {
                    "id": uuid.uuid4(),
                    "tariff_id": tariff_pk,
                    "element_index": index,
                    "component_type": component_type,
                    "price": _decimal_or_none(component.get("price")),
                    "vat": _decimal_or_none(component.get("vat")),
                    "step_size": component.get("step_size"),
                    "start_time": _parse_time(restrictions.get("start_time")),
                    "end_time": _parse_time(restrictions.get("end_time")),
                    "start_date": _parse_date(restrictions.get("start_date")),
                    "end_date": _parse_date(restrictions.get("end_date")),
                    "days_of_week": [str(d).upper() for d in days] if days else None,
                    "min_kwh": _bound(restrictions.get("min_kwh")),
                    "max_kwh": _bound(restrictions.get("max_kwh")),
                    "min_current": _bound(restrictions.get("min_current")),
                    "max_current": _bound(restrictions.get("max_current")),
                    "min_power_kw": _bound(restrictions.get("min_power")),
                    "max_power_kw": _bound(restrictions.get("max_power")),
                    "min_duration_s": _int_bound(restrictions.get("min_duration")),
                    "max_duration_s": _int_bound(restrictions.get("max_duration")),
                    "reservation": restrictions.get("reservation"),
                }
            )
    return rows


def _first_tariff(raw: dict[str, Any]) -> dict[str, Any] | None:
    raw_tariff = raw.get("tariffs")
    if isinstance(raw_tariff, list):
        return raw_tariff[0] if raw_tariff else None
    return raw_tariff or None


def _tariff_changed_in_window(
    raw: dict[str, Any],
    date_from: datetime | None,
    date_to: datetime | None,
) -> bool:
    """Whether the tariff genuinely changed at REVE inside the refresh window.

    The upsert rewrites every fetched row unconditionally, so the fetched count
    overstates real movement; only rows whose ``last_tariff_updated`` lands in
    ``[date_from, date_to]`` actually changed at the source.
    """
    raw_tariff = _first_tariff(raw)
    if raw_tariff is None:
        return False
    updated = _parse_dt(raw_tariff.get("last_tariff_updated"))
    if updated is None:
        return False
    if date_from is not None and updated < date_from:
        return False
    return date_to is None or updated <= date_to


def _window_params(
    date_from: datetime | None, date_to: datetime | None = None
) -> dict[str, Any] | None:
    params: dict[str, Any] = {}
    if date_from is not None:
        params["date_from"] = date_from.isoformat()
    if date_to is not None:
        params["date_to"] = date_to.isoformat()
    return params or None


async def _paginate_with_budget(
    client: ReveClient,
    path: str,
    base_params: dict[str, Any] | None,
    process_item: Callable[[dict[str, Any]], Awaitable[None]],
    *,
    start_page: int,
    max_pages: int | None,
) -> tuple[int, int, bool]:
    """Fetch consecutive pages of REVE data, calling ``process_item`` per row.

    Returns ``(rows_processed, last_page_completed, exhausted)``. ``exhausted``
    is ``True`` when REVE returned a short page (< PAGE_SIZE), signalling no
    more data; the cursor in the caller can then stamp ``completed_at``.
    """
    rows = 0
    last_page_completed = start_page - 1
    exhausted = False
    pages_fetched = 0
    page = start_page

    while True:
        if max_pages is not None and pages_fetched >= max_pages:
            break
        page_params = {**(base_params or {}), "page": page, "limit": PAGE_SIZE}
        items = await client.get(path, params=page_params)
        for item in items:
            await process_item(item)
            rows += 1
        last_page_completed = page
        pages_fetched += 1
        if len(items) < PAGE_SIZE:
            exhausted = True
            break
        page += 1

    return rows, last_page_completed, exhausted


async def _upsert_cpo(db: AsyncSession, raw: dict[str, Any]) -> None:
    payload: dict[str, Any] = {
        "id": uuid.uuid4(),
        "source_id": raw["id"],
        "party_id": raw["party_id"],
        "cif": raw["cif"],
        "name": raw["name"],
        "address": raw["address"],
        "city": raw["city"],
        "city_code": raw["city_code"],
        "postal_code": raw["postal_code"],
        "region": raw.get("region"),
        "state": raw.get("state"),
        "country": raw["country"],
        "phone": raw.get("phone"),
        "website": raw.get("website"),
        "confirmed_at": _parse_dt(raw.get("confirmed_at")),
        "raw_data": raw,
        "source_last_updated_at": _parse_dt(raw["last_updated"]),
    }
    stmt = insert(Cpo).values(**payload)
    stmt = stmt.on_conflict_do_update(
        index_elements=["source_id"],
        set_={k: stmt.excluded[k] for k in payload if k not in ("id", "source_id")},
    )
    await db.execute(stmt)


async def _upsert_connector(
    db: AsyncSession,
    evse_pk: uuid.UUID,
    raw: dict[str, Any],
) -> None:
    payload: dict[str, Any] = {
        "id": uuid.uuid4(),
        "evse_id": evse_pk,
        "source_id": raw["id"],
        "standard": raw["standard"],
        "format": raw["format"],
        "power_type": raw["power_type"],
        "max_electric_power": raw.get("max_electric_power"),
        "max_voltage": raw["max_voltage"],
        "max_amperage": raw["max_amperage"],
        "source_last_updated_at": _parse_dt(raw["last_static_updated"]),
    }
    stmt = insert(Connector).values(**payload)
    stmt = stmt.on_conflict_do_update(
        index_elements=["evse_id", "source_id"],
        set_={
            k: stmt.excluded[k]
            for k in payload
            if k not in ("id", "evse_id", "source_id")
        },
    )
    await db.execute(stmt)


async def _upsert_evse(
    db: AsyncSession,
    charging_point_id: uuid.UUID,
    raw: dict[str, Any],
) -> None:
    payload: dict[str, Any] = {
        "id": uuid.uuid4(),
        "charging_point_id": charging_point_id,
        "source_id": raw["id"],
        "evse_id": raw.get("evse_id"),
        "physical_reference": raw.get("physical_reference"),
        "floor_level": raw.get("floor_level"),
        "capabilities": raw.get("capabilities"),
        "wheelchair_accessibility": raw.get("accessibility"),
        "source_last_updated_at": _parse_dt(raw["last_static_updated"]),
    }
    base = insert(Evse).values(**payload)
    stmt = base.on_conflict_do_update(
        index_elements=["charging_point_id", "source_id"],
        set_={
            k: base.excluded[k]
            for k in payload
            if k not in ("id", "charging_point_id", "source_id")
        },
    ).returning(Evse.id)
    evse_pk: uuid.UUID = (await db.execute(stmt)).scalar_one()

    for raw_conn in _ensure_list(raw.get("connectors")):
        await _upsert_connector(db, evse_pk, raw_conn)


async def _upsert_location(db: AsyncSession, raw: dict[str, Any]) -> None:
    coords = raw["coordinates"]
    opening_times = raw.get("opening_times") or {}

    payload: dict[str, Any] = {
        "id": uuid.uuid4(),
        "source": ChargingPointSource.REVE_SEED,
        "source_id": raw["id"],
        "name": raw.get("name"),
        "cpo_name": raw["cpo_name"],
        "party_id": raw["party_id"],
        "version": raw.get("version"),
        "address": raw["address"],
        "city": raw["city"],
        "postal_code": raw.get("postal_code"),
        "region": raw.get("region"),
        "state": raw.get("state"),
        "country_code": raw["country_code"],
        "latitude": Decimal(coords["latitude"]),
        "longitude": Decimal(coords["longitude"]),
        "parking_type": raw.get("parking_type"),
        "facilities": raw.get("facilities"),
        "time_zone": raw.get("time_zone") or "Europe/Madrid",
        "opening_24_7": opening_times.get("twentyfourseven", False),
        "opening_hours": opening_times.get("regular_hours"),
        "charging_when_closed": raw.get("charging_when_closed"),
        "directions": raw.get("directions"),
        "source_last_updated_at": _parse_dt(raw["last_updated"]),
        "archived_at": None,
    }

    base = insert(ChargingPoint).values(**payload)
    stmt = base.on_conflict_do_update(
        index_elements=["source", "source_id"],
        set_={
            k: base.excluded[k]
            for k in payload
            if k not in ("id", "source", "source_id")
        },
    ).returning(ChargingPoint.id)
    cp_id: uuid.UUID = (await db.execute(stmt)).scalar_one()

    for raw_evse in _ensure_list(raw.get("evses")):
        await _upsert_evse(db, cp_id, raw_evse)


async def _upsert_connector_tariff(
    db: AsyncSession,
    raw: dict[str, Any],
    refreshed_at: datetime,
) -> None:
    raw_tariff = _first_tariff(raw)
    if raw_tariff is None:
        return

    connector_lookup = (
        select(Connector.id)
        .join(Evse, Connector.evse_id == Evse.id)
        .where(Evse.source_id == raw["evse_id"])
        .where(Connector.source_id == raw["connector_id"])
    )
    connector_pk = (await db.execute(connector_lookup)).scalar_one_or_none()
    if connector_pk is None:
        logger.warning(
            "reve_tariff_connector_not_found evse_id=%s connector_id=%s",
            raw["evse_id"],
            raw["connector_id"],
        )
        return

    tariff_payload: dict[str, Any] = {
        "id": uuid.uuid4(),
        "source_id": raw_tariff["id"],
        "currency": raw_tariff["currency"],
        "valid_from": _parse_dt(raw_tariff.get("start_date_time")),
        "valid_to": _parse_dt(raw_tariff.get("end_date_time")),
        "raw_data": raw_tariff,
        "source_last_updated_at": _parse_dt(raw_tariff["last_tariff_updated"]),
        "last_refreshed_at": refreshed_at,
    }
    base = insert(Tariff).values(**tariff_payload)
    stmt = base.on_conflict_do_update(
        index_elements=["source_id"],
        set_={
            k: base.excluded[k] for k in tariff_payload if k not in ("id", "source_id")
        },
    ).returning(Tariff.id)
    tariff_pk: uuid.UUID = (await db.execute(stmt)).scalar_one()

    await db.execute(delete(TariffElement).where(TariffElement.tariff_id == tariff_pk))
    element_rows = _element_rows(tariff_pk, raw_tariff.get("elements"))
    if element_rows:
        await db.execute(insert(TariffElement), element_rows)
    else:
        logger.warning("reve_tariff_without_elements source_id=%s", raw_tariff["id"])

    await db.execute(
        update(Connector)
        .where(Connector.id == connector_pk)
        .values(tariff_id=tariff_pk)
    )


async def import_cpos(
    client: ReveClient,
    db: AsyncSession,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    start_page: int = 1,
    max_pages: int | None = None,
) -> tuple[int, int, bool]:
    async def _process(raw: dict[str, Any]) -> None:
        await _upsert_cpo(db, raw)

    rows, last_page, exhausted = await _paginate_with_budget(
        client,
        "/cpos",
        _window_params(date_from, date_to),
        _process,
        start_page=start_page,
        max_pages=max_pages,
    )
    audit(
        "reve_etl_cpos",
        rows=rows,
        last_page=last_page,
        exhausted=exhausted,
        start_page=start_page,
        max_pages=max_pages,
    )
    return rows, last_page, exhausted


async def import_locations(
    client: ReveClient,
    db: AsyncSession,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    start_page: int = 1,
    max_pages: int | None = None,
) -> tuple[int, int, bool]:
    async def _process(raw: dict[str, Any]) -> None:
        await _upsert_location(db, raw)

    rows, last_page, exhausted = await _paginate_with_budget(
        client,
        "/locations",
        _window_params(date_from, date_to),
        _process,
        start_page=start_page,
        max_pages=max_pages,
    )
    audit(
        "reve_etl_locations",
        rows=rows,
        last_page=last_page,
        exhausted=exhausted,
        start_page=start_page,
        max_pages=max_pages,
    )
    return rows, last_page, exhausted


async def import_tariffs(
    client: ReveClient,
    db: AsyncSession,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    start_page: int = 1,
    max_pages: int | None = None,
) -> tuple[int, int, bool]:
    refreshed_at = datetime.now(UTC)
    changed = 0

    async def _process(raw: dict[str, Any]) -> None:
        nonlocal changed
        if _tariff_changed_in_window(raw, date_from, date_to):
            changed += 1
        await _upsert_connector_tariff(db, raw, refreshed_at)

    rows, last_page, exhausted = await _paginate_with_budget(
        client,
        "/connectors/tariffs",
        _window_params(date_from, date_to),
        _process,
        start_page=start_page,
        max_pages=max_pages,
    )
    audit(
        "reve_etl_tariffs",
        rows=rows,
        changed=changed,
        last_page=last_page,
        exhausted=exhausted,
        start_page=start_page,
        max_pages=max_pages,
    )
    return rows, last_page, exhausted
