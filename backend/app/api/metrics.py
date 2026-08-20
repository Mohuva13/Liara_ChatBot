import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Header, status
from fastapi.responses import PlainTextResponse

from app.api.dependencies import get_runtime_settings
from app.core.config import Settings
from app.core.errors import APIError
from app.core.metrics import metrics

router = APIRouter(tags=["operations"])


@router.get("/metrics", include_in_schema=False)
async def prometheus_metrics(
    settings: Annotated[Settings, Depends(get_runtime_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> PlainTextResponse:
    if not settings.metrics_enabled:
        raise APIError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="metrics_disabled",
            message="Not found",
        )
    if settings.metrics_bearer_token is not None:
        expected = f"Bearer {settings.metrics_bearer_token.get_secret_value()}"
        if authorization is None or not secrets.compare_digest(authorization, expected):
            raise APIError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="metrics_auth_failed",
                message="Unauthorized",
            )
    return PlainTextResponse(
        metrics.render(), media_type="text/plain; version=0.0.4; charset=utf-8"
    )
