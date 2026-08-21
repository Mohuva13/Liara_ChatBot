from typing import Literal

from pydantic import BaseModel, Field


class SessionTurn(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(max_length=20000)
    outcome: str | None = None
    source_ids: list[str] = Field(default_factory=list, max_length=12)


class IssueState(BaseModel):
    key: str | None = None
    failure_count: int = Field(default=0, ge=0, le=20)


class SessionState(BaseModel):
    schema_version: int = 2
    summary: str = Field(default="", max_length=4000)
    turns: list[SessionTurn] = Field(default_factory=list)
    issue: IssueState = Field(default_factory=IssueState)


class ReservationResult(BaseModel):
    acquired: bool
    status: Literal["in_progress", "complete"]
