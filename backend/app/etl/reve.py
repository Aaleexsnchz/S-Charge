import enum
import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Any
from zoneinfo import available_timezones

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.etl.upsert import upsert
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
from app.utils.audit import audit
from app.utils.dates import parse_datetime

logger = logging.getLogger(__name__)

PAGE_SIZE = 100

# What each record has to carry before the mirror can hold it: `id` is the
# upsert key, and the rest back NOT NULL columns. REVE's own spec marks every
# one of them required and publishes records without them anyway, so a record
# that arrives incomplete is dropped rather than raised on. A raise loses far
# more than the record: the page rolls back, the cursor never advances past it,
# and the endpoint refetches the same page every tick until someone ships a fix.
CPO_REQUIRED = ("id", "party_id", "last_updated")
# `address` and `city` sit here rather than being read as optional: their
# columns are NOT NULL and `PointRead` publishes them as required, so a station
# without one cannot be mirrored without changing the API contract and every
# screen that renders it.
LOCATION_REQUIRED = ("id", "country_code", "address", "city", "last_updated")
COORDINATES_REQUIRED = ("latitude", "longitude")
EVSE_REQUIRED = ("id", "last_static_updated")
CONNECTOR_REQUIRED = (
    "id",
    "standard",
    "format",
    "power_type",
    "max_voltage",
    "max_amperage",
    "last_static_updated",
)
TARIFF_ROW_REQUIRED = ("evse_id", "connector_id")
TARIFF_REQUIRED = ("id", "currency", "last_tariff_updated")


class TariffOutcome(enum.StrEnum):
    """Why a tariff row did or did not reach a connector.

    The two failures are not interchangeable: an unmirrored connector is a
    catalogue gap the ledger repairs later, while a malformed row is a price
    that can never be stored, and the ledger must not bank the second as if it
    were the first.
    """

    STORED = "stored"
    UNMIRRORED = "unmirrored"
    MALFORMED = "malformed"


def _missing_fields(raw: dict[str, Any], required: tuple[str, ...]) -> list[str]:
    return [key for key in required if raw.get(key) is None]


def _decimal_or_none(value: str | float | None) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(str(value))


def _known_time_zone(value: str | None) -> str:
    """Fall back to Madrid for a zone Postgres would not recognise.

    The repricing statement resolves every connector in one `AT TIME ZONE`, so a
    single unknown zone from one REVE page would fail the whole recompute rather
    than mispricing one point. ``raw_data`` keeps what was published.
    """
    if not value:
        return "Europe/Madrid"
    if value not in available_timezones():
        logger.warning("reve_unknown_time_zone value=%s", value)
        return "Europe/Madrid"
    return value


def _bound(value: str | float | None) -> Decimal | None:
    """A restriction bound, with REVE's ``0`` placeholder read as "not set".

    A band capped at ``max_power = 0`` would match no connector at all, and one
    gated behind ``min_duration = 0`` is not gated. REVE emits zeros for both
    rather than omitting the field; ``raw_data`` keeps the literal source.
    """
    parsed = _decimal_or_none(value)
    return None if parsed == 0 else parsed


def _int_bound(value: float | None) -> int | None:
    """OCPI types these as numbers, so 1800.0 is legal and must not reach an int
    column as a float."""
    return int(value) if value else None


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

    OCPI makes ``elements`` and ``price_components`` arrays; a bare object is
    read as a one-item list.
    """
    rows: list[dict[str, Any]] = []
    for index, element in enumerate(_ensure_list(elements)):
        restrictions = element.get("restrictions") or {}
        raw_days = restrictions.get("day_of_week")
        days = raw_days if isinstance(raw_days, list) else _ensure_list(raw_days)
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
                    "step_size": _int_bound(component.get("step_size")),
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
    updated = parse_datetime(raw_tariff.get("last_tariff_updated"))
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
    on_page: Callable[[int, bool], Awaitable[None]] | None = None,
) -> tuple[int, int, bool]:
    """Fetch consecutive pages of REVE data, calling ``process_item`` per row.

    Returns ``(rows_processed, last_page_completed, exhausted)``. ``exhausted``
    is ``True`` when REVE returned a short page (< PAGE_SIZE), signalling no
    more data; the cursor in the caller can then stamp ``completed_at``.

    ``on_page`` is awaited after each page with ``(page, exhausted)`` and is
    where the caller commits. Progress has to be durable per page rather than
    per tick: a 429 or 504 on page five propagates out of here, so anything the
    caller meant to record afterwards is lost and the cycle restarts from the
    top — which under a 5-call hourly budget means a long cycle never finishes.
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
        exhausted = len(items) < PAGE_SIZE
        if on_page is not None:
            await on_page(page, exhausted)
        if exhausted:
            break
        page += 1

    return rows, last_page_completed, exhausted


async def _upsert_cpo(db: AsyncSession, raw: dict[str, Any]) -> bool:
    missing = _missing_fields(raw, CPO_REQUIRED)
    if missing:
        logger.warning(
            "reve_cpo_skipped source_id=%s party_id=%s missing=%s",
            raw.get("id"),
            raw.get("party_id"),
            ",".join(missing),
        )
        return False

    payload: dict[str, Any] = {
        "id": uuid.uuid4(),
        "source_id": raw["id"],
        "party_id": raw["party_id"],
        "cif": raw.get("cif"),
        "name": raw.get("name"),
        "address": raw.get("address"),
        "city": raw.get("city"),
        "city_code": raw.get("city_code"),
        "postal_code": raw.get("postal_code"),
        "region": raw.get("region"),
        "state": raw.get("state"),
        "country": raw.get("country"),
        "phone": raw.get("phone"),
        "website": raw.get("website"),
        "confirmed_at": parse_datetime(raw.get("confirmed_at")),
        "raw_data": raw,
        "source_last_updated_at": parse_datetime(raw["last_updated"]),
    }
    await db.execute(upsert(Cpo, payload, ["source_id"]))
    return True


async def _upsert_connector(
    db: AsyncSession,
    evse_pk: uuid.UUID,
    raw: dict[str, Any],
    evse_source_id: str,
) -> None:
    missing = _missing_fields(raw, CONNECTOR_REQUIRED)
    if missing:
        # The parent's id, because the field most likely to be missing is the
        # one that would have identified the record: `source_id=None` names
        # nothing, and REVE has been seen to drop it from every child at once.
        logger.warning(
            "reve_connector_skipped evse=%s source_id=%s missing=%s",
            evse_source_id,
            raw.get("id"),
            ",".join(missing),
        )
        return

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
        "source_last_updated_at": parse_datetime(raw["last_static_updated"]),
    }
    await db.execute(upsert(Connector, payload, ["evse_id", "source_id"]))


async def _upsert_evse(
    db: AsyncSession,
    charging_point_id: uuid.UUID,
    raw: dict[str, Any],
    location_source_id: str,
) -> None:
    missing = _missing_fields(raw, EVSE_REQUIRED)
    if missing:
        logger.warning(
            "reve_evse_skipped location=%s source_id=%s missing=%s",
            location_source_id,
            raw.get("id"),
            ",".join(missing),
        )
        return

    payload: dict[str, Any] = {
        "id": uuid.uuid4(),
        "charging_point_id": charging_point_id,
        "source_id": raw["id"],
        "evse_id": raw.get("evse_id"),
        "physical_reference": raw.get("physical_reference"),
        "floor_level": raw.get("floor_level"),
        "capabilities": raw.get("capabilities"),
        "wheelchair_accessibility": raw.get("accessibility"),
        "source_last_updated_at": parse_datetime(raw["last_static_updated"]),
    }
    stmt = upsert(Evse, payload, ["charging_point_id", "source_id"]).returning(Evse.id)
    evse_pk: uuid.UUID = (await db.execute(stmt)).scalar_one()

    for raw_conn in _ensure_list(raw.get("connectors")):
        await _upsert_connector(db, evse_pk, raw_conn, raw["id"])


async def _upsert_location(db: AsyncSession, raw: dict[str, Any]) -> bool:
    coords = raw.get("coordinates") or {}
    missing = _missing_fields(raw, LOCATION_REQUIRED) + _missing_fields(
        coords, COORDINATES_REQUIRED
    )
    if missing:
        logger.warning(
            "reve_location_skipped source_id=%s party_id=%s missing=%s",
            raw.get("id"),
            raw.get("party_id"),
            ",".join(missing),
        )
        return False

    opening_times = raw.get("opening_times") or {}

    payload: dict[str, Any] = {
        "id": uuid.uuid4(),
        "source": ChargingPointSource.REVE_SEED,
        "source_id": raw["id"],
        "name": raw.get("name"),
        "cpo_name": raw.get("cpo_name"),
        "party_id": raw.get("party_id"),
        "version": raw.get("version"),
        "address": raw.get("address"),
        "city": raw.get("city"),
        "postal_code": raw.get("postal_code"),
        "region": raw.get("region"),
        "state": raw.get("state"),
        "country_code": raw["country_code"],
        "latitude": Decimal(coords["latitude"]),
        "longitude": Decimal(coords["longitude"]),
        "parking_type": raw.get("parking_type"),
        "facilities": raw.get("facilities"),
        "time_zone": _known_time_zone(raw.get("time_zone")),
        "opening_24_7": opening_times.get("twentyfourseven", False),
        "opening_hours": opening_times.get("regular_hours"),
        "charging_when_closed": raw.get("charging_when_closed"),
        "directions": raw.get("directions"),
        "source_last_updated_at": parse_datetime(raw["last_updated"]),
        "archived_at": None,
    }

    stmt = upsert(ChargingPoint, payload, ["source", "source_id"]).returning(
        ChargingPoint.id
    )
    cp_id: uuid.UUID = (await db.execute(stmt)).scalar_one()

    for raw_evse in _ensure_list(raw.get("evses")):
        await _upsert_evse(db, cp_id, raw_evse, raw["id"])
    return True


async def _record_unmirrored(
    db: AsyncSession, raw: dict[str, Any], raw_tariff: dict[str, Any]
) -> None:
    """Keep a tariff whose connector the catalogue does not hold.

    The feed carries a tariff again only when its price next changes, often
    months later, so it is stored with the ids rather than dropped: the
    repair pass can then import the station priced instead of blank.
    """
    payload = {
        "id": uuid.uuid4(),
        "evse_id": raw["evse_id"],
        "connector_id": raw["connector_id"],
        "tariff_raw": raw_tariff,
        "last_seen_at": datetime.now(UTC),
    }
    await db.execute(
        upsert(ReveUnmirroredConnector, payload, ["evse_id", "connector_id"])
    )


async def _upsert_connector_tariff(
    db: AsyncSession,
    raw: dict[str, Any],
    refreshed_at: datetime,
    rewritten_tariffs: set[str],
) -> TariffOutcome:
    """Attach REVE's price to the connector it names.

    A row carrying no tariff object counts as ``STORED``: nothing to write and
    nothing left owing, which is the distinction the ledger acts on.
    """
    missing = _missing_fields(raw, TARIFF_ROW_REQUIRED)
    if missing:
        logger.warning(
            "reve_tariff_row_skipped connector_id=%s missing=%s",
            raw.get("connector_id"),
            ",".join(missing),
        )
        return TariffOutcome.MALFORMED

    raw_tariff = _first_tariff(raw)
    if raw_tariff is None:
        return TariffOutcome.STORED

    missing = _missing_fields(raw_tariff, TARIFF_REQUIRED)
    if missing:
        logger.warning(
            "reve_tariff_skipped source_id=%s connector_id=%s missing=%s",
            raw_tariff.get("id"),
            raw["connector_id"],
            ",".join(missing),
        )
        return TariffOutcome.MALFORMED

    connector_lookup = (
        select(Connector.id)
        .join(Evse, Connector.evse_id == Evse.id)
        .where(Evse.source_id == raw["evse_id"])
        .where(Connector.source_id == raw["connector_id"])
    )
    connector_pk = (await db.execute(connector_lookup)).scalar_one_or_none()
    if connector_pk is None:
        await _record_unmirrored(db, raw, raw_tariff)
        logger.warning(
            "reve_tariff_connector_not_found evse_id=%s connector_id=%s",
            raw["evse_id"],
            raw["connector_id"],
        )
        return TariffOutcome.UNMIRRORED

    tariff_payload: dict[str, Any] = {
        "id": uuid.uuid4(),
        "source_id": raw_tariff["id"],
        "currency": raw_tariff["currency"],
        "valid_from": parse_datetime(raw_tariff.get("start_date_time")),
        "valid_to": parse_datetime(raw_tariff.get("end_date_time")),
        "raw_data": raw_tariff,
        "source_last_updated_at": parse_datetime(raw_tariff["last_tariff_updated"]),
        "last_refreshed_at": refreshed_at,
    }
    stmt = upsert(Tariff, tariff_payload, ["source_id"]).returning(Tariff.id)
    tariff_pk: uuid.UUID = (await db.execute(stmt)).scalar_one()

    # One tariff is shared across many connectors, so a page of 100 rows would
    # otherwise delete and re-insert the same bands 100 times.
    if raw_tariff["id"] not in rewritten_tariffs:
        rewritten_tariffs.add(raw_tariff["id"])
        await db.execute(
            delete(TariffElement).where(TariffElement.tariff_id == tariff_pk)
        )
        element_rows = _element_rows(tariff_pk, raw_tariff.get("elements"))
        if element_rows:
            await db.execute(insert(TariffElement), element_rows)
        else:
            logger.warning(
                "reve_tariff_without_elements source_id=%s", raw_tariff["id"]
            )

    await db.execute(
        update(Connector)
        .where(Connector.id == connector_pk)
        .values(tariff_id=tariff_pk)
    )
    return TariffOutcome.STORED


async def seed_backlog_from_ledger(db: AsyncSession) -> int:
    """Price the backlog rows whose connector now exists, and drop them.

    Called after each `/locations` page, since a page that creates a station is
    when its banked tariff can finally be attached. Pricing and deleting share
    one transaction: a separate sweep of "rows whose connector exists" could
    delete a payload just before it was read, leaving the connector unpriced
    until its tariff next changes.
    """
    ready = (
        select(ReveUnmirroredConnector)
        .join(Evse, Evse.source_id == ReveUnmirroredConnector.evse_id)
        .join(
            Connector,
            (Connector.evse_id == Evse.id)
            & (Connector.source_id == ReveUnmirroredConnector.connector_id),
        )
    )
    entries = (await db.execute(ready)).scalars().all()
    if not entries:
        return 0

    refreshed_at = datetime.now(UTC)
    rewritten: set[str] = set()
    seeded = 0
    for entry in entries:
        # The ledger stores the inner tariff object; the upsert takes the outer
        # feed row, so the wrapper is rebuilt from the columns beside it.
        raw = {
            "evse_id": entry.evse_id,
            "connector_id": entry.connector_id,
            "tariffs": [entry.tariff_raw],
        }
        # A malformed banked tariff keeps its row rather than being dropped as
        # seeded: it can never be stored, and the backlog that stops falling is
        # the only thing that says so.
        if (
            await _upsert_connector_tariff(db, raw, refreshed_at, rewritten)
            is TariffOutcome.STORED
        ):
            await db.delete(entry)
            seeded += 1
    return seeded


async def _import_catalogue(
    client: ReveClient,
    db: AsyncSession,
    *,
    path: str,
    event: str,
    upsert_one: Callable[[AsyncSession, dict[str, Any]], Awaitable[bool]],
    date_from: datetime | None,
    date_to: datetime | None,
    start_page: int,
    max_pages: int | None,
    on_page: Callable[[int, bool], Awaitable[None]] | None,
) -> tuple[int, int, bool]:
    skipped = 0

    async def _process(raw: dict[str, Any]) -> None:
        nonlocal skipped
        if not await upsert_one(db, raw):
            skipped += 1

    rows, last_page, exhausted = await _paginate_with_budget(
        client,
        path,
        _window_params(date_from, date_to),
        _process,
        start_page=start_page,
        max_pages=max_pages,
        on_page=on_page,
    )
    audit(
        event,
        rows=rows,
        skipped=skipped,
        last_page=last_page,
        exhausted=exhausted,
        start_page=start_page,
        max_pages=max_pages,
    )
    return rows, last_page, exhausted


async def import_cpos(
    client: ReveClient,
    db: AsyncSession,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    start_page: int = 1,
    max_pages: int | None = None,
    on_page: Callable[[int, bool], Awaitable[None]] | None = None,
) -> tuple[int, int, bool]:
    return await _import_catalogue(
        client,
        db,
        path="/cpos",
        event="reve_etl_cpos",
        upsert_one=_upsert_cpo,
        date_from=date_from,
        date_to=date_to,
        start_page=start_page,
        max_pages=max_pages,
        on_page=on_page,
    )


async def import_locations(
    client: ReveClient,
    db: AsyncSession,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    start_page: int = 1,
    max_pages: int | None = None,
    on_page: Callable[[int, bool], Awaitable[None]] | None = None,
) -> tuple[int, int, bool]:
    return await _import_catalogue(
        client,
        db,
        path="/locations",
        event="reve_etl_locations",
        upsert_one=_upsert_location,
        date_from=date_from,
        date_to=date_to,
        start_page=start_page,
        max_pages=max_pages,
        on_page=on_page,
    )


async def import_tariffs(
    client: ReveClient,
    db: AsyncSession,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    start_page: int = 1,
    max_pages: int | None = None,
    on_page: Callable[[int, bool], Awaitable[None]] | None = None,
) -> tuple[int, int, bool]:
    refreshed_at = datetime.now(UTC)
    changed = 0
    unmirrored = 0
    skipped = 0
    rewritten_tariffs: set[str] = set()

    async def _process(raw: dict[str, Any]) -> None:
        nonlocal changed, unmirrored, skipped
        if _tariff_changed_in_window(raw, date_from, date_to):
            changed += 1
        outcome = await _upsert_connector_tariff(
            db, raw, refreshed_at, rewritten_tariffs
        )
        if outcome is TariffOutcome.UNMIRRORED:
            unmirrored += 1
        elif outcome is TariffOutcome.MALFORMED:
            skipped += 1

    rows, last_page, exhausted = await _paginate_with_budget(
        client,
        "/connectors/tariffs",
        _window_params(date_from, date_to),
        _process,
        start_page=start_page,
        max_pages=max_pages,
        on_page=on_page,
    )
    audit(
        "reve_etl_tariffs",
        rows=rows,
        changed=changed,
        unmirrored=unmirrored,
        skipped=skipped,
        last_page=last_page,
        exhausted=exhausted,
        start_page=start_page,
        max_pages=max_pages,
    )
    return rows, last_page, exhausted
