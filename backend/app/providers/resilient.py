import asyncio
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from dataclasses import dataclass, replace
from typing import TypeVar

from app.providers.base import (
    AIProvider,
    CompletionResult,
    ProviderFailure,
    ProviderMessage,
    StreamDelta,
)

T = TypeVar("T")

FAILOVER_CODES = {
    "provider_auth_failed",
    "provider_busy",
    "provider_quota_exhausted",
    "provider_rate_limited",
    "provider_timeout",
    "provider_unavailable",
}


@dataclass(frozen=True, slots=True)
class ProviderTarget:
    name: str
    provider: AIProvider


@dataclass(slots=True)
class CircuitState:
    failures: int = 0
    opened_at: float | None = None


class ResilientProvider:
    def __init__(
        self,
        targets: Sequence[ProviderTarget],
        *,
        failure_threshold: int,
        reset_seconds: float,
        concurrency_limit: int,
        queue_timeout_seconds: float,
    ) -> None:
        if not targets:
            raise ValueError("at least one provider target is required")
        self._targets = tuple(targets)
        self._failure_threshold = failure_threshold
        self._reset_seconds = reset_seconds
        self._queue_timeout_seconds = queue_timeout_seconds
        self._circuits = {target.name: CircuitState() for target in targets}
        self._bulkhead = asyncio.Semaphore(concurrency_limit)

    def _available_targets(self) -> list[ProviderTarget]:
        now = time.monotonic()
        available: list[ProviderTarget] = []
        for target in self._targets:
            state = self._circuits[target.name]
            if state.opened_at is None:
                available.append(target)
                continue
            if now - state.opened_at >= self._reset_seconds:
                state.opened_at = None
                # Half-open probe: one failed call re-opens immediately, while
                # a successful call resets the circuit through _success().
                state.failures = self._failure_threshold - 1
                available.append(target)
        return available

    def _success(self, target: ProviderTarget) -> None:
        state = self._circuits[target.name]
        state.failures = 0
        state.opened_at = None

    def _failure(self, target: ProviderTarget, error: ProviderFailure) -> None:
        if error.code not in FAILOVER_CODES:
            return
        state = self._circuits[target.name]
        state.failures += 1
        if state.failures >= self._failure_threshold:
            state.opened_at = time.monotonic()

    async def _with_bulkhead(self, operation: Callable[[], Awaitable[T]]) -> T:
        acquired = False
        try:
            async with asyncio.timeout(self._queue_timeout_seconds):
                await self._bulkhead.acquire()
                acquired = True
            return await operation()
        except TimeoutError as error:
            raise ProviderFailure("provider_busy", retryable=True) from error
        finally:
            if acquired:
                self._bulkhead.release()

    async def _attempt(
        self, operation: Callable[[ProviderTarget], Awaitable[T]]
    ) -> tuple[T, str]:
        targets = self._available_targets()
        if not targets:
            raise ProviderFailure("provider_circuit_open", retryable=True)
        last_error: ProviderFailure | None = None
        for target in targets:
            try:
                result = await operation(target)
                self._success(target)
                return result, target.name
            except ProviderFailure as error:
                self._failure(target, error)
                last_error = error
                if error.code not in FAILOVER_CODES:
                    raise
        assert last_error is not None
        raise last_error

    async def complete(
        self,
        messages: Sequence[ProviderMessage],
        *,
        model: str,
        max_output_tokens: int,
        request_id: str,
        json_mode: bool = False,
    ) -> CompletionResult:
        async def run() -> CompletionResult:
            result, provider_name = await self._attempt(
                lambda target: target.provider.complete(
                    messages,
                    model=model,
                    max_output_tokens=max_output_tokens,
                    request_id=request_id,
                    json_mode=json_mode,
                )
            )
            return replace(
                result,
                usage=replace(result.usage, provider_name=provider_name),
            )

        return await self._with_bulkhead(run)

    async def _collect_stream(
        self,
        target: ProviderTarget,
        messages: Sequence[ProviderMessage],
        *,
        model: str,
        max_output_tokens: int,
        request_id: str,
    ) -> list[StreamDelta]:
        return [
            delta
            async for delta in target.provider.stream(
                messages,
                model=model,
                max_output_tokens=max_output_tokens,
                request_id=request_id,
            )
        ]

    async def stream(
        self,
        messages: Sequence[ProviderMessage],
        *,
        model: str,
        max_output_tokens: int,
        request_id: str,
    ) -> AsyncIterator[StreamDelta]:
        async def run() -> tuple[list[StreamDelta], str]:
            return await self._attempt(
                lambda target: self._collect_stream(
                    target,
                    messages,
                    model=model,
                    max_output_tokens=max_output_tokens,
                    request_id=request_id,
                )
            )

        deltas, provider_name = await self._with_bulkhead(run)
        for delta in deltas:
            yield replace(
                delta,
                usage=(
                    replace(delta.usage, provider_name=provider_name)
                    if delta.usage is not None
                    else None
                ),
            )

    async def embed(
        self,
        inputs: Sequence[str],
        *,
        model: str,
        dimensions: int | None,
        request_id: str,
    ) -> list[list[float]]:
        async def run() -> list[list[float]]:
            result, _ = await self._attempt(
                lambda target: target.provider.embed(
                    inputs,
                    model=model,
                    dimensions=dimensions,
                    request_id=request_id,
                )
            )
            return result

        return await self._with_bulkhead(run)

    async def aclose(self) -> None:
        closed: set[int] = set()
        for target in self._targets:
            provider_id = id(target.provider)
            if provider_id in closed:
                continue
            closed.add(provider_id)
            close = getattr(target.provider, "aclose", None)
            if close is not None:
                await close()
