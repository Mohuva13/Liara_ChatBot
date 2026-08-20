from collections.abc import AsyncIterator, Sequence

import pytest

from app.providers.base import (
    CompletionResult,
    ProviderFailure,
    ProviderMessage,
    ProviderUsage,
    StreamDelta,
)
from app.providers.resilient import ProviderTarget, ResilientProvider


class StubProvider:
    def __init__(self, *, failure: str | None = None, text: str = "ok") -> None:
        self.failure = failure
        self.text = text
        self.calls = 0

    def _fail(self) -> None:
        self.calls += 1
        if self.failure:
            raise ProviderFailure(self.failure, retryable=True)

    async def complete(
        self,
        messages: Sequence[ProviderMessage],
        *,
        model: str,
        max_output_tokens: int,
        request_id: str,
        json_mode: bool = False,
    ) -> CompletionResult:
        self._fail()
        return CompletionResult(
            text=self.text,
            finish_reason="stop",
            usage=ProviderUsage(input_tokens=2, output_tokens=1),
        )

    async def stream(
        self,
        messages: Sequence[ProviderMessage],
        *,
        model: str,
        max_output_tokens: int,
        request_id: str,
    ) -> AsyncIterator[StreamDelta]:
        self._fail()
        yield StreamDelta(text=self.text)
        yield StreamDelta(
            finish_reason="stop", usage=ProviderUsage(input_tokens=2, output_tokens=1)
        )

    async def embed(
        self,
        inputs: Sequence[str],
        *,
        model: str,
        dimensions: int | None,
        request_id: str,
    ) -> list[list[float]]:
        self._fail()
        return [[0.1] for _ in inputs]


def resilient(primary: StubProvider, backup: StubProvider) -> ResilientProvider:
    return ResilientProvider(
        [ProviderTarget("primary", primary), ProviderTarget("backup", backup)],
        failure_threshold=1,
        reset_seconds=60,
        concurrency_limit=2,
        queue_timeout_seconds=1,
    )


@pytest.mark.asyncio
async def test_quota_failure_fails_over_and_attributes_usage() -> None:
    primary = StubProvider(failure="provider_quota_exhausted")
    backup = StubProvider(text="backup")

    result = await resilient(primary, backup).complete(
        [ProviderMessage(role="user", content="test")],
        model="model",
        max_output_tokens=10,
        request_id="request",
    )

    assert result.text == "backup"
    assert result.usage.provider_name == "backup"
    assert primary.calls == backup.calls == 1


@pytest.mark.asyncio
async def test_non_transient_rejection_does_not_fail_over() -> None:
    primary = StubProvider(failure="provider_rejected_request")
    backup = StubProvider(text="must-not-run")

    with pytest.raises(ProviderFailure, match="provider_rejected_request"):
        await resilient(primary, backup).complete(
            [ProviderMessage(role="user", content="test")],
            model="model",
            max_output_tokens=10,
            request_id="request",
        )

    assert backup.calls == 0


@pytest.mark.asyncio
async def test_open_circuit_skips_failed_primary_on_following_request() -> None:
    primary = StubProvider(failure="provider_auth_failed")
    backup = StubProvider(text="backup")
    provider = resilient(primary, backup)

    for _ in range(2):
        result = await provider.complete(
            [ProviderMessage(role="user", content="test")],
            model="model",
            max_output_tokens=10,
            request_id="request",
        )
        assert result.text == "backup"

    assert primary.calls == 1
    assert backup.calls == 2


@pytest.mark.asyncio
async def test_stream_failover_never_emits_partial_primary_output() -> None:
    primary = StubProvider(failure="provider_unavailable", text="partial")
    backup = StubProvider(text="safe")

    deltas = [
        delta
        async for delta in resilient(primary, backup).stream(
            [ProviderMessage(role="user", content="test")],
            model="model",
            max_output_tokens=10,
            request_id="request",
        )
    ]

    assert "".join(delta.text for delta in deltas) == "safe"
    assert deltas[-1].usage is not None
    assert deltas[-1].usage.provider_name == "backup"
