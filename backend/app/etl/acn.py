import uuid
from datetime import datetime
from decimal import Decimal
from email.utils import parsedate_to_datetime
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.acn import AcnClient
from app.models.acn import AcnSession
from app.utils.audit import audit


def _parse_acn_dt(value: str | None) -> datetime | None:
    """ACN serialises datetimes as RFC 1123 strings in GMT."""
    if not value:
        return None
    return parsedate_to_datetime(value)


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(str(value))


def _latest_user_input(raw: dict[str, Any]) -> dict[str, Any]:
    """``userInputs`` is a list of revisions; the last entry is the current one."""
    inputs = raw.get("userInputs")
    if isinstance(inputs, list) and inputs:
        last = inputs[-1]
        if isinstance(last, dict):
            return last
    return {}


async def _upsert_session(db: AsyncSession, site: str, raw: dict[str, Any]) -> None:
    user_input = _latest_user_input(raw)
    payload: dict[str, Any] = {
        "id": uuid.uuid4(),
        "source_id": raw["_id"],
        "session_id": raw.get("sessionID"),
        "site": site,
        "station_id": raw.get("stationID"),
        "space_id": raw.get("spaceID"),
        "cluster_id": raw.get("clusterID"),
        "connection_time": _parse_acn_dt(raw["connectionTime"]),
        "disconnect_time": _parse_acn_dt(raw.get("disconnectTime")),
        "done_charging_time": _parse_acn_dt(raw.get("doneChargingTime")),
        "kwh_delivered": _decimal_or_none(raw.get("kWhDelivered")),
        "time_zone": raw.get("timezone"),
        "user_id": raw.get("userID"),
        "kwh_requested": _decimal_or_none(user_input.get("kWhRequested")),
        "minutes_available": user_input.get("minutesAvailable"),
        "requested_departure": _parse_acn_dt(user_input.get("requestedDeparture")),
        "raw_data": raw,
    }
    stmt = insert(AcnSession).values(**payload)
    stmt = stmt.on_conflict_do_update(
        index_elements=["source_id"],
        set_={k: stmt.excluded[k] for k in payload if k not in ("id", "source_id")},
    )
    await db.execute(stmt)


async def import_acn_sessions(
    client: AcnClient,
    db: AsyncSession,
    site: str,
    *,
    start_page: int = 1,
    max_pages: int | None = None,
    per_page: int = 250,
) -> tuple[int, int, bool]:
    """Import consecutive pages of ACN sessions for ``site``.

    Returns ``(rows, last_page_completed, exhausted)`` — the same contract as
    the REVE ETL functions. The caller owns the transaction.
    """
    rows = 0
    last_page_completed = start_page - 1
    exhausted = False
    pages_fetched = 0
    page = start_page

    while True:
        if max_pages is not None and pages_fetched >= max_pages:
            break
        items, total_pages = await client.get_sessions(site, page=page, per_page=per_page)
        for item in items:
            await _upsert_session(db, site, item)
            rows += 1
        last_page_completed = page
        pages_fetched += 1
        if not items or len(items) < per_page or (total_pages is not None and page >= total_pages):
            exhausted = True
            break
        page += 1

    audit(
        "acn_etl_sessions",
        site=site,
        rows=rows,
        last_page=last_page_completed,
        exhausted=exhausted,
        start_page=start_page,
    )
    return rows, last_page_completed, exhausted
