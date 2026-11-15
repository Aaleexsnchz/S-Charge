from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

# Arbitrary but fixed. Advisory locks share one namespace per database, so this
# only has to differ from every other key the application takes.
REVE_ETL_LOCK_KEY = 4_820_133_071


@asynccontextmanager
async def reve_etl_lock(engine: AsyncEngine) -> AsyncIterator[bool]:
    """Hold the REVE ETL lock for the duration of the block, if it is free.

    Yields whether the lock was taken; a caller that gets ``False`` must not
    touch ``reve_etl_cursor``. That row is read-modify-written every tick, and
    two writers corrupt the refresh watermark.

    The lock lives on its own connection, not the caller's session: a session
    returns its connection to the pool on commit, so a lock taken through it
    would stay with whichever pooled connection took it while later statements
    ran on another.
    """
    async with engine.connect() as conn:
        acquired = bool(
            (
                await conn.execute(
                    text("SELECT pg_try_advisory_lock(:key)"),
                    {"key": REVE_ETL_LOCK_KEY},
                )
            ).scalar()
        )
        try:
            yield acquired
        finally:
            if acquired:
                # Returning the connection to the pool does not end the backend
                # session, so the lock outlives the block unless it is dropped.
                await conn.execute(
                    text("SELECT pg_advisory_unlock(:key)"),
                    {"key": REVE_ETL_LOCK_KEY},
                )
