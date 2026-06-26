from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select, update
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
    attempted_at: datetime | None = None,
) -> None:
    """Persist progress of a post-seed incremental refresh cycle.

    While a cycle is mid-flight, ``refresh_cycle_end`` keeps its frozen upper
    bound so pagination stays stable across ticks. When the cycle drains
    (a short page), the watermark advances to that bound and paging resets.
    """
    now = attempted_at or datetime.now(UTC)
    values: dict[str, object] = {"last_attempted_at": now, "last_error": None}
    if exhausted:
        values["refresh_watermark"] = cycle_end
        values["refresh_cycle_end"] = None
        values["next_page"] = 1
    else:
        values["refresh_cycle_end"] = cycle_end
        values["next_page"] = next_page
    await db.execute(
        update(ReveEtlCursor).where(ReveEtlCursor.endpoint == endpoint).values(**values)
    )


async def skip_refresh_window(
    db: AsyncSession,
    endpoint: str,
    *,
    new_watermark: datetime,
    error: str,
    attempted_at: datetime | None = None,
) -> None:
    """Advance the watermark past a window that failed with a server error.

    The skipped window's upper bound becomes the new watermark and the cycle is
    reset, so the next window starts fresh from there. ``last_error`` keeps the
    error until the next successful drain clears it.
    """
    now = attempted_at or datetime.now(UTC)
    await db.execute(
        update(ReveEtlCursor)
        .where(ReveEtlCursor.endpoint == endpoint)
        .values(
            refresh_watermark=new_watermark,
            refresh_cycle_end=None,
            next_page=1,
            last_attempted_at=now,
            last_error=error,
        )
    )


async def record_error(
    db: AsyncSession,
    endpoint: str,
    error: str,
    *,
    attempted_at: datetime | None = None,
) -> None:
    now = attempted_at or datetime.now(UTC)
    await db.execute(
        update(ReveEtlCursor)
        .where(ReveEtlCursor.endpoint == endpoint)
        .values(last_attempted_at=now, last_error=error)
    )
