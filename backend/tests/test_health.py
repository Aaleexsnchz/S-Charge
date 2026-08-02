from app.config import settings
from httpx import AsyncClient


async def test_health_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": settings.app_version}


async def test_health_reports_a_version(client: AsyncClient) -> None:
    """The deploy is only verifiable if the running build identifies itself."""
    response = await client.get("/api/health")

    assert response.json()["version"]
