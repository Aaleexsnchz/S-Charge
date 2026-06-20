import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Integer, Numeric, Text, Uuid
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
    price_per_kwh: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    price_component_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    vat_percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    step_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    source_last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_refreshed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    connectors: Mapped[list["Connector"]] = relationship(back_populates="tariff")
