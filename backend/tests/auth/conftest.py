from collections.abc import Iterator
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

PASSWORD = "long-enough-password-123"


async def register(
    client: AsyncClient, email: str, *, password: str = PASSWORD, name: str = "Test"
) -> None:
    resp = await client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "name": name},
    )
    assert resp.status_code == 201


@pytest.fixture
def mock_verification_email() -> Iterator[AsyncMock]:
    """Replaces the root conftest's mock so a test can read the sent token."""
    with patch(
        "app.services.user_manager.send_verification_email",
        new_callable=AsyncMock,
    ) as mock:
        yield mock
