from collections.abc import AsyncIterator

import httpx2
import pytest
import pytest_asyncio

from app.api.dependencies import get_runtime_settings
from app.core.config import Settings
from app.main import create_app
from app.models.health import ComponentStatus, ReadyResponse


class FakeReadinessProbe:
    def __init__(self, ready: bool) -> None:
        self.ready = ready

    async def check(self) -> ReadyResponse:
        component = ComponentStatus(
            ready=self.ready,
            code="ok" if self.ready else "unreachable",
        )
        return ReadyResponse(
            ready=self.ready,
            components={
                "postgres": component,
                "corpus": component,
                "redis": component,
                "provider": component,
            },
        )


class FakeSessionStore:
    async def create(self) -> str:
        return "test-session-identifier-1234567890"

    async def delete(self, session_id: str) -> bool:
        return bool(session_id)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        max_user_input_chars=100,
        max_request_bytes=1024,
    )


@pytest_asyncio.fixture
async def ready_client(settings: Settings) -> AsyncIterator[httpx2.AsyncClient]:
    async def override_settings() -> Settings:
        return settings

    app = create_app(
        settings=settings,
        readiness_probe=FakeReadinessProbe(ready=True),  # type: ignore[arg-type]
        session_store=FakeSessionStore(),
    )
    app.dependency_overrides[get_runtime_settings] = override_settings
    transport = httpx2.ASGITransport(app=app)
    async with httpx2.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        yield client


@pytest_asyncio.fixture
async def unavailable_client(
    settings: Settings,
) -> AsyncIterator[httpx2.AsyncClient]:
    async def override_settings() -> Settings:
        return settings

    app = create_app(
        settings=settings,
        readiness_probe=FakeReadinessProbe(False),  # type: ignore[arg-type]
        session_store=FakeSessionStore(),
    )
    app.dependency_overrides[get_runtime_settings] = override_settings
    transport = httpx2.ASGITransport(app=app)
    async with httpx2.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        yield client
