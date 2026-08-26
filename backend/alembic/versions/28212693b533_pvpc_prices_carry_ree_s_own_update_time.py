"""pvpc prices carry ree's own update time

Revision ID: 28212693b533
Revises: 7f34f3decda8
Create Date: 2026-08-26 09:28:30.815652

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "28212693b533"
down_revision: str | Sequence[str] | None = "7f34f3decda8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nullable and left NULL for rows already stored: REE's write time for a past
    # day is knowable only by re-fetching it, and a backfill would spend a request
    # per day to date a curve nothing reads yet.
    op.add_column(
        "electricity_prices",
        sa.Column("source_last_updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("electricity_prices", "source_last_updated_at")
