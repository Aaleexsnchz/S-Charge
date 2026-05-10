from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.etl import ReveEtlCursor


async def read_cursor(db: AsyncSession, endpoint: str) -> ReveEtlCursor:
    cursor = (
        await db.execute(select(ReveEtlCursor).where(ReveEtlCursor.endpoint == endpoint))
    ).scalar_one()
    return cursor


async def read_all_cursors(db: AsyncSession) -> Sequence[ReveEtlCursor]:
    cursors = (
        (await db.execute(select(ReveEtlCursor).order_by(ReveEtlCursor.endpoint))).scalars().all()
    )
    return cursors


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
