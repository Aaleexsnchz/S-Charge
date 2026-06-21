"""evse availability status replaces is_operational

Revision ID: 71cc55ab4bec
Revises: 4702d2758671
Create Date: 2026-06-16 19:50:33.065168

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "71cc55ab4bec"
down_revision: str | Sequence[str] | None = "4702d2758671"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("evses", sa.Column("status", sa.Text(), nullable=True))
    op.add_column(
        "evses", sa.Column("status_updated_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.drop_column("evses", "operational_status_updated_at")
    op.drop_column("evses", "is_operational")


def downgrade() -> None:
    op.add_column("evses", sa.Column("is_operational", sa.Boolean(), nullable=True))
    op.add_column(
        "evses",
        sa.Column("operational_status_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.drop_column("evses", "status_updated_at")
    op.drop_column("evses", "status")
