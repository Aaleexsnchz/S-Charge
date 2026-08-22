import argparse
import asyncio
import sys
from collections.abc import Awaitable, Callable

import httpx
from app.config import settings
from app.database import SessionLocal, engine
from app.etl.cursor import read_all_cursors, read_cursor, record_error, record_progress
from app.etl.lock import reve_etl_lock
from app.etl.reve import (
    import_cpos,
    import_locations,
    import_tariffs,
)
from app.integrations.reve import ReveClient
from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_BUDGET_PER_RUN = settings.reve_budget_per_run

ImportFn = Callable[..., Awaitable[tuple[int, int, bool]]]
ENDPOINT_PRIORITY: list[tuple[str, ImportFn]] = [
    ("/cpos", import_cpos),
    ("/locations", import_locations),
    ("/connectors/tariffs", import_tariffs),
]


def _is_rate_limit(exc: Exception) -> bool:
    if not isinstance(exc, httpx.HTTPStatusError):
        return False
    return exc.response.status_code == httpx.codes.TOO_MANY_REQUESTS


async def _print_status(db: AsyncSession) -> int:
    cursors = await read_all_cursors(db)
    print(f"{'endpoint':<30} {'next_page':>9} {'completed':<24} {'last_error'}")
    for c in cursors:
        completed = c.completed_at.isoformat() if c.completed_at else "-"
        err = c.last_error or "-"
        print(f"{c.endpoint:<30} {c.next_page:>9} {completed:<24} {err}")
    return 0


async def _run_tick(db: AsyncSession, client: ReveClient, budget: int) -> int:
    calls_used = 0

    for endpoint, import_fn in ENDPOINT_PRIORITY:
        cursor = await read_cursor(db, endpoint)
        if cursor.completed_at is not None:
            continue
        remaining = budget - calls_used
        if remaining <= 0:
            break

        start_page = cursor.next_page
        try:
            rows, last_page, exhausted = await import_fn(
                client, db, start_page=start_page, max_pages=remaining
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
        await record_progress(
            db, endpoint, next_page=last_page + 1, exhausted=exhausted
        )
        await db.commit()
        print(
            f"  {endpoint:<30} rows={rows:<6} pages={pages:<3} "
            f"exhausted={'yes' if exhausted else 'no'}"
        )

    cursors = await read_all_cursors(db)
    if all(c.completed_at is not None for c in cursors):
        print("\ninitial seed complete")
    else:
        print(f"\ncalls used: {calls_used}/{budget}")
    return 0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="seed_reve", description="Cursor-driven REVE seed orchestrator"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print the cursor table and exit without making any REVE call.",
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
            async with ReveClient() as client:
                return await _run_tick(db, client, budget=args.budget)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
