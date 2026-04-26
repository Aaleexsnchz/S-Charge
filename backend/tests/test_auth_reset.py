from collections.abc import Iterator
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

EMAIL = "dave@example.com"
PASSWORD = "long-enough-password-123"
NEW_PASSWORD = "even-longer-new-password-321"
NAME = "Dave"


@pytest.fixture
def mock_reset_email() -> Iterator[AsyncMock]:
    with patch(
        "app.services.user_manager.send_reset_password_email",
        new_callable=AsyncMock,
    ) as mock:
        yield mock


async def _register_verified(client: AsyncClient, db_session: AsyncSession) -> None:
    resp = await client.post(
        "/api/auth/register",
        json={"email": EMAIL, "password": PASSWORD, "name": NAME},
    )
    assert resp.status_code == 201
    user = (await db_session.execute(select(User).filter_by(email=EMAIL))).unique().scalar_one()
    user.is_verified = True
    await db_session.commit()


async def test_reset_password_full_flow(
    client: AsyncClient, db_session: AsyncSession, mock_reset_email: AsyncMock
) -> None:
    await _register_verified(client, db_session)

    forgot_resp = await client.post("/api/auth/forgot-password", json={"email": EMAIL})
    assert forgot_resp.status_code == 202
    mock_reset_email.assert_called_once()
    token = mock_reset_email.call_args.args[1]

    reset_resp = await client.post(
        "/api/auth/reset-password",
        json={"token": token, "password": NEW_PASSWORD},
    )
    assert reset_resp.status_code == 200

    old_login = await client.post("/api/auth/login", data={"username": EMAIL, "password": PASSWORD})
    assert old_login.status_code == 400
    assert old_login.json()["detail"] == "LOGIN_BAD_CREDENTIALS"

    new_login = await client.post(
        "/api/auth/login", data={"username": EMAIL, "password": NEW_PASSWORD}
    )
    assert new_login.status_code == 204


async def test_forgot_password_unknown_email_returns_202_without_send(
    client: AsyncClient, mock_reset_email: AsyncMock
) -> None:
    resp = await client.post("/api/auth/forgot-password", json={"email": "ghost@example.com"})
    assert resp.status_code == 202
    mock_reset_email.assert_not_called()


async def test_reset_with_short_password_rejected(
    client: AsyncClient, db_session: AsyncSession, mock_reset_email: AsyncMock
) -> None:
    await _register_verified(client, db_session)

    await client.post("/api/auth/forgot-password", json={"email": EMAIL})
    token = mock_reset_email.call_args.args[1]

    resp = await client.post(
        "/api/auth/reset-password",
        json={"token": token, "password": "short"},
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["code"] == "RESET_PASSWORD_INVALID_PASSWORD"
    assert "12" in detail["reason"]
