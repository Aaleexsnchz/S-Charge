"""ledger of connectors reve serves and we do not

Revision ID: 2300d706fc7e
Revises: a1da13ad1e63
Create Date: 2026-08-23 14:16:12.826978

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2300d706fc7e"
down_revision: str | Sequence[str] | None = "a1da13ad1e63"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reve_unmirrored_connectors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("evse_id", sa.Text(), nullable=False),
        sa.Column("connector_id", sa.Text(), nullable=False),
        sa.Column(
            "tariff_raw", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "evse_id", "connector_id", name="uq_reve_unmirrored_evse_connector"
        ),
    )


def downgrade() -> None:
    op.drop_table("reve_unmirrored_connectors")
