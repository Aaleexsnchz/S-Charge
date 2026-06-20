"""drop reve operational status; add refresh cursor state

Revision ID: 4702d2758671
Revises: fc85bed723ce
Create Date: 2026-06-16 19:29:45.177331

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4702d2758671"
down_revision: str | Sequence[str] | None = "fc85bed723ce"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OPERATIONAL_STATUS_ENDPOINT = "/evses/operational_status"


def upgrade() -> None:
    op.add_column(
        "reve_etl_cursor",
        sa.Column("refresh_watermark", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "reve_etl_cursor",
        sa.Column("refresh_cycle_end", sa.DateTime(timezone=True), nullable=True),
    )
    # We no longer mirror EVSE operational status from REVE — live availability
    # is simulated (Phase 4). Drop its cursor so the seed can reach "complete".
    op.execute(
        sa.text("DELETE FROM reve_etl_cursor WHERE endpoint = :e").bindparams(
            e=OPERATIONAL_STATUS_ENDPOINT
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "INSERT INTO reve_etl_cursor (endpoint, next_page) VALUES (:e, 1) "
            "ON CONFLICT (endpoint) DO NOTHING"
        ).bindparams(e=OPERATIONAL_STATUS_ENDPOINT)
    )
    op.drop_column("reve_etl_cursor", "refresh_cycle_end")
    op.drop_column("reve_etl_cursor", "refresh_watermark")
