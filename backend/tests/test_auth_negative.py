from httpx import AsyncClient

EMAIL = "bob@example.com"
PASSWORD = "long-enough-password-123"


async def _register(client: AsyncClient, email: str, password: str) -> None:
    resp = await client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "name": "Bob"},
    )
    assert resp.status_code == 201


async def test_register_duplicate_email(client: AsyncClient) -> None:
    await _register(client, EMAIL, PASSWORD)

    resp = await client.post(
        "/api/auth/register",
        json={"email": EMAIL, "password": PASSWORD, "name": "Bob"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "REGISTER_USER_ALREADY_EXISTS"


async def test_register_password_too_short(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/auth/register",
        json={"email": EMAIL, "password": "short", "name": "Bob"},
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["code"] == "REGISTER_INVALID_PASSWORD"
    assert "12" in detail["reason"]


async def test_login_wrong_password(client: AsyncClient) -> None:
    await _register(client, EMAIL, PASSWORD)

    resp = await client.post(
        "/api/auth/login",
        data={"username": EMAIL, "password": "wrong-password-value"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "LOGIN_BAD_CREDENTIALS"


async def test_login_unknown_email_returns_same_error(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/auth/login",
        data={"username": "nobody@example.com", "password": PASSWORD},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "LOGIN_BAD_CREDENTIALS"


async def test_me_without_cookie(client: AsyncClient) -> None:
    resp = await client.get("/api/users/me")
    assert resp.status_code == 401


async def test_me_with_malformed_cookie(client: AsyncClient) -> None:
    client.cookies.set("session", "not-a-valid-jwt")
    resp = await client.get("/api/users/me")
    assert resp.status_code == 401
