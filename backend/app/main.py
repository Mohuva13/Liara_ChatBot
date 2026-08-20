from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.health import router as health_router
from app.api.v1.chat import router as chat_router
from app.api.v1.sessions import router as sessions_router
from app.core.config import Settings, get_settings
from app.core.errors import APIError, ErrorBody, ErrorResponse
from app.core.middleware import RequestBodyLimitMiddleware, SecurityHeadersMiddleware
from app.services.readiness import ReadinessProbe
from app.services.sessions import RedisSessionStore, SessionStore


def create_app(
    *,
    settings: Settings | None = None,
    readiness_probe: ReadinessProbe | None = None,
    session_store: SessionStore | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    app = FastAPI(
        title="Liara Documentation Assistant API",
        version="0.1.0",
        docs_url="/docs" if resolved_settings.app_env != "production" else None,
        redoc_url=None,
    )
    app.state.readiness_probe = readiness_probe or ReadinessProbe(resolved_settings)
    app.state.session_store = session_store or RedisSessionStore(resolved_settings)

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
    app.include_router(sessions_router)
    app.include_router(chat_router)
    return app


app = create_app()
