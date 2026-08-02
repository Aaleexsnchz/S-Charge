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
makes REVE scan/return too much and the gateway times out (504). Because there is
no ``date_to``, an old range can't be sliced into chunks — so a 504 from a stale
watermark is handled by **jumping the watermark to ``now`` minus
``REVE_REFRESH_LOOKBACK_HOURS``** (a span we know returns 200) and carrying on.
The skipped stretch is unrecoverable through this endpoint, but it's only ever a
period where little or nothing changed. A 504 while the watermark is *already*
recent is treated as a transient REVE blip: left in place to retry next tick.

A ``429`` stops the tick to resume next time. ``ReveClient(max_retries=0)`` here:
a 504 is not worth an immediate retry under a 5-call/hour budget. Jumps are
audited (``reve_refresh_jumped_to_recent``).
"""

import argparse
import asyncio
import sys
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from http import HTTPStatus

import httpx
from app.config import settings
from app.database import SessionLocal
from app.etl.cursor import (
    read_all_cursors,
    record_error,
    record_refresh_progress,
    skip_refresh_window,
)
from app.etl.reve import import_tariffs
from app.integrations.reve import ReveClient
from app.utils.audit import audit
from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_BUDGET_PER_RUN = settings.reve_budget_per_run
LOOKBACK = timedelta(hours=settings.reve_refresh_lookback_hours)

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
    print(f"{'endpoint':<22} {'next_page':>9} {'watermark':<28} {'cycle_end'}")
    for c in cursors:
        wm = c.refresh_watermark.isoformat() if c.refresh_watermark else "-"
        ce = c.refresh_cycle_end.isoformat() if c.refresh_cycle_end else "-"
        print(f"{c.endpoint:<22} {c.next_page:>9} {wm:<28} {ce}")
    return 0


async def _handle_server_error(
    db: AsyncSession,
    endpoint: str,
    window_start: datetime | None,
    recent: datetime,
    exc: Exception,
) -> None:
    """A 504/timeout: jump a stale watermark to ``recent``; leave a recent one be.

    A 504 with the watermark already recent is a transient REVE blip — keep the
    watermark so the next tick retries the same point. A 504 with a stale
    watermark means the "since then" set is too big to serve; jump to ``recent``
    (the skipped span is unrecoverable here) and carry on.
    """
    error = f"{type(exc).__name__}: {exc}"
    if window_start is not None and window_start >= recent:
        await record_error(db, endpoint, error)
        await db.commit()
        print(
            f"transient server error on {endpoint} at recent watermark; "
            f"retry next tick: {exc}",
            file=sys.stderr,
        )
        return
    await skip_refresh_window(db, endpoint, new_watermark=recent, error=error)
    await db.commit()
    audit(
        "reve_refresh_jumped_to_recent",
        endpoint=endpoint,
        skipped_from=window_start.isoformat() if window_start else None,
        skipped_to=recent.isoformat(),
    )
    print(f"watermark too old on {endpoint}; jumped to {recent.isoformat()}")


async def _run_tick(db: AsyncSession, client: ReveClient, budget: int) -> int:
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
        window_start = cursor.refresh_watermark or cursor.completed_at

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
                await _handle_server_error(
                    db, endpoint, window_start, now - LOOKBACK, exc
                )
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
        async with ReveClient(max_retries=0) as client:
            return await _run_tick(db, client, budget=args.budget)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
