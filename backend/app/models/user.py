import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from fastapi_users.db import SQLAlchemyBaseOAuthAccountTableUUID, SQLAlchemyBaseUserTableUUID
from fastapi_users_db_sqlalchemy.generics import GUID
from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OAuthAccount(SQLAlchemyBaseOAuthAccountTableUUID, Base):
    __tablename__ = "oauth_account"
    __table_args__ = (
        UniqueConstraint("oauth_name", "account_id", name="uq_oauth_provider_account"),
    )

    if TYPE_CHECKING:
        user_id: uuid.UUID
    else:
        user_id: Mapped[uuid.UUID] = mapped_column(
            GUID, ForeignKey("users.id", ondelete="cascade"), nullable=False
        )


class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "users"

    if TYPE_CHECKING:
        email: str
    else:
        email: Mapped[str] = mapped_column(CITEXT, unique=True, index=True, nullable=False)

    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    picture_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    oauth_accounts: Mapped[list[OAuthAccount]] = relationship(lazy="joined")
