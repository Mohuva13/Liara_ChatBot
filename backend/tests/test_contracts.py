import asyncio
from collections.abc import AsyncIterator

import httpx2
import pytest

from app.core.config import Settings
from app.main import create_app
from app.models.events import ChatEvent
from app.models.health import ComponentStatus, ReadyResponse

VALID_CHAT_REQUEST = {
    "protocol_version": "1",
    "session_id": "test-session-identifier-1234567890",
    "message_id": "message-12345678",
    "text": "چطور یک برنامه Next.js را روی لیارا مستقر کنم؟",
    "surface": "page",
    "locale": "fa-IR",
}


class LocalSessionStore:
    async def create(self) -> str:
        return "test-session-identifier-1234567890"

    async def delete(self, session_id: str) -> bool:
        return True


class AlwaysReadyProbe:
    async def check(self) -> ReadyResponse:
        component = ComponentStatus(ready=True, code="ok")
        return ReadyResponse(
            ready=True,
            components={
                "postgres": component,
                "corpus": component,
                "redis": component,
                "provider": component,
            },
        )


class StreamingOrchestrator:
    async def prepare(
        self, payload: object, *, request_id: str, rate_identity: str | None = None
    ) -> object:
        return object()

    async def stream(self, prepared: object) -> AsyncIterator[bytes]:
        yield ChatEvent(type="message_start", response_id="response-id").to_sse()
        await asyncio.sleep(0.01)
        yield ChatEvent(type="status", text="در حال آزمایش stream…").to_sse()
        await asyncio.sleep(0.01)
        yield ChatEvent(
            type="message_end", finish_reason="stop", outcome="answered"
        ).to_sse()

    async def aclose(self) -> None:
        return None


@pytest.mark.asyncio
async def test_session_is_server_issued(ready_client: httpx2.AsyncClient) -> None:
    response = await ready_client.post("/v1/sessions")

    assert response.status_code == 201
    assert response.json()["session_id"].startswith("test-session-")
    assert response.json()["expires_in_seconds"] == 7200


@pytest.mark.asyncio
async def test_chat_fails_closed_before_grounded_pipeline_exists(
    ready_client: httpx2.AsyncClient,
) -> None:
    response = await ready_client.post(
        "/v1/chat/stream",
        json=VALID_CHAT_REQUEST,
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "chat_pipeline_unavailable"
    assert "answer" not in response.json()


@pytest.mark.asyncio
async def test_chat_reports_unavailable_dependencies(
    unavailable_client: httpx2.AsyncClient,
) -> None:
    response = await unavailable_client.post(
        "/v1/chat/stream",
        json=VALID_CHAT_REQUEST,
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_not_ready"
    assert response.json()["error"]["details"]["unavailable_components"] == [
        "corpus",
        "postgres",
        "provider",
        "redis",
    ]


@pytest.mark.asyncio
async def test_chat_rejects_oversized_input(
    ready_client: httpx2.AsyncClient,
) -> None:
    response = await ready_client.post(
        "/v1/chat/stream",
        json={**VALID_CHAT_REQUEST, "text": "الف" * 101},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "input_too_long"


@pytest.mark.asyncio
async def test_openapi_exposes_versioned_service_contract(
    ready_client: httpx2.AsyncClient,
) -> None:
    response = await ready_client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["version"] == "0.1.0"
    assert {
        "/health/live",
        "/health/ready",
        "/v1/chat/stream",
        "/v1/sessions",
        "/v1/sessions/{session_id}",
    } <= set(schema["paths"])

    request_schema = schema["components"]["schemas"]["ChatStreamRequest"]
    assert set(request_schema["required"]) == {
        "locale",
        "message_id",
        "protocol_version",
        "session_id",
        "surface",
        "text",
    }


@pytest.mark.asyncio
async def test_request_body_limit_rejects_before_parsing(
    ready_client: httpx2.AsyncClient,
) -> None:
    response = await ready_client.post(
        "/v1/chat/stream",
        content=b"{" + (b"x" * 2048),
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "request_too_large"
    assert response.headers["x-content-type-options"] == "nosniff"


@pytest.mark.asyncio
async def test_request_body_limit_does_not_cancel_streaming_response() -> None:
    app = create_app(
        settings=Settings(
            _env_file=None,
            app_env="test",
            max_request_bytes=1024,
        ),
        readiness_probe=AlwaysReadyProbe(),  # type: ignore[arg-type]
        session_store=LocalSessionStore(),
        chat_orchestrator=StreamingOrchestrator(),  # type: ignore[arg-type]
    )
    transport = httpx2.ASGITransport(app=app)
    async with httpx2.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        response = await client.post("/v1/chat/stream", json=VALID_CHAT_REQUEST)

    assert response.status_code == 200
    assert '"type":"message_start"' in response.text
    assert '"type":"message_end"' in response.text


@pytest.mark.asyncio
async def test_private_api_rejects_missing_internal_token() -> None:
    app = create_app(
        settings=Settings(
            _env_file=None,
            app_env="test",
            api_internal_token="private-placeholder-token",
        ),
        session_store=LocalSessionStore(),
    )
    transport = httpx2.ASGITransport(app=app)
    async with httpx2.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        denied = await client.post("/v1/sessions")
        allowed = await client.post(
            "/v1/sessions",
            headers={"x-internal-token": "private-placeholder-token"},
        )

    assert denied.status_code == 401
    assert denied.headers["x-content-type-options"] == "nosniff"
    assert allowed.status_code == 201
