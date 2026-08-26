import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ElectricityPrice(Base):
    """One hourly PVPC price slot mirrored from REE."""

    __tablename__ = "electricity_prices"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    hour_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), unique=True, nullable=False
    )
    price_per_kwh: Mapped[Decimal] = mapped_column(Numeric(8, 5), nullable=False)
    # REE's own write time for the day this hour belongs to, not ours. It moves
    # when REE restates a day already published, which `fetched_at` cannot show:
    # that one carries `onupdate` and only ever holds the most recent refetch.
    source_last_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
