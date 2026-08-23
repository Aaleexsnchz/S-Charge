import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, Text, UniqueConstraint, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ReveEtlCursor(Base):
    __tablename__ = "reve_etl_cursor"

    endpoint: Mapped[str] = mapped_column(Text, primary_key=True)
    next_page: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Post-seed incremental refresh state. ``refresh_watermark`` is the upper
    # bound of the last fully drained refresh cycle (date_from for the next).
    # ``refresh_cycle_end`` freezes the current cycle's upper bound while it is
    # paginated across multiple ticks; null between cycles.
    refresh_watermark: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    refresh_cycle_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_attempted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # last_attempted_at answers "when did we last try"; these answer "how long
    # has it been broken", which is the question a stalled watermark raises and
    # the one the container logs cannot answer once they roll over.
    failing_since: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    consecutive_failures: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
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


class ReveUnmirroredConnector(Base):
    """A connector REVE serves a tariff for that the catalogue does not hold.

    The refresh only fetches ``/connectors/tariffs``, so it *meets* stations
    built since the seed without being able to store them — the tariff names an
    EVSE with no row to attach to. Those rows were logged and dropped, which
    survives neither a log rotation nor a container being recreated.

    ``tariff_raw`` is the reason this is a table rather than a counter. A
    connector's tariff reappears in the feed only when its price next changes,
    and that is ~243 days on average, so a repair pass that imported the station
    without the price would leave it blank for the better part of a year. Rows
    are deleted once seeded: the table's size is the honest answer to *how much
    of the catalogue are we missing*, and empty means nothing is.
    """

    __tablename__ = "reve_unmirrored_connectors"
    __table_args__ = (
        UniqueConstraint(
            "evse_id", "connector_id", name="uq_reve_unmirrored_evse_connector"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # REVE's internal ids, matching evses.source_id and connectors.source_id.
    # Not the eMI3 identifier: the tariff feed never sends that, so the operator
    # cannot be recovered from these and a party_id-filtered repair is not open
    # to us.
    evse_id: Mapped[str] = mapped_column(Text, nullable=False)
    connector_id: Mapped[str] = mapped_column(Text, nullable=False)
    tariff_raw: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
