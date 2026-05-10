"""reve etl cursor

Revision ID: a9d9c5a0b8b3
Revises: 628e487869bf
Create Date: 2026-05-10 17:01:09.996325

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a9d9c5a0b8b3"
down_revision: str | Sequence[str] | None = "628e487869bf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REVE_ENDPOINTS = (
    "/cpos",
    "/locations",
    "/connectors/tariffs",
    "/evses/operational_status",
)


def upgrade() -> None:
    """Upgrade schema."""
    cursor_table = op.create_table(
        "reve_etl_cursor",
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("next_page", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("endpoint"),
    )

    op.bulk_insert(
        cursor_table,
        [{"endpoint": endpoint, "next_page": 1} for endpoint in REVE_ENDPOINTS],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("reve_etl_cursor")
