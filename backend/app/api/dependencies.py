from typing import cast

from fastapi import Request

from app.core.config import Settings, get_settings
from app.services.chat import ChatOrchestrator
from app.services.readiness import ReadinessProbe
from app.services.sessions import SessionStore


async def get_readiness_probe(request: Request) -> ReadinessProbe:
    return cast(ReadinessProbe, request.app.state.readiness_probe)


async def get_session_store(request: Request) -> SessionStore:
    return cast(SessionStore, request.app.state.session_store)


async def get_runtime_settings() -> Settings:
    return get_settings()


async def get_chat_orchestrator(request: Request) -> ChatOrchestrator | None:
    return cast(ChatOrchestrator | None, request.app.state.chat_orchestrator)
