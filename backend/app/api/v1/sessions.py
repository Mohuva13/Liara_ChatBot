from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import get_runtime_settings, get_session_store
from app.core.config import Settings
from app.core.errors import APIError, ErrorResponse
from app.models.chat import SessionResponse
from app.services.sessions import SessionStore, SessionStoreUnavailable

router = APIRouter(prefix="/v1/sessions", tags=["sessions"])


@router.post(
    "",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErrorResponse}},
)
async def create_session(
    store: Annotated[SessionStore, Depends(get_session_store)],
    settings: Annotated[Settings, Depends(get_runtime_settings)],
) -> SessionResponse:
    try:
        session_id = await store.create()
    except SessionStoreUnavailable as error:
        raise APIError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="session_store_unavailable",
            message="سرویس نشست موقتاً در دسترس نیست.",
        ) from error
    return SessionResponse(
        session_id=session_id,
        expires_in_seconds=settings.session_ttl_seconds,
    )


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErrorResponse}},
)
async def delete_session(
    session_id: str,
    store: Annotated[SessionStore, Depends(get_session_store)],
) -> Response:
    try:
        await store.delete(session_id)
    except SessionStoreUnavailable as error:
        raise APIError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="session_store_unavailable",
            message="سرویس نشست موقتاً در دسترس نیست.",
        ) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
