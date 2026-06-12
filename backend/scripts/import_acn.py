import argparse
import asyncio
import sys

from app.database import SessionLocal
from app.etl.acn import import_acn_sessions
from app.integrations.acn import AcnClient

SITES = ["caltech", "jpl", "office001"]


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="import_acn", description="One-shot resumable ACN-Data bulk import"
    )
    parser.add_argument(
        "--site",
        choices=SITES,
        default=None,
        help="Import a single site (default: all three).",
    )
    parser.add_argument(
        "--start-page",
        type=int,
        default=1,
        help="Resume from this page (only meaningful with --site).",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Stop after N pages (smoke-testing aid).",
    )
    return parser.parse_args(argv)


async def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    sites = [args.site] if args.site else SITES

    async with SessionLocal() as db, AcnClient() as client:
        for site in sites:
            page = args.start_page if args.site else 1
            total_rows = 0
            pages_done = 0
            while True:
                try:
                    rows, last_page, exhausted = await import_acn_sessions(
                        client, db, site, start_page=page, max_pages=1
                    )
                except Exception as exc:
                    await db.rollback()
                    print(
                        f"error on {site} page {page}: {exc}\n"
                        f"resume with: --site {site} --start-page {page}",
                        file=sys.stderr,
                    )
                    return 1
                await db.commit()
                total_rows += rows
                pages_done += 1
                print(f"  {site:<10} page={last_page:<5} rows={rows}")
                if exhausted or (args.max_pages is not None and pages_done >= args.max_pages):
                    break
                page = last_page + 1
            print(f"{site}: {total_rows} sessions imported")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
