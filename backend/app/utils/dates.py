from datetime import datetime


def parse_datetime(raw: object) -> datetime | None:
    """An upstream ISO 8601 timestamp, or ``None`` when absent or unparseable."""
    if not isinstance(raw, str) or not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None
