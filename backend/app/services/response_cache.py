import hashlib
import json
from collections.abc import Sequence
from typing import Protocol

from redis.asyncio import Redis

from app.core.config import Settings
from app.core.logging import telemetry_event
from app.retrieval.normalizer import normalize_persian

POLICY_VERSION = "grounding-v1"


def response_cache_key(
    *,
    query: str,
    intent: str,
    corpus_versions: Sequence[str],
    locale: str,
    knowledge_level: str,
) -> str:
    payload = json.dumps(
        {
            "query": normalize_persian(query),
            "intent": intent,
            "corpus_versions": sorted(set(corpus_versions)),
            "locale": locale,
            "knowledge_level": knowledge_level,
            "policy": POLICY_VERSION,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(payload.encode()).hexdigest()
    return f"response-cache:{POLICY_VERSION}:{digest}"


class ResponseCache(Protocol):
    async def get(self, key: str) -> str | None: ...

    async def set(self, key: str, value: str, *, ttl_seconds: int) -> None: ...


class RedisResponseCache:
    """Fail-soft cache; grounding is revalidated after every cache read."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _client(self) -> Redis:
        assert self._settings.redis_url is not None
        return Redis.from_url(self._settings.redis_url.get_secret_value())

    async def get(self, key: str) -> str | None:
        client = self._client()
        try:
            raw = await client.get(key)
            return raw.decode() if isinstance(raw, bytes) else raw
        except Exception:
            telemetry_event("response_cache_unavailable", operation="get")
            return None
        finally:
            await client.aclose()

    async def set(self, key: str, value: str, *, ttl_seconds: int) -> None:
        client = self._client()
        try:
            await client.set(key, value, ex=ttl_seconds)
        except Exception:
            telemetry_event("response_cache_unavailable", operation="set")
        finally:
            await client.aclose()
