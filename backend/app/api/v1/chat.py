from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import (
    get_chat_orchestrator,
    get_readiness_probe,
    get_runtime_settings,
)
from app.core.config import Settings
from app.core.errors import APIError, ErrorResponse
from app.models.chat import ChatStreamRequest
from app.services.chat import ChatOrchestrator, ChatPreparationError
from app.services.readiness import ReadinessProbe
from app.services.sessions import SessionStoreUnavailable

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
    request: Request,
    probe: Annotated[ReadinessProbe, Depends(get_readiness_probe)],
    settings: Annotated[Settings, Depends(get_runtime_settings)],
    orchestrator: Annotated[ChatOrchestrator | None, Depends(get_chat_orchestrator)],
) -> StreamingResponse:
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

    if orchestrator is None:
        raise APIError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="chat_pipeline_unavailable",
            message="مسیر پاسخ مستند هنوز فعال نشده است.",
        )
    try:
        prepared = await orchestrator.prepare(
            payload,
            request_id=request.state.request_id,
            rate_identity=(
                f"{payload.session_id}:chat:"
                f"{request.headers.get('x-client-id', 'unknown')[:128]}"
            ),
        )
    except ChatPreparationError as error:
        raise APIError(
            status_code=error.status_code,
            code=error.code,
            message=error.message,
            headers=error.headers,
        ) from error
    except SessionStoreUnavailable as error:
        raise APIError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="session_store_unavailable",
            message="سرویس نشست موقتاً در دسترس نیست.",
        ) from error
    return StreamingResponse(
        orchestrator.stream(prepared),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store",
            "X-Accel-Buffering": "no",
        },
    )
