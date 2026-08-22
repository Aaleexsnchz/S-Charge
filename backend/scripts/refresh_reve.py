"""Post-seed incremental refresh of REVE tariffs (prices).

Runs on the same hourly, budgeted cron as ``seed_reve`` once the initial seed
is complete. Only ``/connectors/tariffs`` is refreshed: prices are the sole
field that changes often enough to matter. The physical catalogue (``/cpos``,
``/locations``) is left frozen at the seed snapshot — it carries no price data,
rarely changes, and refreshing it would only starve the tariff call budget; the
cost is that stations added to REVE after the seed won't appear.

The endpoint takes only ``date_from`` (plus ``page``/``limit``) — there is **no
``date_to``** — and returns every connector whose tariff changed since that
instant. Each tick sets ``date_from`` to the watermark, paginates the result
(across ticks under budget), and on a full drain advances the watermark to the
moment the cycle started, so the next cycle picks up everything since.

What matters is how much has changed *between ``date_from`` and now*: a recent
``date_from`` is a small, cheap result; a watermark that has fallen days behind
makes REVE scan/return too much and the gateway times out (504), and because
there is no ``date_to`` an old range cannot be sliced into chunks.

**A 504 never moves the watermark.** The tick records the error and leaves the
position alone, whatever its age, so the window stays recoverable and an
operator decides what to do about it. An earlier version jumped a stale
watermark forward to a span known to return 200, which kept the refresh moving
by writing the skipped stretch off — silently, and unrecoverably. That is how a
two-hour outage in July 2026 became a 45-day gap. Losing data is worse than
stalling, and a stall is visible in ``last_error``.

The cost is that a watermark REVE will not serve now burns one call per tick
until someone intervenes. That is the intended trade, and ``--date-from`` is how
it gets intervened with.

A ``429`` stops the tick to resume next time. ``ReveClient(max_retries=0)`` here:
a 504 is not worth an immediate retry under a 5-call/hour budget.
"""

import argparse
import asyncio
import sys
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from http import HTTPStatus

import httpx
from app.config import settings
from app.database import SessionLocal, engine
from app.etl.cursor import (
    read_all_cursors,
    record_error,
    record_refresh_progress,
)
from app.etl.lock import reve_etl_lock
from app.etl.reve import import_tariffs
from app.integrations.reve import ReveClient
from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_BUDGET_PER_RUN = settings.reve_budget_per_run

_SKIP_STATUS = frozenset(
    {
        HTTPStatus.BAD_GATEWAY,
        HTTPStatus.SERVICE_UNAVAILABLE,
        HTTPStatus.GATEWAY_TIMEOUT,
    }
)

ImportFn = Callable[..., Awaitable[tuple[int, int, bool]]]
REFRESH_PRIORITY: list[tuple[str, ImportFn]] = [
    ("/connectors/tariffs", import_tariffs),
]


def _is_rate_limit(exc: Exception) -> bool:
    return (
        isinstance(exc, httpx.HTTPStatusError)
        and exc.response.status_code == HTTPStatus.TOO_MANY_REQUESTS
    )


def _is_server_error(exc: Exception) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.TransportError)):
        return True
    return (
        isinstance(exc, httpx.HTTPStatusError)
        and exc.response.status_code in _SKIP_STATUS
    )


async def _print_status(db: AsyncSession) -> int:
    cursors = await read_all_cursors(db)
    print(
        f"{'endpoint':<22} {'next_page':>9} {'watermark':<28} "
        f"{'cycle_end':<28} {'last_error'}"
    )
    for c in cursors:
        wm = c.refresh_watermark.isoformat() if c.refresh_watermark else "-"
        ce = c.refresh_cycle_end.isoformat() if c.refresh_cycle_end else "-"
        err = c.last_error or "-"
        print(f"{c.endpoint:<22} {c.next_page:>9} {wm:<28} {ce:<28} {err}")
    return 0


async def _handle_server_error(db: AsyncSession, endpoint: str, exc: Exception) -> None:
    """A 504/timeout: record it and leave the watermark exactly where it is.

    Advancing past a window REVE would not serve discards that window for good,
    because the endpoint has no ``date_to`` to come back with. Stalling is
    recoverable; skipping is not.
    """
    await record_error(db, endpoint, f"{type(exc).__name__}: {exc}")
    await db.commit()
    print(
        f"server error on {endpoint}; watermark left in place, retry next tick: {exc}",
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
    for endpoint, import_fn in REFRESH_PRIORITY:
        remaining = budget - calls_used
        if remaining <= 0:
            break
        cursor = cursors[endpoint]

        if cursor.refresh_cycle_end is None:
            cycle_end = now
            start_page = 1
        else:
            cycle_end = cursor.refresh_cycle_end
            start_page = cursor.next_page
        window_start = date_from_override or (
            cursor.refresh_watermark or cursor.completed_at
        )

        try:
            rows, last_page, exhausted = await import_fn(
                client,
                db,
                date_from=window_start,
                date_to=None,
                start_page=start_page,
                max_pages=remaining,
            )
        except Exception as exc:
            if _is_rate_limit(exc):
                await db.commit()
                print(f"rate-limited on {endpoint}; resume next tick")
                return 0
            await db.rollback()
            if _is_server_error(exc):
                await _handle_server_error(db, endpoint, exc)
                return 0
            await record_error(db, endpoint, f"{type(exc).__name__}: {exc}")
            await db.commit()
            print(f"error on {endpoint}: {exc}", file=sys.stderr)
            return 1

        calls_used += last_page - start_page + 1
        await record_refresh_progress(
            db,
            endpoint,
            next_page=last_page + 1,
            cycle_end=cycle_end,
            exhausted=exhausted,
        )
        await db.commit()
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
            async with ReveClient(max_retries=0) as client:
                return await _run_tick(
                    db, client, budget=args.budget, date_from_override=args.date_from
                )


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
