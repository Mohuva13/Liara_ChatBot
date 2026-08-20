from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import get_readiness_probe
from app.models.health import LiveResponse, ReadyResponse
from app.services.readiness import ReadinessProbe

router = APIRouter(tags=["health"])


@router.get("/health/live", response_model=LiveResponse)
async def live() -> LiveResponse:
    return LiveResponse()


@router.get(
    "/health/ready",
    response_model=ReadyResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadyResponse}},
)
async def ready(
    response: Response,
    probe: Annotated[ReadinessProbe, Depends(get_readiness_probe)],
) -> ReadyResponse:
    report = await probe.check()
    if not report.ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return report
