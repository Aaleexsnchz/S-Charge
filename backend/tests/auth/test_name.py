from collections.abc import Iterator
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

EMAIL = "namer@example.com"
PASSWORD = "long-enough-password-123"


@pytest.fixture
def mock_verification_email() -> Iterator[AsyncMock]:
    with patch(
        "app.services.user_manager.send_verification_email",
        new_callable=AsyncMock,
    ) as mock:
        yield mock


@pytest.fixture
async def logged_in(
    client: AsyncClient, mock_verification_email: AsyncMock
) -> AsyncClient:
    register = await client.post(
        "/api/auth/register",
        json={"email": EMAIL, "password": PASSWORD, "name": "Alejandro"},
    )
    assert register.status_code == 201

    token = mock_verification_email.call_args.args[1]
    verify = await client.post("/api/auth/verify", json={"token": token})
    assert verify.status_code == 200

    login = await client.post(
        "/api/auth/login", data={"username": EMAIL, "password": PASSWORD}
    )
    assert login.status_code == 204
    return client


async def test_register_rejects_a_missing_name(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/auth/register",
        json={"email": EMAIL, "password": PASSWORD},
    )
    assert resp.status_code == 422


@pytest.mark.parametrize("name", ["", "   "])
async def test_register_rejects_a_blank_name(client: AsyncClient, name: str) -> None:
    resp = await client.post(
        "/api/auth/register",
        json={"email": EMAIL, "password": PASSWORD, "name": name},
    )
    assert resp.status_code == 422


async def test_register_strips_surrounding_whitespace(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/auth/register",
        json={"email": EMAIL, "password": PASSWORD, "name": "  Alejandro  "},
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Alejandro"


async def test_patch_me_sets_the_name(logged_in: AsyncClient) -> None:
    resp = await logged_in.patch("/api/users/me", json={"name": "  Alejandra  "})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Alejandra"
    assert (await logged_in.get("/api/users/me")).json()["name"] == "Alejandra"


@pytest.mark.parametrize("name", [None, "", "   "])
async def test_patch_me_refuses_to_clear_the_name(
    logged_in: AsyncClient, name: str | None
) -> None:
    resp = await logged_in.patch("/api/users/me", json={"name": name})
    assert resp.status_code == 422
    assert (await logged_in.get("/api/users/me")).json()["name"] == "Alejandro"


async def test_patch_me_leaves_an_omitted_name_alone(logged_in: AsyncClient) -> None:
    resp = await logged_in.patch("/api/users/me", json={"picture_url": None})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Alejandro"
