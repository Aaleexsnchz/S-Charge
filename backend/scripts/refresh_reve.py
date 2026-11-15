"""Post-seed incremental refresh of the REVE catalogue.

Runs on the same hourly, budgeted cron as ``seed_reve`` once the initial seed is
complete. Each tick spends its call budget down ``REFRESH_PRIORITY``: tariffs
first, because prices are what the app serves, then CPOs and locations on
whatever budget is left, each throttled by its own minimum interval.

Every endpoint takes only ``date_from`` (plus ``page``/``limit``), with **no
``date_to``**, and returns everything changed since that instant. A tick
paginates from the watermark, across ticks if the budget runs out, and on a full
drain advances the watermark to the moment the cycle started.

A watermark that has fallen far behind makes REVE return too much and the
gateway times out (504); with no ``date_to`` the range cannot be sliced. **A 504
never moves the watermark**: skipping ahead would silently lose the changes in
between, while a stall is visible in ``last_error`` and an operator can
intervene with ``--date-from``.

A ``429`` stops the tick to resume next time. ``ReveClient(max_retries=0)``: a
504 is not worth an immediate retry under a 5-call/hour budget.
"""

import argparse
import asyncio
import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.config import settings
from app.database import SessionLocal, engine
from app.etl.cursor import (
    read_all_cursors,
    read_cursor,
    record_error,
    record_refresh_progress,
)
from app.etl.lock import reve_etl_lock
from app.etl.reve import (
    import_cpos,
    import_locations,
    import_tariffs,
    seed_backlog_from_ledger,
)
from app.integrations.reve import ReveClient, is_rate_limit, is_server_error
from app.models.etl import ReveEtlCursor, ReveUnmirroredConnector
from app.services.tariff_pricing import recompute_connector_prices
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_BUDGET_PER_RUN = settings.reve_budget_per_run

# How much further back each failed attempt reaches. Geometric because the
# cost of a filtered window falls off with its width, so small increments buy
# nothing: 36 hours and 7 days fail alike when 30 days is what answers.
WIDENING_STEPS = (
    timedelta(days=1),
    timedelta(days=7),
    timedelta(days=30),
    timedelta(days=90),
)

TARIFFS_ENDPOINT = "/connectors/tariffs"
CPOS_ENDPOINT = "/cpos"
LOCATIONS_ENDPOINT = "/locations"

ImportFn = Callable[..., Awaitable[tuple[int, int, bool]]]


@dataclass(frozen=True)
class RefreshTarget:
    endpoint: str
    import_fn: ImportFn
    # Retry a 504 against the last window REVE served. Only the tariff feed has
    # been seen to refuse a window it had just served a superset of.
    recover: bool = False
    # Leave the endpoint alone while its last cycle is younger than this.
    min_interval: timedelta | None = None
    # Seed backlog rows whose connector each page brings into existence.
    consumes_backlog: bool = False


# Order is priority, and the budget loop below gives each target only what the
# ones above it left. Prices are first because they are what the app serves; the
# catalogue is a 68+ page catch-up that must never be able to starve them, and on
# leftover budget it costs about two calls a day once caught up.
REFRESH_PRIORITY: list[RefreshTarget] = [
    RefreshTarget(TARIFFS_ENDPOINT, import_tariffs, recover=True),
    # 142 CPOs, of which one changed in June and one in March. A call an hour
    # would be 24 a day to discover nothing; the foreign key from
    # charging_points only needs it to be roughly current.
    RefreshTarget(CPOS_ENDPOINT, import_cpos, min_interval=timedelta(days=1)),
    # Never unfiltered: `date_from` is a poor filter over 77 days (>6,800 of
    # 13,654 locations) but an excellent one over a day and a half (~125), and
    # the steady state is the latter.
    RefreshTarget(
        LOCATIONS_ENDPOINT,
        import_locations,
        consumes_backlog=True,
        # ~88 locations change a day, so an hourly window holds about four -
        # a whole call for a twentieth of a page. Six hours fills more of one.
        # The interval never applies mid-cycle, so the catch-up still runs
        # every tick until it drains.
        min_interval=timedelta(hours=6),
    ),
]


def _ago(when: datetime | None, now: datetime) -> str:
    if when is None:
        return "—"
    days = (now - when).days
    stamp = when.strftime("%Y-%m-%d %H:%M:%SZ")
    if days >= 1:
        return f"{stamp}   ({days} day{'s' if days != 1 else ''} ago)"
    hours = int((now - when).total_seconds() // 3600)
    return f"{stamp}   ({hours}h ago)" if hours else f"{stamp}   (just now)"


def _one_line(error: str | None) -> str:
    """REVE's 504 body spans two lines and a URL; a table cannot hold it."""
    if not error:
        return "—"
    first = error.strip().splitlines()[0]
    return first if len(first) <= 110 else f"{first[:107]}..."


async def _print_status(db: AsyncSession) -> int:
    now = datetime.now(UTC)
    backlog = await db.scalar(select(func.count()).select_from(ReveUnmirroredConnector))
    print(f"\ncatalogue backlog   {backlog} connector(s) REVE serves and we do not")
    for c in await read_all_cursors(db):
        streak = _ago(c.failing_since, now)
        if c.failing_since is not None:
            plural = "s" if c.consecutive_failures != 1 else ""
            streak = f"{streak[:-1]}, {c.consecutive_failures} failure{plural})"
        print(f"\n{c.endpoint}")
        print(f"  watermark        {_ago(c.refresh_watermark, now)}")
        print(f"  next page        {c.next_page}")
        print(f"  cycle end        {_ago(c.refresh_cycle_end, now)}")
        print(f"  last attempt     {_ago(c.last_attempted_at, now)}")
        print(f"  failing since    {streak}")
        print(f"  last error       {_one_line(c.last_error)}")
    print()
    return 0


def _too_soon(target: RefreshTarget, cursor: ReveEtlCursor, now: datetime) -> bool:
    """Whether this endpoint may be left alone for now.

    Only applies between cycles: a cycle already in flight always continues, or
    a long drain would be abandoned halfway every time the interval elapsed.
    """
    if target.min_interval is None or cursor.refresh_cycle_end is not None:
        return False
    last = cursor.refresh_watermark or cursor.completed_at
    return last is not None and now - last < target.min_interval


def _recovery_windows(
    watermark: datetime | None, cursor: ReveEtlCursor, *, recover: bool = True
) -> list[datetime | None]:
    """The windows worth trying, in order, each a superset of the one before.

    A `504` means REVE could not serve *this* window, not that the changes are
    gone: a wider window returns everything the narrower one would, so widening
    never skips anything. That is what separates this from advancing the
    watermark past an unserved gap, which loses the gap permanently and is why
    the automatic jump was removed in Slice 2.

    Widening reaches further back on a fixed schedule rather than recalling a
    window that once worked. Measured during the 26 August outage, REVE's
    filtered path degrades as the window narrows -- 36 hours back timed out,
    26 days answered in 16s, 87 days in 2.7s, and no filter at all in 2.5s --
    because a scan has to travel further to fill a page of 100 when fewer rows
    match. Under that failure a remembered window is worth nothing: it is a
    fact about REVE when it was healthy, and it is recent by construction,
    which is the shape that fails hardest. It stays as a cheap second rung for
    an ordinary blip, but the schedule is what actually recovers.

    A standing failure also starts further down the ladder, so a rung already
    known bad is not re-bought at a call an hour. The last rung is never
    dropped -- that would leave none.

    There is deliberately no unfiltered rung. A full drain is 469 pages and four
    days, too big to start unattended on a failure nobody has looked at; the
    tick stops instead and says so.
    """
    windows: list[datetime | None] = []
    if watermark is not None:
        windows.append(watermark)
    if not recover:
        return windows

    good = cursor.last_good_date_from
    if good is not None and good not in windows:
        windows.append(good)

    anchor = watermark or good
    if anchor is not None:
        for step in WIDENING_STEPS:
            wider = anchor - step
            if wider not in windows:
                windows.append(wider)

    skip = min(cursor.consecutive_failures, len(windows) - 1)
    return windows[skip:]


async def _drain(
    client: ReveClient,
    db: AsyncSession,
    import_fn: ImportFn,
    windows: list[datetime | None],
    *,
    start_page: int,
    remaining: int,
    save: Callable[..., Awaitable[None]],
) -> tuple[int, int, bool, datetime | None, int]:
    """Try each window in turn, giving the tick's budget to the first that works.

    Also reports the attempts that failed. They cost REVE calls exactly like
    successful ones, so leaving them out of the count would let a recovery
    tick spend past the hourly cap and collect a 429 for its trouble.
    """
    last_error: Exception | None = None
    for attempt, window in enumerate(windows):
        if remaining - attempt <= 0:
            break
        try:
            rows, last_page, exhausted = await import_fn(
                client,
                db,
                date_from=window,
                date_to=None,
                # Widening starts a different result set, so page 5 of the old
                # one means nothing in the new: pagination restarts.
                start_page=start_page if attempt == 0 else 1,
                max_pages=remaining - attempt,
                on_page=lambda page, done, _w=window: save(page, done, window=_w),
            )
        except Exception as exc:
            if not is_server_error(exc) or attempt == len(windows) - 1:
                raise
            await db.rollback()
            last_error = exc
            label = window.isoformat() if window else "no date_from"
            print(f"  {label} not served; widening", file=sys.stderr)
            continue
        return rows, last_page, exhausted, window, attempt
    raise last_error if last_error else RuntimeError("no window attempted")


async def _restart_cycle(db: AsyncSession) -> int:
    """Send the in-flight cycle back to page 1 without moving its window.

    Pages already drained cannot be revisited any other way: the endpoint has no
    `date_to`, and once a cycle completes the watermark jumps past them for good.
    Rewinding re-reads the same `date_from` result set from the start, which is
    how rows dropped before a fix shipped are picked up by the fixed code.

    Only `next_page` moves. `refresh_cycle_end` stays frozen, so the window does
    not shift under the re-read, and `refresh_watermark` is untouched.
    """
    cursor = await read_cursor(db, TARIFFS_ENDPOINT)
    if cursor.refresh_cycle_end is None:
        print(
            f"{TARIFFS_ENDPOINT}: no cycle in flight, nothing to rewind "
            "(the next tick starts a fresh one at page 1 anyway)",
            file=sys.stderr,
        )
        return 1

    was = cursor.next_page
    cursor.next_page = 1
    await db.commit()
    print(
        f"{TARIFFS_ENDPOINT}: rewound page {was} -> 1, "
        f"window held at {cursor.refresh_cycle_end.isoformat()}"
    )
    return 0


async def _handle_server_error(db: AsyncSession, endpoint: str, detail: str) -> None:
    """A 504/timeout: record it and leave the watermark exactly where it is.

    Advancing past a window REVE would not serve discards that window for good,
    because the endpoint has no ``date_to`` to come back with. Stalling is
    recoverable; skipping is not.
    """
    await record_error(db, endpoint, detail)
    await db.commit()
    print(
        f"server error on {endpoint}; watermark left in place, "
        f"retry next tick: {detail}",
        file=sys.stderr,
    )


async def _run_tick(
    db: AsyncSession,
    client: ReveClient,
    budget: int,
    date_from_override: datetime | None = None,
) -> int:
    cursors = {c.endpoint: c for c in await read_all_cursors(db)}
    if not all(c.completed_at is not None for c in cursors.values()):
        print("initial seed not complete; refresh is a no-op")
        return 0

    now = datetime.now(UTC)
    calls_used = 0
    for target in REFRESH_PRIORITY:
        endpoint, import_fn = target.endpoint, target.import_fn
        remaining = budget - calls_used
        if remaining <= 0:
            break
        # Read fresh rather than from a map built before the loop: the target
        # above this one has committed since, and a bulk UPDATE expires the ORM
        # instances it matched.
        cursor = await read_cursor(db, endpoint)
        if _too_soon(target, cursor, now):
            continue

        if cursor.refresh_cycle_end is None:
            cycle_end = now
            start_page = 1
        else:
            cycle_end = cursor.refresh_cycle_end
            start_page = cursor.next_page
        watermark = cursor.refresh_watermark or cursor.completed_at
        windows: list[datetime | None] = (
            [date_from_override]
            if date_from_override is not None
            else _recovery_windows(watermark, cursor, recover=target.recover)
        )

        async def _save(
            page: int,
            exhausted: bool,
            *,
            window: datetime | None,
            _endpoint: str = endpoint,
            _cycle_end: datetime = cycle_end,
            _consumes: bool = target.consumes_backlog,
        ) -> None:
            if _consumes:
                seeded = await seed_backlog_from_ledger(db)
                if seeded:
                    print(f"  seeded {seeded} connector(s) from the backlog")
            await record_refresh_progress(
                db,
                _endpoint,
                next_page=page + 1,
                cycle_end=_cycle_end,
                exhausted=exhausted,
                window_start=window,
            )
            await db.commit()

        try:
            rows, last_page, exhausted, window_start, failed = await _drain(
                client,
                db,
                import_fn,
                windows,
                start_page=start_page,
                remaining=remaining,
                save=_save,
            )
        except Exception as exc:
            if is_rate_limit(exc):
                await db.commit()
                print(f"rate-limited on {endpoint}; resume next tick")
                return 0
            await db.rollback()
            # Read back rather than reuse `start_page`: progress commits per
            # page, so the cursor is the only thing that knows which page of a
            # multi-page tick actually died - and that page is what the next
            # tick will retry.
            failed_page = (await read_cursor(db, endpoint)).next_page
            detail = f"page {failed_page}: {type(exc).__name__}: {exc}"
            if is_server_error(exc):
                await _handle_server_error(db, endpoint, detail)
                return 0
            await record_error(db, endpoint, detail)
            await db.commit()
            print(f"error on {endpoint} {detail}", file=sys.stderr)
            return 1

        calls_used += last_page - start_page + 1 + failed
        wm = window_start.isoformat() if window_start else "-"
        print(
            f"  {endpoint:<22} date_from={wm} rows={rows:<5} "
            f"{'drained' if exhausted else 'more pages next tick'}"
        )

    print(f"\ncalls used: {calls_used}/{budget}")
    return 0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="refresh_reve", description="Incremental post-seed REVE refresh"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print the refresh cursor state and exit without making any REVE call.",
    )
    parser.add_argument(
        "--date-from",
        type=datetime.fromisoformat,
        default=None,
        help=(
            "Override the stored watermark for this run only (ISO 8601). "
            "Aims a probe without editing reve_etl_cursor by hand."
        ),
    )
    parser.add_argument(
        "--restart-cycle",
        action="store_true",
        help=(
            "Rewind the in-flight cycle to page 1 and exit, making no REVE call. "
            "Leaves the window and the watermark alone, so the next tick re-reads "
            "the same result set from the start."
        ),
    )
    parser.add_argument(
        "--budget",
        type=int,
        default=DEFAULT_BUDGET_PER_RUN,
        help=(
            "Max REVE calls this tick may make "
            f"(env REVE_BUDGET_PER_RUN, default {DEFAULT_BUDGET_PER_RUN})."
        ),
    )
    return parser.parse_args(argv)


async def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    async with SessionLocal() as db:
        if args.status:
            return await _print_status(db)
        async with reve_etl_lock(engine) as acquired:
            if not acquired:
                print("another REVE run holds the lock; nothing to do")
                return 0
            if args.restart_cycle:
                return await _restart_cycle(db)
            async with ReveClient(max_retries=0) as client:
                exit_code = await _run_tick(
                    db, client, budget=args.budget, date_from_override=args.date_from
                )
            # Runs whatever the tick did: the band that applies rotates on the
            # hour, so the stored price goes stale without any REVE call.
            changed = await recompute_connector_prices(db)
            await db.commit()
            print(f"repriced connectors: {changed}")
            return exit_code


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
