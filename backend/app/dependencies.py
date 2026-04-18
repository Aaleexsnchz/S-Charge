from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SessionLocal


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
