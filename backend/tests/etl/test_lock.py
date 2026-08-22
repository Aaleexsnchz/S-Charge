import pytest
from app.etl.lock import REVE_ETL_LOCK_KEY, reve_etl_lock
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def test_second_holder_is_refused_while_the_first_runs(
    engine: AsyncEngine,
) -> None:
    async with reve_etl_lock(engine) as first:
        assert first is True
        async with reve_etl_lock(engine) as second:
            assert second is False


async def test_the_lock_is_released_when_the_block_exits(engine: AsyncEngine) -> None:
    async with reve_etl_lock(engine) as acquired:
        assert acquired is True

    async with reve_etl_lock(engine) as again:
        assert again is True


async def test_the_lock_is_released_even_when_the_block_raises(
    engine: AsyncEngine,
) -> None:
    with pytest.raises(RuntimeError):
        async with reve_etl_lock(engine) as acquired:
            assert acquired is True
            raise RuntimeError("tick blew up")

    async with reve_etl_lock(engine) as again:
        assert again is True


async def test_no_advisory_lock_leaks_into_the_pool(engine: AsyncEngine) -> None:
    """A pooled connection is not closed, so an unreleased lock would persist."""
    async with reve_etl_lock(engine):
        pass

    async with engine.connect() as conn:
        held = (
            await conn.execute(
                text(
                    "SELECT count(*) FROM pg_locks "
                    "WHERE locktype = 'advisory' AND objid = :key"
                ),
                {"key": REVE_ETL_LOCK_KEY % 2**32},
            )
        ).scalar()
    assert held == 0
