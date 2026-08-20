from typing import Literal

from pydantic import BaseModel


class LiveResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ComponentStatus(BaseModel):
    ready: bool
    code: str


class ReadyResponse(BaseModel):
    ready: bool
    components: dict[str, ComponentStatus]
