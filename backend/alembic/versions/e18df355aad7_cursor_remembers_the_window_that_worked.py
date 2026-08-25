"""cursor remembers the window that worked

Revision ID: e18df355aad7
Revises: 2300d706fc7e
Create Date: 2026-08-25 21:21:18.586704

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e18df355aad7"
down_revision: str | Sequence[str] | None = "2300d706fc7e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "reve_etl_cursor",
        sa.Column("last_good_date_from", sa.DateTime(timezone=True), nullable=True),
    )

    # `/locations` and `/cpos` join the refresh in this change, and both cursors
    # carry the remains of a cycle abandoned on 2026-06-21 when the refresh was
    # narrowed to tariffs: `/locations` sits at page 5 with a `refresh_cycle_end`
    # still set. The tick resumes at `next_page` whenever that is set, so without
    # this reset the first cycle would start a brand-new result set at page 5 and
    # silently skip pages 1-4. Nothing is lost: the seed watermark stays, so the
    # first cycle asks from the seed date.
    op.execute(
        """
        UPDATE reve_etl_cursor
        SET next_page = 1, refresh_cycle_end = NULL
        WHERE endpoint IN ('/locations', '/cpos') AND refresh_cycle_end IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_column("reve_etl_cursor", "last_good_date_from")
