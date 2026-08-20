from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True, slots=True)
class ProviderMessage:
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True, slots=True)
class ProviderUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    provider_name: str | None = None


@dataclass(frozen=True, slots=True)
class CompletionResult:
    text: str
    finish_reason: str
    usage: ProviderUsage
    request_id: str | None = None


@dataclass(frozen=True, slots=True)
class StreamDelta:
    text: str = ""
    finish_reason: str | None = None
    usage: ProviderUsage | None = None


class ProviderFailure(RuntimeError):
    def __init__(
        self,
        code: str,
        *,
        retryable: bool,
        status_code: int | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.retryable = retryable
        self.status_code = status_code


class AIProvider(Protocol):
    async def complete(
        self,
        messages: Sequence[ProviderMessage],
        *,
        model: str,
        max_output_tokens: int,
        request_id: str,
        json_mode: bool = False,
    ) -> CompletionResult: ...

    def stream(
        self,
        messages: Sequence[ProviderMessage],
        *,
        model: str,
        max_output_tokens: int,
        request_id: str,
    ) -> AsyncIterator[StreamDelta]: ...

    async def embed(
        self,
        inputs: Sequence[str],
        *,
        model: str,
        dimensions: int | None,
        request_id: str,
    ) -> list[list[float]]: ...
