import httpx2
import pytest


@pytest.mark.asyncio
async def test_liveness_is_lightweight(
    unavailable_client: httpx2.AsyncClient,
) -> None:
    response = await unavailable_client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-content-type-options"] == "nosniff"
    assert len(response.headers["x-request-id"]) == 32


@pytest.mark.asyncio
async def test_readiness_uses_service_status(
    unavailable_client: httpx2.AsyncClient,
) -> None:
    response = await unavailable_client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["ready"] is False
    assert response.json()["components"]["corpus"]["code"] == "unreachable"


@pytest.mark.asyncio
async def test_readiness_returns_ok_when_every_component_is_ready(
    ready_client: httpx2.AsyncClient,
) -> None:
    response = await ready_client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["ready"] is True
