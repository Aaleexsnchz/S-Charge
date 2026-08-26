"""a cpo's descriptive fields are optional

Revision ID: 7f34f3decda8
Revises: e18df355aad7
Create Date: 2026-08-26 08:23:34.006837

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7f34f3decda8"
down_revision: str | Sequence[str] | None = "e18df355aad7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Everything REVE publishes about an operator beyond its identity. `source_id`,
# `party_id` and the watermark stay required: they are the key, the target of
# `charging_points.party_id`, and the refresh position.
DESCRIPTIVE = ("cif", "name", "address", "city", "city_code", "postal_code", "country")


def upgrade() -> None:
    for column in DESCRIPTIVE:
        op.alter_column("cpos", column, existing_type=sa.TEXT(), nullable=True)


def downgrade() -> None:
    # Reversible only while every row happens to be complete; a CPO mirrored
    # after this migration may hold the NULLs it exists to allow.
    for column in DESCRIPTIVE:
        op.alter_column("cpos", column, existing_type=sa.TEXT(), nullable=False)
