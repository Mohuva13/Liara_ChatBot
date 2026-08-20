import asyncio
import json
import random
from collections.abc import AsyncIterator, Sequence
from typing import Any

import httpx

from app.providers.base import (
    CompletionResult,
    ProviderFailure,
    ProviderMessage,
    ProviderUsage,
    StreamDelta,
)


class OpenAICompatibleProvider:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: float,
        max_retries: int = 2,
        retry_base_seconds: float = 0.2,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._owns_client = client is None
        self._max_retries = max_retries
        self._retry_base_seconds = retry_base_seconds
        transport = httpx.AsyncHTTPTransport(retries=0)
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_seconds),
            transport=transport,
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    def _headers(self, request_id: str) -> dict[str, str]:
        return {
            "authorization": f"Bearer {self._api_key}",
            "content-type": "application/json",
            "x-request-id": request_id,
        }

    @staticmethod
    def _messages(messages: Sequence[ProviderMessage]) -> list[dict[str, str]]:
        return [
            {"role": message.role, "content": message.content} for message in messages
        ]

    @staticmethod
    def _usage(payload: dict[str, Any] | None) -> ProviderUsage:
        payload = payload or {}
        prompt_details = payload.get("prompt_tokens_details") or {}
        return ProviderUsage(
            input_tokens=int(payload.get("prompt_tokens") or 0),
            output_tokens=int(payload.get("completion_tokens") or 0),
            cached_tokens=int(prompt_details.get("cached_tokens") or 0),
        )

    @staticmethod
    async def _raise_for_status(response: httpx.Response) -> None:
        if response.is_success:
            return
        status = response.status_code
        if status == 429:
            code = "provider_rate_limited"
        elif status == 402:
            code = "provider_quota_exhausted"
        elif status in {401, 403}:
            code = "provider_auth_failed"
        elif status in {408, 504}:
            code = "provider_timeout"
        elif status >= 500:
            code = "provider_unavailable"
        else:
            code = "provider_rejected_request"
        raise ProviderFailure(
            code,
            retryable=status in {401, 402, 403, 408, 429} or status >= 500,
            status_code=status,
        )

    async def _retry_delay(self, attempt: int, response: httpx.Response | None) -> None:
        retry_after = 0.0
        if response is not None:
            try:
                retry_after = max(0.0, float(response.headers.get("retry-after", "0")))
            except ValueError:
                retry_after = 0.0
        exponential = self._retry_base_seconds * (2**attempt)
        jitter = random.SystemRandom().uniform(0, exponential)
        await asyncio.sleep(min(10.0, retry_after) + jitter)

    async def _post(
        self,
        path: str,
        *,
        request_id: str,
        payload: dict[str, Any],
    ) -> httpx.Response:
        for attempt in range(self._max_retries + 1):
            response: httpx.Response | None = None
            try:
                response = await self._client.post(
                    f"{self._base_url}{path}",
                    headers=self._headers(request_id),
                    json=payload,
                )
                if response.is_success:
                    return response
                # Authentication/quota failures cannot recover by retrying the
                # same credential. Surface them immediately so the resilient
                # wrapper can switch to a separately configured backup key.
                retryable = (
                    response.status_code in {408, 429} or response.status_code >= 500
                )
                if not retryable or attempt >= self._max_retries:
                    await self._raise_for_status(response)
            except httpx.TimeoutException as error:
                if attempt >= self._max_retries:
                    raise ProviderFailure("provider_timeout", retryable=True) from error
            except httpx.HTTPError as error:
                if attempt >= self._max_retries:
                    raise ProviderFailure(
                        "provider_unavailable", retryable=True
                    ) from error
            await self._retry_delay(attempt, response)
        raise ProviderFailure("provider_unavailable", retryable=True)

    async def complete(
        self,
        messages: Sequence[ProviderMessage],
        *,
        model: str,
        max_output_tokens: int,
        request_id: str,
        json_mode: bool = False,
    ) -> CompletionResult:
        payload: dict[str, Any] = {
            "model": model,
            "messages": self._messages(messages),
            "max_tokens": max_output_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        response = await self._post(
            "/chat/completions", request_id=request_id, payload=payload
        )
        try:
            body = response.json()
            choice = body["choices"][0]
            text = choice["message"]["content"]
            if not isinstance(text, str):
                raise TypeError
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise ProviderFailure(
                "provider_invalid_response", retryable=False
            ) from error
        return CompletionResult(
            text=text,
            finish_reason=str(choice.get("finish_reason") or "unknown"),
            usage=self._usage(body.get("usage")),
            request_id=response.headers.get("x-request-id"),
        )

    async def stream(
        self,
        messages: Sequence[ProviderMessage],
        *,
        model: str,
        max_output_tokens: int,
        request_id: str,
    ) -> AsyncIterator[StreamDelta]:
        payload = {
            "model": model,
            "messages": self._messages(messages),
            "max_tokens": max_output_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
            "response_format": {"type": "json_object"},
        }
        try:
            async with self._client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                headers=self._headers(request_id),
                json=payload,
            ) as response:
                await self._raise_for_status(response)
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line.removeprefix("data:").strip()
                    if not data or data == "[DONE]":
                        continue
                    try:
                        event = json.loads(data)
                        choices = event.get("choices") or []
                        choice = choices[0] if choices else {}
                        delta = choice.get("delta") or {}
                        text = delta.get("content") or ""
                        usage = event.get("usage")
                    except (TypeError, ValueError) as error:
                        raise ProviderFailure(
                            "provider_invalid_stream", retryable=False
                        ) from error
                    yield StreamDelta(
                        text=text if isinstance(text, str) else "",
                        finish_reason=choice.get("finish_reason"),
                        usage=self._usage(usage) if usage else None,
                    )
        except httpx.TimeoutException as error:
            raise ProviderFailure("provider_timeout", retryable=True) from error
        except httpx.HTTPError as error:
            raise ProviderFailure("provider_unavailable", retryable=True) from error

    async def embed(
        self,
        inputs: Sequence[str],
        *,
        model: str,
        dimensions: int | None,
        request_id: str,
    ) -> list[list[float]]:
        payload: dict[str, Any] = {
            "model": model,
            "input": list(inputs),
            "encoding_format": "float",
        }
        if dimensions is not None:
            payload["dimensions"] = dimensions
        response = await self._post(
            "/embeddings", request_id=request_id, payload=payload
        )
        try:
            rows = sorted(response.json()["data"], key=lambda row: row["index"])
            embeddings = [row["embedding"] for row in rows]
            if len(embeddings) != len(inputs) or not all(
                isinstance(vector, list) for vector in embeddings
            ):
                raise TypeError
            return [[float(value) for value in vector] for vector in embeddings]
        except (KeyError, TypeError, ValueError) as error:
            raise ProviderFailure(
                "provider_invalid_response", retryable=False
            ) from error
