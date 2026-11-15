from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.etl import ReveEtlCursor


async def read_cursor(db: AsyncSession, endpoint: str) -> ReveEtlCursor:
    return (
        await db.execute(
            select(ReveEtlCursor).where(ReveEtlCursor.endpoint == endpoint)
        )
    ).scalar_one()


async def read_all_cursors(db: AsyncSession) -> Sequence[ReveEtlCursor]:
    return (
        (await db.execute(select(ReveEtlCursor).order_by(ReveEtlCursor.endpoint)))
        .scalars()
        .all()
    )


async def record_progress(
    db: AsyncSession,
    endpoint: str,
    *,
    next_page: int,
    exhausted: bool,
    attempted_at: datetime | None = None,
) -> None:
    now = attempted_at or datetime.now(UTC)
    values: dict[str, object] = {
        "next_page": next_page,
        "last_attempted_at": now,
        "last_error": None,
    }
    if exhausted:
        values["completed_at"] = now
    await db.execute(
        update(ReveEtlCursor).where(ReveEtlCursor.endpoint == endpoint).values(**values)
    )


async def record_refresh_progress(
    db: AsyncSession,
    endpoint: str,
    *,
    next_page: int,
    cycle_end: datetime,
    exhausted: bool,
    window_start: datetime | None = None,
    attempted_at: datetime | None = None,
) -> None:
    """Persist progress of a post-seed incremental refresh cycle.

    While a cycle is mid-flight, ``refresh_cycle_end`` keeps its frozen upper
    bound so pagination stays stable across ticks. When the cycle drains
    (a short page), the watermark advances to that bound and paging resets.

    Called after every page rather than once per tick, so a tick that dies
    partway keeps the pages it already fetched; restarting the cycle instead
    could never finish a long drain under a 5-call hourly budget.
    """
    now = attempted_at or datetime.now(UTC)
    values: dict[str, object] = {
        "last_attempted_at": now,
        "last_error": None,
        "failing_since": None,
        "consecutive_failures": 0,
    }
    if window_start is not None:
        values["last_good_date_from"] = window_start
    if exhausted:
        values["refresh_watermark"] = cycle_end
        values["refresh_cycle_end"] = None
        values["next_page"] = 1
    else:
        values["refresh_cycle_end"] = cycle_end
        values["next_page"] = next_page
        if window_start is not None:
            # Mid-cycle the watermark *is* the window being paginated, so the
            # next tick resumes against the same result set. Moving it
            # backwards is lossless: it can only cause a re-fetch.
            values["refresh_watermark"] = window_start
    await db.execute(
        update(ReveEtlCursor).where(ReveEtlCursor.endpoint == endpoint).values(**values)
    )


async def record_error(
    db: AsyncSession,
    endpoint: str,
    error: str,
    *,
    attempted_at: datetime | None = None,
) -> None:
    """Record a failed attempt, opening a failure streak if none is open."""
    now = attempted_at or datetime.now(UTC)
    await db.execute(
        update(ReveEtlCursor)
        .where(ReveEtlCursor.endpoint == endpoint)
        .values(
            last_attempted_at=now,
            last_error=error,
            # coalesce, not now: the streak keeps the instant it began, so the
            # age of the stall is readable rather than resetting every tick.
            failing_since=func.coalesce(ReveEtlCursor.failing_since, now),
            consecutive_failures=ReveEtlCursor.consecutive_failures + 1,
        )
    )
