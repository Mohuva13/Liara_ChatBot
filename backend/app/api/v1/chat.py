from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_readiness_probe, get_runtime_settings
from app.core.config import Settings
from app.core.errors import APIError, ErrorResponse
from app.models.chat import ChatStreamRequest
from app.services.readiness import ReadinessProbe

router = APIRouter(prefix="/v1/chat", tags=["chat"])


@router.post(
    "/stream",
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErrorResponse},
    },
)
async def stream_chat(
    payload: ChatStreamRequest,
    probe: Annotated[ReadinessProbe, Depends(get_readiness_probe)],
    settings: Annotated[Settings, Depends(get_runtime_settings)],
) -> None:
    if len(payload.text) > settings.max_user_input_chars:
        raise APIError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="input_too_long",
            message="طول پیام از حد مجاز بیشتر است.",
            details={"max_characters": settings.max_user_input_chars},
        )

    readiness = await probe.check()
    if not readiness.ready:
        unavailable = sorted(
            name
            for name, component in readiness.components.items()
            if not component.ready
        )
        raise APIError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="service_not_ready",
            message="دستیار هنوز برای پاسخ‌گویی آماده نیست.",
            details={"unavailable_components": unavailable},
        )

    raise APIError(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        code="chat_pipeline_unavailable",
        message="مسیر پاسخ مستند هنوز فعال نشده است.",
    )
