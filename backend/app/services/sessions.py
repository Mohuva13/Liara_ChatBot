import json
import secrets
from typing import Protocol

from redis.asyncio import Redis

from app.core.config import Settings


class SessionStore(Protocol):
    async def create(self) -> str: ...

    async def delete(self, session_id: str) -> bool: ...


class SessionStoreUnavailable(RuntimeError):
    pass


class RedisSessionStore:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _client(self) -> Redis:
        if self._settings.redis_url is None:
            raise SessionStoreUnavailable
        return Redis.from_url(self._settings.redis_url.get_secret_value())

    async def create(self) -> str:
        client = self._client()
        try:
            for _ in range(3):
                session_id = secrets.token_urlsafe(32)
                created = await client.set(
                    f"session:{session_id}:state",
                    json.dumps({"schema_version": 1}, separators=(",", ":")),
                    ex=self._settings.session_ttl_seconds,
                    nx=True,
                )
                if created:
                    return session_id
        except Exception as error:
            raise SessionStoreUnavailable from error
        finally:
            await client.aclose()
        raise SessionStoreUnavailable

    async def delete(self, session_id: str) -> bool:
        client = self._client()
        try:
            deleted = await client.delete(f"session:{session_id}:state")
        except Exception as error:
            raise SessionStoreUnavailable from error
        finally:
            await client.aclose()
        return bool(deleted)
