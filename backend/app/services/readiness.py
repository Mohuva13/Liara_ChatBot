import asyncio
from collections.abc import Awaitable
from typing import cast

import asyncpg
from redis.asyncio import Redis

from app.core.config import Settings
from app.models.health import ComponentStatus, ReadyResponse


class ReadinessProbe:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def check(self) -> ReadyResponse:
        database, corpus, redis, provider = await asyncio.gather(
            self._check_database(),
            self._check_corpus(),
            self._check_redis(),
            self._check_provider_configuration(),
        )
        components = {
            "postgres": database,
            "corpus": corpus,
            "redis": redis,
            "provider": provider,
        }
        return ReadyResponse(
            ready=all(component.ready for component in components.values()),
            components=components,
        )

    async def _connect_database(self) -> asyncpg.Connection:
        if self._settings.database_url is None:
            raise RuntimeError("database configuration missing")
        return await asyncpg.connect(
            dsn=self._settings.database_url.get_secret_value(),
            timeout=self._settings.readiness_timeout_seconds,
        )

    async def _check_database(self) -> ComponentStatus:
        if self._settings.database_url is None:
            return ComponentStatus(ready=False, code="configuration_missing")
        try:
            connection = await self._connect_database()
            try:
                await connection.fetchval("SELECT 1")
            finally:
                await connection.close()
        except Exception:
            return ComponentStatus(ready=False, code="unreachable")
        return ComponentStatus(ready=True, code="ok")

    async def _check_corpus(self) -> ComponentStatus:
        if self._settings.database_url is None:
            return ComponentStatus(ready=False, code="database_unavailable")
        try:
            connection = await self._connect_database()
            try:
                table_exists = await connection.fetchval(
                    "SELECT to_regclass('public.corpus_versions') IS NOT NULL"
                )
                if not table_exists:
                    return ComponentStatus(ready=False, code="schema_missing")
                active_exists = await connection.fetchval(
                    "SELECT EXISTS (SELECT 1 FROM corpus_versions "
                    "WHERE activated_at IS NOT NULL)"
                )
            finally:
                await connection.close()
        except Exception:
            return ComponentStatus(ready=False, code="check_failed")
        if not active_exists:
            return ComponentStatus(ready=False, code="active_version_missing")
        return ComponentStatus(ready=True, code="ok")

    async def _check_redis(self) -> ComponentStatus:
        if self._settings.redis_url is None:
            return ComponentStatus(ready=False, code="configuration_missing")
        client = Redis.from_url(
            self._settings.redis_url.get_secret_value(),
            socket_connect_timeout=self._settings.readiness_timeout_seconds,
            socket_timeout=self._settings.readiness_timeout_seconds,
        )
        try:
            await cast(Awaitable[bool], client.ping())
        except Exception:
            return ComponentStatus(ready=False, code="unreachable")
        finally:
            await client.aclose()
        return ComponentStatus(ready=True, code="ok")

    async def _check_provider_configuration(self) -> ComponentStatus:
        configured = all(
            (
                self._settings.llm_provider,
                self._settings.llm_base_url,
                self._settings.llm_api_key,
                self._settings.llm_small_model,
                self._settings.llm_large_model,
                self._settings.embedding_provider,
                self._settings.embedding_base_url,
                self._settings.embedding_api_key,
                self._settings.embedding_model,
                self._settings.embedding_dimensions,
            )
        )
        return ComponentStatus(
            ready=bool(configured),
            code="ok" if configured else "configuration_missing",
        )
