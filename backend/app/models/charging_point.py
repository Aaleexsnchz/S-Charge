import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.cpo import Cpo
    from app.models.tariff import Tariff


class ChargingPointSource(enum.StrEnum):
    REVE_SEED = "reve_seed"
    USER = "user"


class PricingKind(enum.StrEnum):
    """How a connector charges, right now, by the bands that apply to it.

    ``UNKNOWN`` covers no tariff, no band matching the present moment, and a
    price the source published outside any plausible range.
    """

    ENERGY = "energy"
    TIME = "time"
    FLAT = "flat"
    FREE = "free"
    UNKNOWN = "unknown"


class ChargingPoint(Base):
    __tablename__ = "charging_points"
    __table_args__ = (
        UniqueConstraint(
            "source", "source_id", name="uq_charging_points_source_source_id"
        ),
        Index(
            "ix_charging_points_archived_lat_lng",
            "archived_at",
            "latitude",
            "longitude",
        ),
        Index("ix_charging_points_party_id", "party_id"),
        Index("ix_charging_points_owner_user_id", "owner_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source: Mapped[ChargingPointSource] = mapped_column(
        Enum(
            ChargingPointSource,
            name="charging_point_source",
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
        ),
        nullable=False,
    )
    source_id: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    cpo_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    party_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("cpos.party_id"), nullable=True
    )
    version: Mapped[str | None] = mapped_column(Text, nullable=True)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str] = mapped_column(Text, nullable=False)
    postal_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    region: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str | None] = mapped_column(Text, nullable=True)
    country_code: Mapped[str] = mapped_column(Text, nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    parking_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    facilities: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    time_zone: Mapped[str] = mapped_column(Text, nullable=False)
    opening_24_7: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # OCPI regular_hours: a list of {weekday, period_begin, period_end} objects
    opening_hours: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB, nullable=True
    )
    charging_when_closed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    directions: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB, nullable=True
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    cpo: Mapped["Cpo | None"] = relationship(
        back_populates="charging_points",
        foreign_keys="ChargingPoint.party_id",
        primaryjoin="ChargingPoint.party_id == Cpo.party_id",
    )
    evses: Mapped[list["Evse"]] = relationship(
        back_populates="charging_point",
        cascade="all, delete-orphan",
    )

    @property
    def aggregate_status(self) -> str:
        """Marker-colour rollup of the EVSEs' (simulated) availability.

        Requires ``evses`` to be loaded; readers go through the points
        service, which eager-loads the full nesting.
        """
        known = [evse.status for evse in self.evses if evse.status is not None]
        if not known:
            return "unknown"
        if any(status == "AVAILABLE" for status in known):
            return "available"
        return "occupied"


class Evse(Base):
    __tablename__ = "evses"
    __table_args__ = (
        UniqueConstraint(
            "charging_point_id", "source_id", name="uq_evses_charging_point_source_id"
        ),
        Index(
            "ix_evses_evse_id",
            "evse_id",
            postgresql_where="evse_id IS NOT NULL",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    charging_point_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("charging_points.id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[str] = mapped_column(Text, nullable=False)
    evse_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    physical_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    floor_level: Mapped[str | None] = mapped_column(Text, nullable=True)
    capabilities: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    wheelchair_accessibility: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Availability (OCPI EVSE status, e.g. "AVAILABLE"), simulated in Phase 4 —
    # not mirrored from REVE. Null until simulation runs. Operational status
    # (working vs. broken) is assumed always-operational and is not modelled.
    status: Mapped[str | None] = mapped_column(Text, nullable=True)
    status_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source_last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    charging_point: Mapped["ChargingPoint"] = relationship(back_populates="evses")
    connectors: Mapped[list["Connector"]] = relationship(
        back_populates="evse", cascade="all, delete-orphan"
    )


class Connector(Base):
    __tablename__ = "connectors"
    __table_args__ = (
        UniqueConstraint("evse_id", "source_id", name="uq_connectors_evse_source_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    evse_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("evses.id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[str] = mapped_column(Text, nullable=False)
    standard: Mapped[str] = mapped_column(Text, nullable=False)
    format: Mapped[str] = mapped_column(Text, nullable=False)
    power_type: Mapped[str] = mapped_column(Text, nullable=False)
    max_electric_power: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_voltage: Mapped[int] = mapped_column(Integer, nullable=False)
    max_amperage: Mapped[int] = mapped_column(Integer, nullable=False)
    tariff_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("tariffs.id"), nullable=True
    )
    pricing_kind: Mapped[PricingKind] = mapped_column(
        Enum(
            PricingKind,
            name="connector_pricing_kind",
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
        ),
        nullable=False,
        server_default=PricingKind.UNKNOWN.value,
    )
    # Denormalised from the tariff bands for "now"; recomputed on the hourly
    # tick, since the band that applies changes on the hour.
    current_price_per_kwh: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 4), nullable=True
    )
    source_last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    evse: Mapped["Evse"] = relationship(back_populates="connectors")
    tariff: Mapped["Tariff | None"] = relationship(back_populates="connectors")
