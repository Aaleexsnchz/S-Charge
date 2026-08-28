from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from app.etl.cursor import read_cursor
from app.etl.lock import reve_etl_lock
from app.integrations.reve import ReveClient
from app.models.etl import ReveEtlCursor
from pytest_httpx import HTTPXMock
from scripts.refresh_reve import (
    REFRESH_PRIORITY,
    _recovery_windows,
    _run_tick,
    _too_soon,
    main,
)
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

BASE_URL = "https://reve.test/api/v1"
API_KEY = "secret-key"


@pytest.fixture
def reve_client() -> ReveClient:
    return ReveClient(api_key=API_KEY, base_url=BASE_URL, max_retries=0)


@pytest.fixture
def main_uses_test_session(
    db_session: AsyncSession, engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Let ``main`` run against the test transaction.

    It opens its own ``SessionLocal``, so without this a test can only reach the
    branches that return before a session exists. The stand-in yields the test
    session and declines to close it, since the fixture owns its lifecycle.
    """

    class _Handle:
        async def __aenter__(self) -> AsyncSession:
            return db_session

        async def __aexit__(self, *exc: object) -> None:
            return None

    monkeypatch.setattr("scripts.refresh_reve.SessionLocal", lambda: _Handle())
    monkeypatch.setattr("scripts.refresh_reve.engine", engine)


async def _seed_tariff_cursor(db: AsyncSession, watermark: datetime) -> None:
    await db.execute(update(ReveEtlCursor).values(completed_at=watermark))
    await db.execute(
        update(ReveEtlCursor)
        .where(ReveEtlCursor.endpoint == "/connectors/tariffs")
        .values(refresh_watermark=watermark, refresh_cycle_end=None, next_page=1)
    )
    # Park the catalogue endpoints inside their intervals so a tariff test is
    # about tariffs. Prioritisation gets its own test.
    await db.execute(
        update(ReveEtlCursor)
        .where(ReveEtlCursor.endpoint != "/connectors/tariffs")
        .values(refresh_watermark=datetime.now(UTC), refresh_cycle_end=None)
    )
    await db.commit()


def _tariff_row() -> dict[str, Any]:
    return {"tariffs": None}


@pytest.mark.parametrize(
    "age",
    [timedelta(minutes=30), timedelta(hours=100), timedelta(days=45)],
    ids=["recent", "stale", "very-stale"],
)
async def test_504_never_moves_the_watermark(
    reve_client: ReveClient,
    db_session: AsyncSession,
    httpx_mock: HTTPXMock,
    age: timedelta,
) -> None:
    """Whatever its age, a 504 leaves the position recoverable.

    The endpoint has no ``date_to``, so a watermark advanced past a window that
    was never served cannot be aimed back at it.
    """
    watermark = datetime.now(UTC) - age
    await _seed_tariff_cursor(db_session, watermark)
    # Every rung of the recovery ladder fails, including the unfiltered floor.
    httpx_mock.add_response(status_code=504, is_reusable=True)

    async with reve_client as client:
        exit_code = await _run_tick(db_session, client, budget=5)

    assert exit_code == 0
    cursor = await read_cursor(db_session, "/connectors/tariffs")
    assert cursor.refresh_watermark == watermark
    assert cursor.last_error is not None


async def test_date_from_override_aims_the_window(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    """A probe names its own window without writing the cursor to get one."""
    watermark = datetime.now(UTC) - timedelta(days=45)
    await _seed_tariff_cursor(db_session, watermark)
    override = datetime(2026, 7, 8, 19, 30, 3, tzinfo=UTC)
    httpx_mock.add_response(json=[])

    async with reve_client as client:
        await _run_tick(db_session, client, budget=1, date_from_override=override)

    sent = httpx_mock.get_requests()[0].url
    assert sent.params["date_from"] == override.isoformat()


async def test_drain_advances_watermark_to_now(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    watermark = datetime.now(UTC) - timedelta(minutes=90)
    await _seed_tariff_cursor(db_session, watermark)
    httpx_mock.add_response(json=[])

    async with reve_client as client:
        exit_code = await _run_tick(db_session, client, budget=5)

    assert exit_code == 0
    cursor = await read_cursor(db_session, "/connectors/tariffs")
    assert cursor.refresh_cycle_end is None
    assert cursor.next_page == 1
    assert cursor.refresh_watermark is not None
    assert cursor.refresh_watermark >= datetime.now(UTC) - timedelta(minutes=2)


async def test_budget_exhausted_mid_pagination_resumes(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    watermark = datetime.now(UTC) - timedelta(minutes=90)
    await _seed_tariff_cursor(db_session, watermark)
    httpx_mock.add_response(json=[_tariff_row() for _ in range(100)])

    async with reve_client as client:
        exit_code = await _run_tick(db_session, client, budget=1)

    assert exit_code == 0
    cursor = await read_cursor(db_session, "/connectors/tariffs")
    assert cursor.next_page == 2
    assert cursor.refresh_cycle_end is not None
    assert cursor.refresh_watermark == watermark


async def test_rate_limit_stops_without_change(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    watermark = datetime.now(UTC) - timedelta(hours=100)
    await _seed_tariff_cursor(db_session, watermark)
    httpx_mock.add_response(status_code=429, headers={"Retry-After": "0"})

    async with reve_client as client:
        exit_code = await _run_tick(db_session, client, budget=5)

    assert exit_code == 0
    cursor = await read_cursor(db_session, "/connectors/tariffs")
    assert cursor.refresh_watermark == watermark


async def test_unexpected_error_surfaces_exit_1(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    watermark = datetime.now(UTC) - timedelta(minutes=90)
    await _seed_tariff_cursor(db_session, watermark)
    httpx_mock.add_response(status_code=500)

    async with reve_client as client:
        exit_code = await _run_tick(db_session, client, budget=5)

    assert exit_code == 1
    cursor = await read_cursor(db_session, "/connectors/tariffs")
    assert cursor.refresh_watermark == watermark
    assert cursor.last_error is not None


async def test_a_second_runner_exits_without_writing(
    db_session: AsyncSession,
    httpx_mock: HTTPXMock,
    engine: AsyncEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The lock is what makes "stop the scheduler first" unnecessary.

    Patching the module's engine keeps the injection out of ``main``'s
    signature; with the lock already held it returns before opening a session,
    so no application database is touched.
    """
    monkeypatch.setattr("scripts.refresh_reve.engine", engine)
    watermark = datetime.now(UTC) - timedelta(days=45)
    await _seed_tariff_cursor(db_session, watermark)

    async with reve_etl_lock(engine) as held:
        assert held is True
        exit_code = await main([])

    assert exit_code == 0
    assert httpx_mock.get_requests() == []
    cursor = await read_cursor(db_session, "/connectors/tariffs")
    assert cursor.refresh_watermark == watermark


async def test_restart_cycle_rewinds_to_page_one_without_moving_the_window(
    db_session: AsyncSession, main_uses_test_session: None
) -> None:
    """Pages already drained are unreachable any other way: the endpoint has no
    `date_to`, and a completed cycle moves the watermark past them for good."""
    watermark = datetime(2026, 7, 8, 19, 30, tzinfo=UTC)
    cycle_end = datetime(2026, 8, 23, 9, 12, tzinfo=UTC)
    await _seed_tariff_cursor(db_session, watermark)
    await db_session.execute(
        update(ReveEtlCursor)
        .where(ReveEtlCursor.endpoint == "/connectors/tariffs")
        .values(next_page=19, refresh_cycle_end=cycle_end)
    )

    assert await main(["--restart-cycle"]) == 0

    cursor = await read_cursor(db_session, "/connectors/tariffs")
    assert cursor.next_page == 1
    # The window must not shift, or the re-read covers a different result set.
    assert cursor.refresh_cycle_end == cycle_end
    assert cursor.refresh_watermark == watermark


async def test_restart_cycle_refuses_when_no_cycle_is_in_flight(
    db_session: AsyncSession, main_uses_test_session: None
) -> None:
    await _seed_tariff_cursor(db_session, datetime(2026, 7, 8, 19, 30, tzinfo=UTC))

    assert await main(["--restart-cycle"]) == 1


async def test_a_504_widens_the_window_rather_than_skipping_it(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    """Measured 2026-08-24: `date_from=09:00:04` failed 27 times running while
    `08:00:05`, an hour wider and containing it, succeeded every time. So a 504
    means *this window* was not served, not that the changes are gone — and the
    answer is to ask for more, never to step over the gap."""
    watermark = datetime(2026, 8, 24, 9, 0, 4, tzinfo=UTC)
    last_good = watermark - timedelta(hours=1)
    await _seed_tariff_cursor(db_session, watermark)
    await db_session.execute(
        update(ReveEtlCursor)
        .where(ReveEtlCursor.endpoint == "/connectors/tariffs")
        .values(last_good_date_from=last_good)
    )
    await db_session.commit()

    # Responses are matched in registration order: the watermark's window is
    # refused, the wider one behind it is served.
    httpx_mock.add_response(status_code=504)
    httpx_mock.add_response(json=[_tariff_row()])

    async with reve_client as client:
        assert await _run_tick(db_session, client, budget=5) == 0

    cursor = await read_cursor(db_session, "/connectors/tariffs")
    # The cycle drained on the wider window, so the watermark moves forward past
    # the value that could not be served - without the gap being skipped.
    assert cursor.refresh_watermark is not None
    assert cursor.refresh_watermark > watermark
    assert cursor.last_good_date_from == last_good
    assert cursor.last_error is None


async def test_a_rate_limit_keeps_the_pages_already_fetched(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    """A cycle longer than one hour's budget could never finish otherwise: the
    429 propagated before progress was written, so every run restarted at page
    one and re-spent the same calls."""
    watermark = datetime(2026, 8, 24, 9, 0, 4, tzinfo=UTC)
    await _seed_tariff_cursor(db_session, watermark)

    httpx_mock.add_response(json=[_tariff_row() for _ in range(100)])
    httpx_mock.add_response(json=[_tariff_row() for _ in range(100)])
    httpx_mock.add_response(status_code=429)

    async with reve_client as client:
        assert await _run_tick(db_session, client, budget=5) == 0

    cursor = await read_cursor(db_session, "/connectors/tariffs")
    assert cursor.next_page == 3, "the two full pages must survive the rate limit"
    # Mid-cycle the watermark tracks the window being paginated, so the next
    # tick resumes against the same result set.
    assert cursor.refresh_watermark == watermark
    assert cursor.refresh_cycle_end is not None


async def test_prices_take_the_budget_before_the_catalogue(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    """The catalogue catch-up is 68+ pages. If it could take the budget first,
    prices would go unrefreshed for a day and a half - so order is priority and
    each target gets only what the ones above it left."""
    await _seed_tariff_cursor(db_session, datetime(2026, 8, 24, 9, 0, tzinfo=UTC))
    # Tariffs keep asking for more, so nothing is left for anyone else.
    httpx_mock.add_response(json=[_tariff_row() for _ in range(100)], is_reusable=True)

    async with reve_client as client:
        assert await _run_tick(db_session, client, budget=3) == 0

    for request in httpx_mock.get_requests():
        assert "/connectors/tariffs" in str(request.url), (
            "the catalogue must not get a call while prices still want them"
        )


async def test_cpos_is_left_alone_between_intervals(db_session: AsyncSession) -> None:
    """142 CPOs, one changed in June and one in March. A call an hour would be
    24 a day spent discovering nothing."""
    now = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)
    cursor = await read_cursor(db_session, "/cpos")
    cursor.refresh_watermark = now - timedelta(hours=2)
    cursor.refresh_cycle_end = None
    target = next(t for t in REFRESH_PRIORITY if t.endpoint == "/cpos")

    assert _too_soon(target, cursor, now) is True

    cursor.refresh_watermark = now - timedelta(days=2)
    assert _too_soon(target, cursor, now) is False


async def test_an_in_flight_cycle_is_never_left_alone(db_session: AsyncSession) -> None:
    """Or a long drain would be abandoned halfway every time the interval passed."""
    now = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)
    cursor = await read_cursor(db_session, "/cpos")
    cursor.refresh_watermark = now - timedelta(hours=2)
    cursor.refresh_cycle_end = now - timedelta(hours=1)
    target = next(t for t in REFRESH_PRIORITY if t.endpoint == "/cpos")

    assert _too_soon(target, cursor, now) is False


async def test_widening_reaches_back_when_the_remembered_window_also_fails(
    reve_client: ReveClient, db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    """Measured 2026-08-26: REVE's filtered path degraded and every recent window
    timed out, the remembered one included — it is recent by construction. Only
    reaching much further back answered, so the schedule has to escalate rather
    than recall."""
    watermark = datetime(2026, 8, 26, 8, 0, 3, tzinfo=UTC)
    last_good = watermark - timedelta(hours=1)
    await _seed_tariff_cursor(db_session, watermark)
    await db_session.execute(
        update(ReveEtlCursor)
        .where(ReveEtlCursor.endpoint == "/connectors/tariffs")
        .values(last_good_date_from=last_good)
    )
    await db_session.commit()

    # watermark, the remembered window, -1d and -7d all refused; -30d answers.
    for _ in range(4):
        httpx_mock.add_response(status_code=504)
    httpx_mock.add_response(json=[_tariff_row()])

    async with reve_client as client:
        assert await _run_tick(db_session, client, budget=5) == 0

    served = httpx_mock.get_requests()[-1].url.params["date_from"]
    assert datetime.fromisoformat(served) == watermark - timedelta(days=30)

    cursor = await read_cursor(db_session, "/connectors/tariffs")
    assert cursor.last_error is None


async def test_a_standing_failure_stops_rebuying_known_bad_rungs(
    db_session: AsyncSession,
) -> None:
    """A rung that failed last tick fails this tick too. Re-paying a call an hour
    to rediscover that is how the ladder spent 21 attempts going nowhere."""
    watermark = datetime(2026, 8, 26, 8, 0, 3, tzinfo=UTC)
    await _seed_tariff_cursor(db_session, watermark)
    cursor = await read_cursor(db_session, "/connectors/tariffs")
    cursor.last_good_date_from = watermark - timedelta(hours=1)

    cursor.consecutive_failures = 0
    assert _recovery_windows(watermark, cursor)[0] == watermark

    cursor.consecutive_failures = 2
    assert _recovery_windows(watermark, cursor)[0] == watermark - timedelta(days=1)

    # However long it has been failing, one rung always survives.
    cursor.consecutive_failures = 99
    assert len(_recovery_windows(watermark, cursor)) == 1
