from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from app.main import app
from httpx import AsyncClient

PUBLIC_PREFIXES = ("/api/health", "/api/auth/")


def _protected_routes() -> list[tuple[str, str]]:
    """Every `/api` route that is not deliberately public, as (method, path).

    Read from the OpenAPI schema rather than ``app.routes``, which holds
    opaque ``_IncludedRouter`` entries instead of the sub-routers' own routes.
    Derived from the app either way, so a router mounted without the
    authentication dependency fails this module instead of shipping open.
    """
    return sorted(
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        if path.startswith("/api") and not path.startswith(PUBLIC_PREFIXES)
        for method in operations
        if method.upper() not in {"HEAD", "OPTIONS"}
    )


PROTECTED_ROUTES = _protected_routes()


def test_the_route_inventory_is_not_empty() -> None:
    """Guards the guard: a path-filter typo would silently test nothing."""
    assert len(PROTECTED_ROUTES) >= 5


@pytest.mark.parametrize(("method", "path"), PROTECTED_ROUTES)
async def test_route_requires_authentication(
    client: AsyncClient, method: str, path: str
) -> None:
    url = path.replace("{point_id}", str(uuid4())).replace("{id}", str(uuid4()))

    response = await client.request(method, url, json={})

    assert response.status_code == 401, (
        f"{method} {path} answered {response.status_code} without a session"
    )


async def test_a_real_session_cookie_opens_the_gate(client: AsyncClient) -> None:
    """The other tests reject; this one admits, over the real credential path.

    The ``auth_client`` fixture overrides the dependency, so without this the
    suite would still pass if the gate rejected every caller.
    """
    with patch(
        "app.services.user_manager.send_verification_email", new_callable=AsyncMock
    ) as send:
        register = await client.post(
            "/api/auth/register",
            json={"email": "gate@example.com", "password": "long-enough-password-123"},
        )
    assert register.status_code == 201

    verify = await client.post(
        "/api/auth/verify", json={"token": send.call_args.args[1]}
    )
    assert verify.status_code == 200

    login = await client.post(
        "/api/auth/login",
        data={"username": "gate@example.com", "password": "long-enough-password-123"},
    )
    assert login.status_code == 204

    assert (await client.get("/api/points/map")).status_code == 200
    assert (await client.get("/api/vehicles")).status_code == 200
