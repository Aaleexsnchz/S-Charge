from unittest.mock import patch

import pytest

from app.config import settings
from app.services.email import send_reset_password_email, send_verification_email


@pytest.fixture
def _api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "resend_api_key", "test_key")
    monkeypatch.setattr(settings, "mail_from", "noreply@test")
    monkeypatch.setattr(settings, "app_base_url", "https://app.test")


async def test_send_verification_email_calls_resend(_api_key: None) -> None:
    with patch("app.services.email.resend.Emails.send") as mock_send:
        await send_verification_email("user@example.com", "tok123")

    mock_send.assert_called_once()
    payload = mock_send.call_args[0][0]
    assert payload["from"] == "noreply@test"
    assert payload["to"] == ["user@example.com"]
    assert "https://app.test/verify-email?token=tok123" in payload["text"]


async def test_send_reset_password_email_calls_resend(_api_key: None) -> None:
    with patch("app.services.email.resend.Emails.send") as mock_send:
        await send_reset_password_email("user@example.com", "rtok")

    mock_send.assert_called_once()
    payload = mock_send.call_args[0][0]
    assert "https://app.test/reset-password?token=rtok" in payload["text"]


async def test_send_swallows_resend_errors(_api_key: None) -> None:
    with patch("app.services.email.resend.Emails.send", side_effect=RuntimeError("boom")):
        await send_verification_email("user@example.com", "tok")


async def test_send_skipped_when_api_key_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "resend_api_key", "")
    with patch("app.services.email.resend.Emails.send") as mock_send:
        await send_verification_email("user@example.com", "tok")

    mock_send.assert_not_called()
