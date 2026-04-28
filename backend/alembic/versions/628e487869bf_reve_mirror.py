"""reve mirror

Revision ID: 628e487869bf
Revises: c204916f7c36
Create Date: 2026-04-28 20:09:28.550156

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "628e487869bf"
down_revision: str | Sequence[str] | None = "c204916f7c36"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Postgres ENUM type, managed explicitly so downgrade can drop it cleanly.
# create_type=False keeps op.create_table from auto-issuing CREATE TYPE.
charging_point_source = postgresql.ENUM(
    "reve_seed",
    "user",
    name="charging_point_source",
    create_type=False,
)


def upgrade() -> None:
    """Upgrade schema."""
    charging_point_source.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "cpos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("party_id", sa.Text(), nullable=False),
        sa.Column("cif", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("city", sa.Text(), nullable=False),
        sa.Column("city_code", sa.Text(), nullable=False),
        sa.Column("postal_code", sa.Text(), nullable=False),
        sa.Column("region", sa.Text(), nullable=True),
        sa.Column("state", sa.Text(), nullable=True),
        sa.Column("country", sa.Text(), nullable=False),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("website", sa.Text(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source_last_updated_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("party_id"),
        sa.UniqueConstraint("source_id"),
    )
    op.create_table(
        "tariffs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("price_per_kwh", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("price_component_type", sa.Text(), nullable=True),
        sa.Column("vat_percentage", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("step_size", sa.Integer(), nullable=True),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_last_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_refreshed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id"),
    )
    op.create_table(
        "charging_points",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source", charging_point_source, nullable=False),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("cpo_name", sa.Text(), nullable=True),
        sa.Column("party_id", sa.Text(), nullable=True),
        sa.Column("version", sa.Text(), nullable=True),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("city", sa.Text(), nullable=False),
        sa.Column("postal_code", sa.Text(), nullable=True),
        sa.Column("region", sa.Text(), nullable=True),
        sa.Column("state", sa.Text(), nullable=True),
        sa.Column("country_code", sa.Text(), nullable=False),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("longitude", sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column("parking_type", sa.Text(), nullable=True),
        sa.Column("facilities", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("time_zone", sa.Text(), nullable=False),
        sa.Column("opening_24_7", sa.Boolean(), nullable=False),
        sa.Column("opening_hours", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("charging_when_closed", sa.Boolean(), nullable=True),
        sa.Column("directions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("owner_user_id", sa.Uuid(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_last_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["party_id"], ["cpos.party_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "source_id", name="uq_charging_points_source_source_id"),
    )
    op.create_index(
        "ix_charging_points_archived_lat_lng",
        "charging_points",
        ["archived_at", "latitude", "longitude"],
        unique=False,
    )
    op.create_index(
        "ix_charging_points_owner_user_id",
        "charging_points",
        ["owner_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_charging_points_party_id",
        "charging_points",
        ["party_id"],
        unique=False,
    )
    op.create_table(
        "evses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("charging_point_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("evse_id", sa.Text(), nullable=True),
        sa.Column("physical_reference", sa.Text(), nullable=True),
        sa.Column("floor_level", sa.Text(), nullable=True),
        sa.Column("capabilities", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("wheelchair_accessibility", sa.Text(), nullable=True),
        sa.Column("is_operational", sa.Boolean(), nullable=True),
        sa.Column("operational_status_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_last_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["charging_point_id"], ["charging_points.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "charging_point_id", "source_id", name="uq_evses_charging_point_source_id"
        ),
    )
    op.create_index(
        "ix_evses_evse_id",
        "evses",
        ["evse_id"],
        unique=False,
        postgresql_where="evse_id IS NOT NULL",
    )
    op.create_table(
        "connectors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("evse_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("standard", sa.Text(), nullable=False),
        sa.Column("format", sa.Text(), nullable=False),
        sa.Column("power_type", sa.Text(), nullable=False),
        sa.Column("max_electric_power", sa.Integer(), nullable=True),
        sa.Column("max_voltage", sa.Integer(), nullable=False),
        sa.Column("max_amperage", sa.Integer(), nullable=False),
        sa.Column("tariff_id", sa.Uuid(), nullable=True),
        sa.Column("source_last_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["evse_id"], ["evses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tariff_id"], ["tariffs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evse_id", "source_id", name="uq_connectors_evse_source_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("connectors")
    op.drop_index(
        "ix_evses_evse_id", table_name="evses", postgresql_where="evse_id IS NOT NULL"
    )
    op.drop_table("evses")
    op.drop_index("ix_charging_points_party_id", table_name="charging_points")
    op.drop_index("ix_charging_points_owner_user_id", table_name="charging_points")
    op.drop_index("ix_charging_points_archived_lat_lng", table_name="charging_points")
    op.drop_table("charging_points")
    op.drop_table("tariffs")
    op.drop_table("cpos")

    charging_point_source.drop(op.get_bind(), checkfirst=True)
