from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.health import router as health_router
from app.api.metrics import router as metrics_router
from app.api.v1.chat import router as chat_router
from app.api.v1.sessions import router as sessions_router
from app.core.config import Settings, get_settings
from app.core.errors import APIError, ErrorBody, ErrorResponse
from app.core.logging import configure_logging
from app.core.middleware import (
    InternalAuthMiddleware,
    RequestBodyLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.tracing import configure_tracing
from app.services.chat import ChatOrchestrator, build_chat_orchestrator
from app.services.readiness import ReadinessProbe
from app.services.sessions import RedisSessionStore, SessionStore


def create_app(
    *,
    settings: Settings | None = None,
    readiness_probe: ReadinessProbe | None = None,
    session_store: SessionStore | None = None,
    chat_orchestrator: ChatOrchestrator | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)

    @asynccontextmanager
    async def lifespan(runtime_app: FastAPI) -> AsyncIterator[None]:
        yield
        orchestrator = getattr(runtime_app.state, "chat_orchestrator", None)
        if orchestrator is not None:
            await orchestrator.aclose()
        tracer_provider = getattr(runtime_app.state, "tracer_provider", None)
        if tracer_provider is not None:
            tracer_provider.shutdown()

    app = FastAPI(
        title="Liara Documentation Assistant API",
        version="0.1.0",
        docs_url="/docs" if resolved_settings.app_env != "production" else None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.readiness_probe = readiness_probe or ReadinessProbe(resolved_settings)
    app.state.session_store = session_store or RedisSessionStore(resolved_settings)
    app.state.chat_orchestrator = chat_orchestrator or build_chat_orchestrator(
        resolved_settings
    )
    app.state.tracer_provider = configure_tracing(app, resolved_settings)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID"],
    )
    app.add_middleware(
        RequestBodyLimitMiddleware,
        max_bytes=resolved_settings.max_request_bytes,
    )
    app.add_middleware(
        InternalAuthMiddleware,
        token=(
            resolved_settings.api_internal_token.get_secret_value()
            if resolved_settings.api_internal_token is not None
            else None
        ),
    )
    # Added last so rejected private-hop requests also receive request IDs,
    # security headers, structured telemetry, and bounded metrics.
    app.add_middleware(SecurityHeadersMiddleware)

    @app.exception_handler(APIError)
    async def handle_api_error(request: Request, error: APIError) -> JSONResponse:
        payload = ErrorResponse(
            error=ErrorBody(
                code=error.code,
                message=error.message,
                request_id=request.state.request_id,
                details=error.details,
            )
        )
        return JSONResponse(
            status_code=error.status_code,
            content=payload.model_dump(mode="json"),
            headers=error.headers,
        )

    app.include_router(health_router)
    app.include_router(metrics_router)
    app.include_router(sessions_router)
    app.include_router(chat_router)
    return app


app = create_app()
