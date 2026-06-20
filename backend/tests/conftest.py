import asyncio
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from unittest.mock import AsyncMock, patch
from urllib.parse import urlparse, urlunparse

import asyncpg
import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from app.config import settings
from app.dependencies import get_db
from app.main import app
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

ALEMBIC_CFG_PATH = Path(__file__).resolve().parents[1] / "alembic.ini"


def _admin_dsn_and_db_name(async_url: str) -> tuple[str, str]:
    parsed = urlparse(async_url.replace("+asyncpg", ""))
    db_name = parsed.path.lstrip("/")
    admin_dsn = urlunparse(parsed._replace(path="/postgres"))
    return admin_dsn, db_name


@pytest_asyncio.fixture(scope="session")
async def _test_database() -> AsyncIterator[None]:
    admin_dsn, db_name = _admin_dsn_and_db_name(settings.test_database_url)

    conn = await asyncpg.connect(admin_dsn)
    try:
        await conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        await conn.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        await conn.close()

    yield

    conn = await asyncpg.connect(admin_dsn)
    try:
        await conn.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = $1 AND pid <> pg_backend_pid()",
            db_name,
        )
        await conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
    finally:
        await conn.close()


def _run_migrations() -> None:
    cfg = Config(str(ALEMBIC_CFG_PATH))
    cfg.set_main_option("sqlalchemy.url", settings.test_database_url)
    command.upgrade(cfg, "head")


@pytest_asyncio.fixture(scope="session")
async def engine(_test_database: None) -> AsyncIterator[AsyncEngine]:
    await asyncio.to_thread(_run_migrations)

    engine = create_async_engine(settings.test_database_url, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def db_session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()


@pytest.fixture(autouse=True)
def _mock_outbound_emails() -> Iterator[None]:
    """Auto-mock outbound email sends so tests never hit Resend.

    Tests that need to assert on or capture the verification / reset token
    should add their own fixture that re-patches the same targets and yields
    the mock instance — that patch will sit on top of this one and win.
    """
    with (
        patch(
            "app.services.user_manager.send_verification_email",
            new_callable=AsyncMock,
        ),
        patch(
            "app.services.user_manager.send_reset_password_email",
            new_callable=AsyncMock,
        ),
    ):
        yield


@pytest_asyncio.fixture(loop_scope="session")
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="https://test"
        ) as http_client:
            yield http_client
    finally:
        app.dependency_overrides.clear()
