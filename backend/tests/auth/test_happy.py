from unittest.mock import AsyncMock

from app.utils.auth_backend import COOKIE_NAME
from httpx import AsyncClient

from tests.auth.conftest import PASSWORD

EMAIL = "alice@example.com"
NAME = "Alice"


async def test_auth_happy_flow(
    client: AsyncClient, mock_verification_email: AsyncMock
) -> None:
    register_resp = await client.post(
        "/api/auth/register",
        json={"email": EMAIL, "password": PASSWORD, "name": NAME},
    )
    assert register_resp.status_code == 201
    registered = register_resp.json()
    assert registered["email"] == EMAIL
    assert registered["name"] == NAME
    assert registered["is_active"] is True
    assert registered["is_verified"] is False

    mock_verification_email.assert_called_once()
    verification_token = mock_verification_email.call_args.args[1]

    verify_resp = await client.post(
        "/api/auth/verify", json={"token": verification_token}
    )
    assert verify_resp.status_code == 200
    assert verify_resp.json()["is_verified"] is True

    login_resp = await client.post(
        "/api/auth/login",
        data={"username": EMAIL, "password": PASSWORD},
    )
    assert login_resp.status_code == 204
    assert COOKIE_NAME in client.cookies

    me_resp = await client.get("/api/users/me")
    assert me_resp.status_code == 200
    me = me_resp.json()
    assert me["email"] == EMAIL
    assert me["name"] == NAME
    assert me["id"] == registered["id"]

    logout_resp = await client.post("/api/auth/logout")
    assert logout_resp.status_code == 204
    assert COOKIE_NAME not in client.cookies

    me_after_logout = await client.get("/api/users/me")
    assert me_after_logout.status_code == 401
