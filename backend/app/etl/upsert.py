from collections.abc import Sequence
from typing import Any

from sqlalchemy.dialects.postgresql import Insert, insert

from app.database import Base


def upsert(model: type[Base], payload: dict[str, Any], key: Sequence[str]) -> Insert:
    """Insert ``payload``, or overwrite the row ``key`` already identifies.

    Every column but the key and the surrogate ``id`` is overwritten, so a row
    keeps its primary key across refreshes and children stay attached to it.
    """
    stmt = insert(model).values(**payload)
    return stmt.on_conflict_do_update(
        index_elements=list(key),
        set_={k: stmt.excluded[k] for k in payload if k != "id" and k not in key},
    )
