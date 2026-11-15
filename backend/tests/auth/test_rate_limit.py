from app.routers.auth import LOGIN_LIMIT, MAIL_LIMIT
from httpx import AsyncClient

from tests.auth.conftest import PASSWORD

EMAIL = "rate@example.com"


def _count(limit: str) -> int:
    return int(limit.split("/")[0])


async def test_login_is_limited_after_the_allowance(client: AsyncClient) -> None:
    payload = {"username": EMAIL, "password": "wrong-password-value"}

    for _ in range(_count(LOGIN_LIMIT)):
        resp = await client.post("/api/auth/login", data=payload)
        assert resp.status_code == 400

    resp = await client.post("/api/auth/login", data=payload)
    assert resp.status_code == 429
    assert resp.json()["detail"] == "TOO_MANY_REQUESTS"
    assert int(resp.headers["retry-after"]) > 0


async def test_forgot_password_is_limited(client: AsyncClient) -> None:
    payload = {"email": EMAIL}

    for _ in range(_count(MAIL_LIMIT)):
        resp = await client.post("/api/auth/forgot-password", json=payload)
        assert resp.status_code == 202

    resp = await client.post("/api/auth/forgot-password", json=payload)
    assert resp.status_code == 429


async def test_limits_are_counted_per_path(client: AsyncClient) -> None:
    for _ in range(_count(MAIL_LIMIT) + 1):
        await client.post("/api/auth/forgot-password", json={"email": EMAIL})

    resp = await client.post(
        "/api/auth/login", data={"username": EMAIL, "password": PASSWORD}
    )
    assert resp.status_code != 429


async def test_unlimited_endpoints_are_untouched(client: AsyncClient) -> None:
    for _ in range(_count(LOGIN_LIMIT) + 5):
        resp = await client.get("/api/users/me")
        assert resp.status_code == 401
