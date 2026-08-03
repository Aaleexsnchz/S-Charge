"""Write the OpenAPI schema to a file, so the contract is reviewable in a diff.

The frontend's types are generated from this file rather than from a running
backend, which is what lets CI check that a contract change was regenerated:
`uv run python -m scripts.export_openapi --check` fails when the committed
schema no longer matches the app.
"""

import argparse
import json
import sys
from pathlib import Path

from app.main import app

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "openapi.json"


def render() -> str:
    return json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=DEFAULT_PATH)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero if the file is missing or out of date, writing nothing",
    )
    args = parser.parse_args()

    schema = render()
    if args.check:
        current = args.path.read_text() if args.path.exists() else ""
        if current != schema:
            print(
                f"{args.path} is out of date. Run `just gen-api` and commit it.",
                file=sys.stderr,
            )
            return 1
        return 0

    args.path.write_text(schema)
    print(f"wrote {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
