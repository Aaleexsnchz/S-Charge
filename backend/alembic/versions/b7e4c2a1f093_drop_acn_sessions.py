"""drop acn_sessions

ACN-Data was dropped from scope (see docs/PLAN.md revision 2026-06-21): it stayed
internal-only and never landed in the product. The catalogue/pricing/simulation stack
does not depend on it. Kept only as a documented road-not-taken in the thesis.

Revision ID: b7e4c2a1f093
Revises: 71cc55ab4bec
Create Date: 2026-06-21 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b7e4c2a1f093"
down_revision: Union[str, Sequence[str], None] = "71cc55ab4bec"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_acn_sessions_station_id", table_name="acn_sessions")
    op.drop_index("ix_acn_sessions_site_connection", table_name="acn_sessions")
    op.drop_index("ix_acn_sessions_site", table_name="acn_sessions")
    op.drop_table("acn_sessions")


def downgrade() -> None:
    op.create_table(
        "acn_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("session_id", sa.Text(), nullable=True),
        sa.Column("site", sa.Text(), nullable=False),
        sa.Column("station_id", sa.Text(), nullable=True),
        sa.Column("space_id", sa.Text(), nullable=True),
        sa.Column("cluster_id", sa.Text(), nullable=True),
        sa.Column("connection_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("disconnect_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("done_charging_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("kwh_delivered", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("time_zone", sa.Text(), nullable=True),
        sa.Column("user_id", sa.Text(), nullable=True),
        sa.Column("kwh_requested", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("minutes_available", sa.Integer(), nullable=True),
        sa.Column("requested_departure", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "imported_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id"),
    )
    op.create_index(
        op.f("ix_acn_sessions_site"), "acn_sessions", ["site"], unique=False
    )
    op.create_index(
        "ix_acn_sessions_site_connection",
        "acn_sessions",
        ["site", "connection_time"],
        unique=False,
    )
    op.create_index(
        op.f("ix_acn_sessions_station_id"),
        "acn_sessions",
        ["station_id"],
        unique=False,
    )
