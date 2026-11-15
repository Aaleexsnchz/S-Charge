from datetime import UTC, datetime

import pytest
from app.utils.dates import parse_datetime


def test_parses_a_zulu_timestamp_as_utc() -> None:
    assert parse_datetime("2026-07-01T09:30:00Z") == datetime(
        2026, 7, 1, 9, 30, tzinfo=UTC
    )


@pytest.mark.parametrize("raw", [None, "", "not a date", 1_700_000_000])
def test_returns_none_for_anything_unparseable(raw: object) -> None:
    assert parse_datetime(raw) is None
