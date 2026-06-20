import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, Index, Integer, Numeric, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AcnSession(Base):
    """One charging session mirrored from ACN-Data.

    ``raw_data`` keeps the full upstream payload so later phases can extract
    fields without re-importing.
    """

    __tablename__ = "acn_sessions"
    __table_args__ = (
        Index("ix_acn_sessions_site_connection", "site", "connection_time"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    session_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    site: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    station_id: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    space_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    cluster_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    connection_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    disconnect_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    done_charging_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    kwh_delivered: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    time_zone: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    kwh_requested: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    minutes_available: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requested_departure: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
