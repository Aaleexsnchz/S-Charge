from collections.abc import AsyncIterator, Iterator
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
import pytest_asyncio
from fastapi_users.router.oauth import CSRF_TOKEN_COOKIE_NAME, generate_state_token
from httpx import AsyncClient
from httpx_oauth.oauth2 import OAuth2Token
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import OAuthAccount, User
from app.routers.auth import google_client
from app.utils.auth_backend import COOKIE_NAME

CALLBACK_URL = "/api/auth/google/callback"
GOOGLE_ACCOUNT_ID = "118452365478912345678"
GOOGLE_EMAIL = "oauth_user@example.com"
EXISTING_PASSWORD = "long-enough-password-123"
CSRF_VALUE = "test_csrf_token_value"


def _state_for(csrf: str) -> str:
    return generate_state_token({"csrftoken": csrf}, settings.secret_key)


def _prime_csrf(client: AsyncClient, csrf: str = CSRF_VALUE) -> None:
    client.cookies.set(CSRF_TOKEN_COOKIE_NAME, csrf)


@pytest.fixture(autouse=True)
def mock_google_calls() -> Iterator[None]:
    """Replace the outbound Google HTTP calls with deterministic stand-ins."""
    access_token = OAuth2Token({"access_token": "fake_access_token", "token_type": "bearer"})
    with (
        patch.object(google_client, "get_access_token", AsyncMock(return_value=access_token)),
        patch.object(
            google_client,
            "get_id_email",
            AsyncMock(return_value=(GOOGLE_ACCOUNT_ID, GOOGLE_EMAIL)),
        ),
    ):
        yield


@pytest_asyncio.fixture(loop_scope="session")
async def fresh_client(client: AsyncClient) -> AsyncIterator[AsyncClient]:
    """Per-test client with a clean cookie jar.

    The shared client fixture outlives cookie mutations from earlier tests
    within a module; OAuth state cookies and session cookies must not bleed
    between scenarios."""
    client.cookies.clear()
    yield client


async def test_oauth_first_time_user(fresh_client: AsyncClient, db_session: AsyncSession) -> None:
    _prime_csrf(fresh_client)
    resp = await fresh_client.get(
        CALLBACK_URL,
        params={"code": "fake_code", "state": _state_for(CSRF_VALUE)},
        follow_redirects=False,
    )

    assert resp.status_code == 303
    assert resp.headers["location"] == "/profile"
    assert COOKIE_NAME in fresh_client.cookies

    user_row = (
        (await db_session.execute(select(User).filter_by(email=GOOGLE_EMAIL))).unique().scalar_one()
    )
    assert isinstance(user_row.id, UUID)
    assert user_row.is_verified is True

    oauth_rows = (
        (await db_session.execute(select(OAuthAccount).filter_by(user_id=user_row.id)))
        .scalars()
        .all()
    )
    assert len(oauth_rows) == 1
    assert oauth_rows[0].oauth_name == "google"
    assert oauth_rows[0].account_id == GOOGLE_ACCOUNT_ID
    assert oauth_rows[0].account_email == GOOGLE_EMAIL


async def test_oauth_returning_user_matches_by_provider_id(
    fresh_client: AsyncClient, db_session: AsyncSession
) -> None:
    # First sign-in provisions the row.
    _prime_csrf(fresh_client)
    await fresh_client.get(
        CALLBACK_URL,
        params={"code": "c1", "state": _state_for(CSRF_VALUE)},
        follow_redirects=False,
    )

    # Fresh browser session (new CSRF, old session cookie cleared).
    fresh_client.cookies.clear()
    _prime_csrf(fresh_client)

    resp = await fresh_client.get(
        CALLBACK_URL,
        params={"code": "c2", "state": _state_for(CSRF_VALUE)},
        follow_redirects=False,
    )
    assert resp.status_code == 303

    users = (
        (await db_session.execute(select(User).filter_by(email=GOOGLE_EMAIL)))
        .unique()
        .scalars()
        .all()
    )
    assert len(users) == 1

    oauth_rows = (
        (await db_session.execute(select(OAuthAccount).filter_by(account_id=GOOGLE_ACCOUNT_ID)))
        .scalars()
        .all()
    )
    assert len(oauth_rows) == 1


async def test_oauth_links_to_existing_password_user(
    fresh_client: AsyncClient, db_session: AsyncSession
) -> None:
    register_resp = await fresh_client.post(
        "/api/auth/register",
        json={"email": GOOGLE_EMAIL, "password": EXISTING_PASSWORD, "name": "Existing"},
    )
    assert register_resp.status_code == 201
    existing_id = register_resp.json()["id"]

    _prime_csrf(fresh_client)
    resp = await fresh_client.get(
        CALLBACK_URL,
        params={"code": "c", "state": _state_for(CSRF_VALUE)},
        follow_redirects=False,
    )
    assert resp.status_code == 303

    users = (
        (await db_session.execute(select(User).filter_by(email=GOOGLE_EMAIL)))
        .unique()
        .scalars()
        .all()
    )
    assert len(users) == 1
    assert str(users[0].id) == existing_id

    oauth_rows = (
        (await db_session.execute(select(OAuthAccount).filter_by(user_id=users[0].id)))
        .scalars()
        .all()
    )
    assert len(oauth_rows) == 1


async def test_oauth_state_mismatch_redirects_to_login_error(
    fresh_client: AsyncClient,
) -> None:
    _prime_csrf(fresh_client, csrf="wrong_value")
    resp = await fresh_client.get(
        CALLBACK_URL,
        params={"code": "c", "state": _state_for("correct_value")},
        follow_redirects=False,
    )

    assert resp.status_code == 303
    assert resp.headers["location"] == "/login?error=oauth_failed"
    assert COOKIE_NAME not in fresh_client.cookies
