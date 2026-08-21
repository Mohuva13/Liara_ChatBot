import secrets
from collections.abc import Callable
from typing import Protocol

from redis.asyncio import Redis

from app.core.config import Settings
from app.sessions.models import IssueState, ReservationResult, SessionState, SessionTurn


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
                    SessionState().model_dump_json(),
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
            keys = [
                key
                async for key in client.scan_iter(
                    match=f"session:{session_id}:*", count=100
                )
            ]
            deleted = await client.unlink(*keys) if keys else 0
        except Exception as error:
            raise SessionStoreUnavailable from error
        finally:
            await client.aclose()
        return bool(deleted)

    async def load(self, session_id: str) -> SessionState | None:
        client = self._client()
        try:
            raw = await client.get(f"session:{session_id}:state")
            if raw is None:
                return None
            await client.expire(
                f"session:{session_id}:state", self._settings.session_ttl_seconds
            )
            return SessionState.model_validate_json(raw)
        except Exception as error:
            raise SessionStoreUnavailable from error
        finally:
            await client.aclose()

    async def append_turns(
        self, session_id: str, turns: list[SessionTurn]
    ) -> SessionState:
        return await self._update_state(
            session_id,
            lambda state: self._append_to_state(state, turns),
        )

    def _append_to_state(
        self, state: SessionState, turns: list[SessionTurn]
    ) -> SessionState:
        state.turns.extend(turns)
        if len(state.turns) > self._settings.session_summary_after_turns:
            keep = max(4, self._settings.session_summary_after_turns // 2)
            summarized = state.turns[:-keep]
            user_facts = [
                f"- {turn.text[:500]}" for turn in summarized if turn.role == "user"
            ]
            if user_facts:
                previous = state.summary.strip()
                additions = "درخواست‌های قبلی کاربر:\n" + "\n".join(user_facts)
                state.summary = "\n".join(
                    part for part in (previous, additions) if part
                )[-4000:]
            state.turns = state.turns[-keep:]
        state.turns = state.turns[-self._settings.session_max_turns :]
        return state

    async def _update_state(
        self,
        session_id: str,
        update: Callable[[SessionState], SessionState],
    ) -> SessionState:
        client = self._client()
        key = f"session:{session_id}:state"
        try:
            async with client.pipeline(transaction=True) as pipeline:
                while True:
                    try:
                        await pipeline.watch(key)
                        raw = await pipeline.get(key)
                        if raw is None:
                            raise SessionStoreUnavailable
                        state = SessionState.model_validate_json(raw)
                        state = update(state)
                        pipeline.multi()  # type: ignore[no-untyped-call]
                        pipeline.set(
                            key,
                            state.model_dump_json(),
                            ex=self._settings.session_ttl_seconds,
                        )
                        await pipeline.execute()
                        return state
                    except Exception as error:
                        if error.__class__.__name__ == "WatchError":
                            continue
                        raise
        except SessionStoreUnavailable:
            raise
        except Exception as error:
            raise SessionStoreUnavailable from error
        finally:
            await client.aclose()

    async def record_issue_failure(
        self, session_id: str, issue_key: str
    ) -> SessionState:
        def update(state: SessionState) -> SessionState:
            if state.issue.key == issue_key:
                state.issue.failure_count = min(20, state.issue.failure_count + 1)
            else:
                state.issue = IssueState(key=issue_key, failure_count=1)
            return state

        return await self._update_state(session_id, update)

    async def reserve_message(
        self, session_id: str, message_id: str
    ) -> ReservationResult:
        client = self._client()
        key = f"session:{session_id}:idempotency:{message_id}"
        try:
            acquired = await client.set(
                key,
                "in_progress",
                nx=True,
                ex=self._settings.session_ttl_seconds,
            )
            if acquired:
                return ReservationResult(acquired=True, status="in_progress")
            status = await client.get(key)
            return ReservationResult(
                acquired=False,
                status="complete" if status == b"complete" else "in_progress",
            )
        except Exception as error:
            raise SessionStoreUnavailable from error
        finally:
            await client.aclose()

    async def finish_message(self, session_id: str, message_id: str) -> None:
        client = self._client()
        try:
            await client.set(
                f"session:{session_id}:idempotency:{message_id}",
                "complete",
                xx=True,
                ex=self._settings.session_ttl_seconds,
            )
        except Exception as error:
            raise SessionStoreUnavailable from error
        finally:
            await client.aclose()

    async def release_message(self, session_id: str, message_id: str) -> None:
        client = self._client()
        try:
            await client.delete(f"session:{session_id}:idempotency:{message_id}")
        except Exception as error:
            raise SessionStoreUnavailable from error
        finally:
            await client.aclose()
