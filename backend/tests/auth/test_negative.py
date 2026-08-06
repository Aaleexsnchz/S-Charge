from app.services.user_manager import MIN_PASSWORD_LENGTH
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
    assert str(MIN_PASSWORD_LENGTH) in detail["reason"]


async def test_register_password_one_short_of_minimum_rejected(
    client: AsyncClient,
) -> None:
    resp = await client.post(
        "/api/auth/register",
        json={
            "email": EMAIL,
            "password": "a" * (MIN_PASSWORD_LENGTH - 1),
            "name": "Bob",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "REGISTER_INVALID_PASSWORD"


async def test_register_password_at_minimum_accepted(client: AsyncClient) -> None:
    await _register(client, EMAIL, "a" * MIN_PASSWORD_LENGTH)


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


async def test_login_unverified_user_blocked(client: AsyncClient) -> None:
    await _register(client, EMAIL, PASSWORD)

    resp = await client.post(
        "/api/auth/login",
        data={"username": EMAIL, "password": PASSWORD},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "LOGIN_USER_NOT_VERIFIED"


async def test_verify_with_tampered_token(client: AsyncClient) -> None:
    resp = await client.post("/api/auth/verify", json={"token": "not-a-valid-jwt"})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "VERIFY_USER_BAD_TOKEN"


async def test_reset_with_tampered_token(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/auth/reset-password",
        json={"token": "not-a-valid-jwt", "password": "long-enough-password-123"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "RESET_PASSWORD_BAD_TOKEN"
