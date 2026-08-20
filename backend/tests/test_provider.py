import json

import httpx
import pytest

from app.providers.base import ProviderFailure, ProviderMessage
from app.providers.openai_compat import OpenAICompatibleProvider


@pytest.mark.asyncio
async def test_openai_compatible_completion_contract() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["authorization"].startswith("Bearer ")
        body = json.loads(request.content)
        assert body["model"] == "small-model"
        assert body["response_format"] == {"type": "json_object"}
        return httpx.Response(
            200,
            headers={"x-request-id": "provider-request"},
            json={
                "choices": [
                    {
                        "message": {"content": '{"outcome":"answered"}'},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 12,
                    "completion_tokens": 4,
                    "prompt_tokens_details": {"cached_tokens": 3},
                },
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleProvider(
        base_url="https://provider.test/v1",
        api_key="test-placeholder-key",
        timeout_seconds=5,
        max_retries=0,
        client=client,
    )

    result = await provider.complete(
        [ProviderMessage(role="user", content="سلام")],
        model="small-model",
        max_output_tokens=100,
        request_id="request",
        json_mode=True,
    )

    assert result.finish_reason == "stop"
    assert result.usage.input_tokens == 12
    assert result.usage.output_tokens == 4
    assert result.usage.cached_tokens == 3
    assert result.request_id == "provider-request"
    await client.aclose()


@pytest.mark.asyncio
async def test_embedding_order_follows_provider_indices() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/embeddings"
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 1, "embedding": [0.3, 0.4]},
                    {"index": 0, "embedding": [0.1, 0.2]},
                ]
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleProvider(
        base_url="https://provider.test/v1",
        api_key="test-placeholder-key",
        timeout_seconds=5,
        client=client,
    )

    embeddings = await provider.embed(
        ["یک", "دو"],
        model="embedding-model",
        dimensions=2,
        request_id="request",
    )

    assert embeddings == [[0.1, 0.2], [0.3, 0.4]]
    await client.aclose()


@pytest.mark.asyncio
async def test_stream_requests_json_mode_and_usage() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["stream"] is True
        assert body["stream_options"] == {"include_usage": True}
        assert body["response_format"] == {"type": "json_object"}
        first = {"choices": [{"delta": {"content": '{"answer'}, "finish_reason": None}]}
        second = {
            "choices": [{"delta": {"content": '":1}'}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 2},
        }
        events = "\n\n".join(
            (
                f"data: {json.dumps(first)}",
                f"data: {json.dumps(second)}",
                "data: [DONE]",
            )
        )
        return httpx.Response(200, text=events)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleProvider(
        base_url="https://provider.test/v1",
        api_key="test-placeholder-key",
        timeout_seconds=5,
        client=client,
    )

    deltas = [
        delta
        async for delta in provider.stream(
            [ProviderMessage(role="user", content="سلام")],
            model="model",
            max_output_tokens=100,
            request_id="request",
        )
    ]

    assert "".join(delta.text for delta in deltas) == '{"answer":1}'
    assert deltas[-1].finish_reason == "stop"
    assert deltas[-1].usage is not None
    assert deltas[-1].usage.input_tokens == 5
    await client.aclose()


@pytest.mark.asyncio
async def test_provider_maps_rate_limit_without_leaking_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "private detail"}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleProvider(
        base_url="https://provider.test/v1",
        api_key="test-placeholder-key",
        timeout_seconds=5,
        max_retries=0,
        client=client,
    )

    with pytest.raises(ProviderFailure) as captured:
        await provider.complete(
            [ProviderMessage(role="user", content="سلام")],
            model="model",
            max_output_tokens=100,
            request_id="request",
        )

    assert captured.value.code == "provider_rate_limited"
    assert captured.value.retryable is True
    assert "private detail" not in str(captured.value)
    await client.aclose()


@pytest.mark.asyncio
async def test_provider_retries_transient_failure_then_succeeds() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}]},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleProvider(
        base_url="https://provider.test/v1",
        api_key="test-placeholder-key",
        timeout_seconds=5,
        max_retries=1,
        retry_base_seconds=0,
        client=client,
    )

    result = await provider.complete(
        [ProviderMessage(role="user", content="سلام")],
        model="model",
        max_output_tokens=100,
        request_id="request",
    )

    assert result.text == "{}"
    assert calls == 2
    await client.aclose()
