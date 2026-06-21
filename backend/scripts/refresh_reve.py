"""Post-seed incremental refresh of REVE tariffs (prices).

Runs on the same hourly, budgeted cron as ``seed_reve`` once the initial seed
is complete. Only ``/connectors/tariffs`` is refreshed: prices are the sole
field that changes often enough to matter. The physical catalogue (``/cpos``,
``/locations``) is left frozen at the seed snapshot — it carries no price data,
rarely changes, and refreshing it would only starve the tariff call budget; the
cost is that stations added to REVE after the seed won't appear.

The endpoint is refreshed with an ``[date_from, date_to]`` window: ``date_from``
is the last fully drained cycle's upper bound (the watermark), ``date_to`` is
frozen when the cycle starts so pagination stays stable across ticks. A cycle
may span several ticks under budget; the watermark only advances once the whole
window drains, so a backlog is always picked up by later ticks.
"""

import argparse
import asyncio
import os
import sys
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

import httpx
from app.database import SessionLocal
from app.etl.cursor import read_all_cursors, record_error, record_refresh_progress
from app.etl.reve import import_tariffs
from app.integrations.reve import ReveClient
from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_BUDGET_PER_RUN = int(os.getenv("REVE_BUDGET_PER_RUN", "5"))

ImportFn = Callable[..., Awaitable[tuple[int, int, bool]]]
REFRESH_PRIORITY: list[tuple[str, ImportFn]] = [
    ("/connectors/tariffs", import_tariffs),
]


def _is_rate_limit(exc: Exception) -> bool:
    if not isinstance(exc, httpx.HTTPStatusError):
        return False
    return exc.response.status_code == httpx.codes.TOO_MANY_REQUESTS


async def _print_status(db: AsyncSession) -> int:
    cursors = await read_all_cursors(db)
    print(f"{'endpoint':<22} {'next_page':>9} {'watermark':<28} {'cycle_end'}")
    for c in cursors:
        wm = c.refresh_watermark.isoformat() if c.refresh_watermark else "-"
        ce = c.refresh_cycle_end.isoformat() if c.refresh_cycle_end else "-"
        print(f"{c.endpoint:<22} {c.next_page:>9} {wm:<28} {ce}")
    return 0


async def _run_tick(db: AsyncSession, client: ReveClient, budget: int) -> int:
    cursors = {c.endpoint: c for c in await read_all_cursors(db)}
    if not all(c.completed_at is not None for c in cursors.values()):
        print("initial seed not complete; refresh is a no-op")
        return 0

    calls_used = 0
    for endpoint, import_fn in REFRESH_PRIORITY:
        cursor = cursors[endpoint]
        remaining = budget - calls_used
        if remaining <= 0:
            break

        if cursor.refresh_cycle_end is None:
            cycle_end = datetime.now(UTC)
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
                date_to=cycle_end,
                start_page=start_page,
                max_pages=remaining,
            )
        except Exception as exc:
            if _is_rate_limit(exc):
                await db.commit()
                print(f"rate-limited on {endpoint}; resume next tick")
                return 0
            await db.rollback()
            await record_error(db, endpoint, f"{type(exc).__name__}: {exc}")
            await db.commit()
            print(f"error on {endpoint}: {exc}", file=sys.stderr)
            return 1

        pages = max(0, last_page - start_page + 1)
        calls_used += pages
        await record_refresh_progress(
            db,
            endpoint,
            next_page=last_page + 1,
            cycle_end=cycle_end,
            exhausted=exhausted,
        )
        await db.commit()
        print(
            f"  {endpoint:<22} rows={rows:<5} pages={pages:<3} "
            f"{'cycle complete' if exhausted else 'cycle continues'}"
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
        async with ReveClient() as client:
            return await _run_tick(db, client, budget=args.budget)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
