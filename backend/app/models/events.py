from typing import Literal

from pydantic import BaseModel


class SourcePayload(BaseModel):
    id: str
    title: str
    url: str
    section: str
    snippet: str
    source_commit: str


class UsagePayload(BaseModel):
    model_tier: Literal["small", "large", "none"]
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    cache_hit: bool = False
    provider_name: Literal["primary", "backup"] | None = None
    estimated_cost_usd: float = 0


class ChatEvent(BaseModel):
    type: Literal[
        "message_start",
        "status",
        "text_delta",
        "sources",
        "suggestions",
        "support",
        "usage",
        "message_end",
        "error",
    ]
    response_id: str | None = None
    session_id: str | None = None
    text: str | None = None
    sources: list[SourcePayload] | None = None
    suggestions: list[str] | None = None
    reason_code: str | None = None
    ticket_url: str | None = None
    summary: str | None = None
    usage: UsagePayload | None = None
    finish_reason: str | None = None
    outcome: str | None = None
    code: str | None = None
    message: str | None = None
    retryable: bool | None = None

    def to_sse(self) -> bytes:
        payload = self.model_dump_json(exclude_none=True)
        return f"event: {self.type}\ndata: {payload}\n\n".encode()
