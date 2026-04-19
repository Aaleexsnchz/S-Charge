from httpx import AsyncClient

from app.utils.auth_backend import COOKIE_NAME

EMAIL = "alice@example.com"
PASSWORD = "long-enough-password-123"
NAME = "Alice"


async def test_auth_happy_flow(client: AsyncClient) -> None:
    register_resp = await client.post(
        "/api/auth/register",
        json={"email": EMAIL, "password": PASSWORD, "name": NAME},
    )
    assert register_resp.status_code == 201
    registered = register_resp.json()
    assert registered["email"] == EMAIL
    assert registered["name"] == NAME
    assert registered["is_active"] is True

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
