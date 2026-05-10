from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.etl.cursor import (
    read_all_cursors,
    read_cursor,
    record_error,
    record_progress,
)


async def test_read_cursor_returns_seeded_row(db_session: AsyncSession) -> None:
    cursor = await read_cursor(db_session, "/cpos")

    assert cursor.endpoint == "/cpos"
    assert cursor.next_page == 1
    assert cursor.completed_at is None
    assert cursor.last_attempted_at is None
    assert cursor.last_error is None


async def test_read_all_cursors_returns_four_rows(db_session: AsyncSession) -> None:
    cursors = await read_all_cursors(db_session)

    endpoints = sorted(c.endpoint for c in cursors)
    assert endpoints == [
        "/connectors/tariffs",
        "/cpos",
        "/evses/operational_status",
        "/locations",
    ]


async def test_record_progress_advances_next_page(db_session: AsyncSession) -> None:
    now = datetime(2026, 5, 10, 18, 0, tzinfo=UTC)

    await record_progress(db_session, "/cpos", next_page=3, exhausted=False, attempted_at=now)
    cursor = await read_cursor(db_session, "/cpos")

    assert cursor.next_page == 3
    assert cursor.last_attempted_at == now
    assert cursor.completed_at is None
    assert cursor.last_error is None


async def test_record_progress_with_exhausted_sets_completed_at(
    db_session: AsyncSession,
) -> None:
    now = datetime(2026, 5, 10, 18, 0, tzinfo=UTC)

    await record_progress(db_session, "/cpos", next_page=4, exhausted=True, attempted_at=now)
    cursor = await read_cursor(db_session, "/cpos")

    assert cursor.next_page == 4
    assert cursor.completed_at == now


async def test_record_progress_clears_previous_error(db_session: AsyncSession) -> None:
    await record_error(db_session, "/cpos", "boom")
    await record_progress(db_session, "/cpos", next_page=2, exhausted=False)
    cursor = await read_cursor(db_session, "/cpos")

    assert cursor.last_error is None


async def test_record_error_sets_error_without_advancing_page(
    db_session: AsyncSession,
) -> None:
    now = datetime(2026, 5, 10, 18, 0, tzinfo=UTC)

    await record_error(db_session, "/cpos", "connection refused", attempted_at=now)
    cursor = await read_cursor(db_session, "/cpos")

    assert cursor.next_page == 1
    assert cursor.last_error == "connection refused"
    assert cursor.last_attempted_at == now
    assert cursor.completed_at is None
