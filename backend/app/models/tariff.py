import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    ARRAY,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    Time,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.charging_point import Connector


class Tariff(Base):
    __tablename__ = "tariffs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    currency: Mapped[str] = mapped_column(Text, nullable=False)
    valid_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    valid_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    source_last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_refreshed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    connectors: Mapped[list["Connector"]] = relationship(back_populates="tariff")
    elements: Mapped[list["TariffElement"]] = relationship(
        back_populates="tariff",
        cascade="all, delete-orphan",
        order_by="TariffElement.element_index",
    )


class TariffElement(Base):
    """One OCPI price component, with the restrictions of the element holding it.

    OCPI nests components inside elements; flattening to one row per component
    keeps the price and the restrictions that gate it on the same row, which is
    the grain every query wants. ``element_index`` preserves the source order.
    """

    __tablename__ = "tariff_elements"
    __table_args__ = (Index("ix_tariff_elements_tariff_id", "tariff_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tariff_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tariffs.id", ondelete="CASCADE"), nullable=False
    )
    element_index: Mapped[int] = mapped_column(Integer, nullable=False)
    component_type: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    vat: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    step_size: Mapped[int | None] = mapped_column(Integer, nullable=True)

    start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    days_of_week: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    min_kwh: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    max_kwh: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    min_current: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    max_current: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    # REVE publishes power restrictions in kW, unlike Connector.max_electric_power.
    min_power_kw: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    max_power_kw: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    min_duration_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_duration_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reservation: Mapped[str | None] = mapped_column(Text, nullable=True)

    tariff: Mapped["Tariff"] = relationship(back_populates="elements")
