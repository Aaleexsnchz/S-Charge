from unittest.mock import AsyncMock

from httpx import AsyncClient

from tests.auth.conftest import PASSWORD

EMAIL = "carol@example.com"
NAME = "Carol"


async def _register_capture_token(
    client: AsyncClient, mock_verification_email: AsyncMock
) -> str:
    resp = await client.post(
        "/api/auth/register",
        json={"email": EMAIL, "password": PASSWORD, "name": NAME},
    )
    assert resp.status_code == 201
    mock_verification_email.assert_called_once()
    return mock_verification_email.call_args.args[1]


async def test_request_verify_token_resends_email(
    client: AsyncClient, mock_verification_email: AsyncMock
) -> None:
    await _register_capture_token(client, mock_verification_email)
    mock_verification_email.reset_mock()

    resp = await client.post("/api/auth/request-verify-token", json={"email": EMAIL})
    assert resp.status_code == 202
    mock_verification_email.assert_called_once()
    assert mock_verification_email.call_args.args[0] == EMAIL


async def test_request_verify_token_unknown_email_silent(
    client: AsyncClient, mock_verification_email: AsyncMock
) -> None:
    resp = await client.post(
        "/api/auth/request-verify-token", json={"email": "ghost@example.com"}
    )
    assert resp.status_code == 202
    mock_verification_email.assert_not_called()


async def test_already_verified_user_cannot_reverify(
    client: AsyncClient, mock_verification_email: AsyncMock
) -> None:
    token = await _register_capture_token(client, mock_verification_email)

    first = await client.post("/api/auth/verify", json={"token": token})
    assert first.status_code == 200

    second = await client.post("/api/auth/verify", json={"token": token})
    assert second.status_code == 400
    assert second.json()["detail"] == "VERIFY_USER_ALREADY_VERIFIED"
