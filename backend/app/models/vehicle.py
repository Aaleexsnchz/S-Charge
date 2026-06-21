import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Vehicle(Base):
    """Curated EV catalogue row used as simulation input.

    ``battery_kwh`` is usable capacity; AC charging is always Type 2 in the
    EU market, so only the DC standard varies per model.
    """

    __tablename__ = "vehicles"
    __table_args__ = (UniqueConstraint("make", "model", name="uq_vehicles_make_model"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    make: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    battery_kwh: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    max_ac_kw: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    max_dc_kw: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    dc_connector: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
