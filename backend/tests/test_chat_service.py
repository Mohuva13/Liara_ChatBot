import json
from collections.abc import AsyncIterator, Sequence

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.models.chat import ChatStreamRequest
from app.policies.rate_limit import RateLimitDecision
from app.providers.base import (
    CompletionResult,
    ProviderFailure,
    ProviderMessage,
    ProviderUsage,
    StreamDelta,
)
from app.retrieval.models import RetrievedChunk
from app.services.chat import (
    ChatOrchestrator,
    ChatPreparationError,
    build_chat_orchestrator,
)
from app.sessions.models import ReservationResult, SessionState, SessionTurn


class FakeStore:
    def __init__(self) -> None:
        self.state = SessionState()
        self.reservation = ReservationResult(acquired=True, status="in_progress")
        self.finished = False
        self.released = False

    async def load(self, session_id: str) -> SessionState | None:
        return self.state

    async def append_turns(
        self, session_id: str, turns: list[SessionTurn]
    ) -> SessionState:
        self.state.turns.extend(turns)
        return self.state

    async def reserve_message(
        self, session_id: str, message_id: str
    ) -> ReservationResult:
        return self.reservation

    async def finish_message(self, session_id: str, message_id: str) -> None:
        self.finished = True

    async def release_message(self, session_id: str, message_id: str) -> None:
        self.released = True

    async def record_issue_failure(
        self, session_id: str, issue_key: str
    ) -> SessionState:
        if self.state.issue.key == issue_key:
            self.state.issue.failure_count += 1
        else:
            self.state.issue.key = issue_key
            self.state.issue.failure_count = 1
        return self.state


class FakeCache:
    def __init__(self, value: str | None = None) -> None:
        self.value = value
        self.saved: str | None = None

    async def get(self, key: str) -> str | None:
        return self.value

    async def set(self, key: str, value: str, *, ttl_seconds: int) -> None:
        self.saved = value


class FakeRateLimiter:
    def __init__(self, allowed: bool = True) -> None:
        self.allowed = allowed

    async def check(self, identity: str) -> RateLimitDecision:
        return RateLimitDecision(
            allowed=self.allowed,
            retry_after_seconds=17 if not self.allowed else 0,
        )


class FakeRetriever:
    def __init__(self) -> None:
        self.last_embedding: Sequence[float] | None | object = "unset"
        self.last_query: str | None = None

    async def retrieve(
        self, query: str, embedding: Sequence[float] | None
    ) -> list[RetrievedChunk]:
        self.last_query = query
        self.last_embedding = embedding
        return [
            RetrievedChunk(
                chunk_id="source-1",
                document_id="doc-1",
                title="راه‌اندازی PostgreSQL",
                canonical_url=("https://docs.liara.ir/dbaas/postgresql/quick-setup/"),
                heading_path=("افزونه Pgvector",),
                content=(
                    "افزونه Pgvector لیارا از قابلیت HNSW indexing پشتیبانی نمی‌کند."
                ),
                token_count=30,
                source_commit="commit",
                corpus_version="version",
                fused_score=0.04,
                rerank_score=0.04,
            )
        ]


class EmptyRetriever:
    async def retrieve(
        self, query: str, embedding: Sequence[float] | None
    ) -> list[RetrievedChunk]:
        return []


class FakeProvider:
    def __init__(self) -> None:
        self.called = False
        self.stream_called = False
        self.embed_called = False

    async def complete(
        self,
        messages: Sequence[ProviderMessage],
        *,
        model: str,
        max_output_tokens: int,
        request_id: str,
        json_mode: bool = False,
    ) -> CompletionResult:
        return CompletionResult(
            text=self.answer(),
            finish_reason="stop",
            usage=ProviderUsage(input_tokens=10, output_tokens=5),
        )

    async def stream(
        self,
        messages: Sequence[ProviderMessage],
        *,
        model: str,
        max_output_tokens: int,
        request_id: str,
    ) -> AsyncIterator[StreamDelta]:
        self.called = True
        self.stream_called = True
        yield StreamDelta(text=self.answer())
        yield StreamDelta(
            finish_reason="stop",
            usage=ProviderUsage(input_tokens=20, output_tokens=8),
        )

    async def embed(
        self,
        inputs: Sequence[str],
        *,
        model: str,
        dimensions: int | None,
        request_id: str,
    ) -> list[list[float]]:
        self.called = True
        self.embed_called = True
        return [[0.1, 0.2] for _ in inputs]

    @staticmethod
    def answer() -> str:
        return json.dumps(
            {
                "answer_markdown": "خیر؛ HNSW در Pgvector لیارا پشتیبانی نمی‌شود.",
                "claims": [
                    {
                        "text": "HNSW پشتیبانی نمی‌شود.",
                        "source_ids": ["source-1"],
                    }
                ],
                "suggestions": ["جست‌وجوی exact چه زمانی مناسب است؟"],
                "outcome": "answered",
            }
        )


class FailingEmbeddingProvider(FakeProvider):
    async def embed(
        self,
        inputs: Sequence[str],
        *,
        model: str,
        dimensions: int | None,
        request_id: str,
    ) -> list[list[float]]:
        raise ProviderFailure("provider_unavailable", retryable=True)


class AbstainingProvider(FakeProvider):
    @staticmethod
    def answer() -> str:
        return json.dumps(
            {
                "answer_markdown": (
                    "در evidence ارائه‌شده شاهد کافی برای پاسخ وجود ندارد."
                ),
                "claims": [
                    {
                        "text": "شاهد کافی نیست.",
                        "source_ids": ["source-1"],
                    }
                ],
                "suggestions": [],
                "outcome": "answered",
            },
            ensure_ascii=False,
        )


def settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        llm_provider="openai-compatible",
        llm_base_url="https://provider.test/v1",
        llm_api_key="placeholder",
        llm_small_model="small",
        llm_large_model="large",
        embedding_provider="openai-compatible",
        embedding_base_url="https://provider.test/v1",
        embedding_api_key="placeholder",
        embedding_model="embedding",
        embedding_dimensions=2,
        evidence_min_score=0.025,
        evidence_min_query_coverage=0.2,
    )


def payload(text: str) -> ChatStreamRequest:
    return ChatStreamRequest(
        protocol_version="1",
        session_id="session-identifier-1234567890",
        message_id="message-12345678",
        text=text,
        surface="page",
        locale="fa-IR",
    )


@pytest.mark.asyncio
async def test_chat_reuses_provider_when_llm_and_embedding_credentials_match() -> None:
    configured = settings().model_copy(
        update={
            "database_url": SecretStr("postgresql://database/db"),
            "redis_url": SecretStr("redis://redis/0"),
        }
    )

    orchestrator = build_chat_orchestrator(configured)

    assert orchestrator is not None
    assert orchestrator.llm_provider is orchestrator.embedding_provider
    await orchestrator.aclose()


def parse_events(chunks: list[bytes]) -> list[dict[str, object]]:
    events = []
    for chunk in chunks:
        data_line = next(
            line for line in chunk.decode().splitlines() if line.startswith("data: ")
        )
        events.append(json.loads(data_line.removeprefix("data: ")))
    return events


@pytest.mark.asyncio
async def test_grounded_stream_emits_validated_sources_and_usage() -> None:
    store = FakeStore()
    provider = FakeProvider()
    orchestrator = ChatOrchestrator(
        settings=settings(),
        store=store,
        rate_limiter=FakeRateLimiter(),
        retriever=FakeRetriever(),
        llm_provider=provider,
        embedding_provider=provider,
    )
    prepared = await orchestrator.prepare(
        payload("آیا Pgvector لیارا از HNSW پشتیبانی می‌کند؟"),
        request_id="request",
    )

    events = parse_events([chunk async for chunk in orchestrator.stream(prepared)])

    assert events[0]["type"] == "message_start"
    source_event = next(event for event in events if event["type"] == "sources")
    sources = source_event["sources"]
    assert isinstance(sources, list)
    first_source = sources[0]
    assert isinstance(first_source, dict)
    assert str(first_source["url"]).startswith("https://docs.liara.ir/")
    assert events[-1]["outcome"] == "answered"
    assert store.finished is True
    assert store.state.turns[-1].source_ids == ["source-1"]


@pytest.mark.asyncio
async def test_query_embedding_failure_falls_back_to_lexical_retrieval() -> None:
    retriever = FakeRetriever()
    orchestrator = ChatOrchestrator(
        settings=settings(),
        store=FakeStore(),
        rate_limiter=FakeRateLimiter(),
        retriever=retriever,
        llm_provider=FakeProvider(),
        embedding_provider=FailingEmbeddingProvider(),
    )
    prepared = await orchestrator.prepare(
        payload("آیا Pgvector لیارا از HNSW پشتیبانی می‌کند؟"),
        request_id="request",
    )

    events = parse_events([chunk async for chunk in orchestrator.stream(prepared)])

    assert retriever.last_embedding is None
    assert events[-1]["outcome"] == "answered"


@pytest.mark.asyncio
async def test_follow_up_retrieval_uses_bounded_session_technology_context() -> None:
    store = FakeStore()
    store.state.turns = [
        SessionTurn(role="user", text="برنامه Node.js من به PostgreSQL لیارا وصل است"),
        SessionTurn(role="assistant", text="اتصال برقرار شد", outcome="answered"),
    ]
    retriever = FakeRetriever()
    orchestrator = ChatOrchestrator(
        settings=settings(),
        store=store,
        rate_limiter=FakeRateLimiter(),
        retriever=retriever,
        llm_provider=FakeProvider(),
        embedding_provider=FakeProvider(),
    )
    prepared = await orchestrator.prepare(
        payload("Connection pooling چطوریه؟"), request_id="request"
    )

    await orchestrator._retrieve(prepared)

    assert retriever.last_query is not None
    assert "nodejs" in retriever.last_query
    assert "postgresql" in retriever.last_query


@pytest.mark.asyncio
async def test_short_clarification_answer_keeps_original_topic_across_turns() -> None:
    store = FakeStore()
    store.state.turns = [
        SessionTurn(
            role="user",
            text="برای اتصال امن برنامه به Redis از کدام شبکه استفاده کنم؟",
        ),
        SessionTurn(
            role="assistant",
            text="پلتفرم برنامه را بگویید.",
            outcome="clarification:insufficient_query_coverage",
        ),
        SessionTurn(role="user", text="پس من چیکار کنم"),
        SessionTurn(
            role="assistant",
            text="نام پلتفرم را بگویید.",
            outcome="clarification:low_relevance",
        ),
    ]
    retriever = FakeRetriever()
    orchestrator = ChatOrchestrator(
        settings=settings(),
        store=store,
        rate_limiter=FakeRateLimiter(),
        retriever=retriever,
        llm_provider=FakeProvider(),
        embedding_provider=FakeProvider(),
    )
    prepared = await orchestrator.prepare(payload("پایتون"), request_id="request")

    await orchestrator._retrieve(prepared)

    assert retriever.last_query is not None
    assert "Redis" in retriever.last_query
    assert "پایتون" in retriever.last_query


@pytest.mark.asyncio
async def test_later_referential_follow_up_keeps_topic_and_platform() -> None:
    store = FakeStore()
    store.state.turns = [
        SessionTurn(
            role="user",
            text="برای اتصال امن برنامه به Redis از کدام شبکه استفاده کنم؟",
        ),
        SessionTurn(role="assistant", text="پلتفرم چیست؟", outcome="clarification:x"),
        SessionTurn(role="user", text="پایتون"),
        SessionTurn(role="assistant", text="پاسخ قبلی", outcome="answered"),
    ]
    retriever = FakeRetriever()
    orchestrator = ChatOrchestrator(
        settings=settings(),
        store=store,
        rate_limiter=FakeRateLimiter(),
        retriever=retriever,
        llm_provider=FakeProvider(),
        embedding_provider=FakeProvider(),
    )
    prepared = await orchestrator.prepare(
        payload("کجا باید وارد کنم"), request_id="request"
    )

    await orchestrator._retrieve(prepared)

    assert retriever.last_query is not None
    assert "Redis" in retriever.last_query
    assert "python" in retriever.last_query


@pytest.mark.asyncio
async def test_missing_evidence_clarifies_before_offering_support() -> None:
    store = FakeStore()
    orchestrator = ChatOrchestrator(
        settings=settings(),
        store=store,
        rate_limiter=FakeRateLimiter(),
        retriever=EmptyRetriever(),
        llm_provider=FakeProvider(),
        embedding_provider=FakeProvider(),
    )
    first = await orchestrator.prepare(
        payload("تنظیم ناشناخته دیتابیس لیارا چطور است؟"), request_id="request-1"
    )

    first_events = parse_events([chunk async for chunk in orchestrator.stream(first)])

    assert not any(event["type"] == "support" for event in first_events)
    assert first_events[-1]["outcome"] == "clarification"

    second = await orchestrator.prepare(
        payload("من از Node.js استفاده می‌کنم"), request_id="request-2"
    )
    second_events = parse_events([chunk async for chunk in orchestrator.stream(second)])

    assert any(event["type"] == "support" for event in second_events)
    assert second_events[-1]["outcome"] == "support"


@pytest.mark.asyncio
async def test_named_service_with_unrelated_evidence_goes_directly_to_support() -> None:
    provider = FakeProvider()
    orchestrator = ChatOrchestrator(
        settings=settings(),
        store=FakeStore(),
        rate_limiter=FakeRateLimiter(),
        retriever=FakeRetriever(),
        llm_provider=provider,
        embedding_provider=provider,
    )
    prepared = await orchestrator.prepare(
        payload("برای اتصال امن برنامه به Redis از کدام شبکه استفاده کنم؟"),
        request_id="request",
    )

    events = parse_events([chunk async for chunk in orchestrator.stream(prepared)])

    assert any(event["type"] == "support" for event in events)
    assert not any(event["type"] == "sources" for event in events)
    assert provider.stream_called is False
    assert events[-1]["outcome"] == "support"


@pytest.mark.asyncio
async def test_short_follow_up_after_support_stays_terminal_without_provider() -> None:
    store = FakeStore()
    store.state.turns = [
        SessionTurn(role="user", text="اتصال Redis به برنامه Python چطور است؟"),
        SessionTurn(role="assistant", text="خلاصه تیکت", outcome="support"),
    ]
    provider = FakeProvider()
    orchestrator = ChatOrchestrator(
        settings=settings(),
        store=store,
        rate_limiter=FakeRateLimiter(),
        retriever=FakeRetriever(),
        llm_provider=provider,
        embedding_provider=provider,
    )
    prepared = await orchestrator.prepare(
        payload("پس من چیکار کنم؟"), request_id="request"
    )

    events = parse_events([chunk async for chunk in orchestrator.stream(prepared)])

    assert events[-1]["outcome"] == "support"
    assert provider.called is False


@pytest.mark.asyncio
async def test_new_liara_topic_after_support_does_not_inherit_old_service() -> None:
    store = FakeStore()
    store.state.turns = [
        SessionTurn(role="user", text="اتصال Redis به برنامه چطور است؟"),
        SessionTurn(role="assistant", text="خلاصه تیکت", outcome="support"),
    ]
    orchestrator = ChatOrchestrator(
        settings=settings(),
        store=store,
        rate_limiter=FakeRateLimiter(),
        retriever=FakeRetriever(),
        llm_provider=FakeProvider(),
        embedding_provider=FakeProvider(),
    )
    prepared = await orchestrator.prepare(payload("دامنه چطور؟"), request_id="request")

    assert orchestrator._follows_terminal_support(prepared) is False
    assert orchestrator._retrieval_query(prepared) == "دامنه چطور؟"


@pytest.mark.asyncio
async def test_specific_entity_after_support_can_retry_retrieval() -> None:
    store = FakeStore()
    store.state.turns = [
        SessionTurn(role="user", text="محدودیت PostgreSQL چیست؟"),
        SessionTurn(role="assistant", text="خلاصه تیکت", outcome="support"),
    ]
    orchestrator = ChatOrchestrator(
        settings=settings(),
        store=store,
        rate_limiter=FakeRateLimiter(),
        retriever=FakeRetriever(),
        llm_provider=FakeProvider(),
        embedding_provider=FakeProvider(),
    )
    prepared = await orchestrator.prepare(
        payload("Pgvector چه محدودیتی دارد؟"), request_id="request"
    )

    assert orchestrator._follows_terminal_support(prepared) is False


@pytest.mark.asyncio
async def test_out_of_scope_is_deterministic_and_skips_provider() -> None:
    provider = FakeProvider()
    orchestrator = ChatOrchestrator(
        settings=settings(),
        store=FakeStore(),
        rate_limiter=FakeRateLimiter(),
        retriever=FakeRetriever(),
        llm_provider=provider,
        embedding_provider=provider,
    )
    prepared = await orchestrator.prepare(
        payload("برای شام چه غذای آشپزی پیشنهاد می‌کنی؟"), request_id="request"
    )

    events = parse_events([chunk async for chunk in orchestrator.stream(prepared)])

    assert events[-1]["outcome"] == "out_of_scope"
    assert provider.called is False


@pytest.mark.asyncio
async def test_unrecognized_out_of_scope_query_never_calls_answer_model() -> None:
    provider = FakeProvider()
    orchestrator = ChatOrchestrator(
        settings=settings(),
        store=FakeStore(),
        rate_limiter=FakeRateLimiter(),
        retriever=EmptyRetriever(),
        llm_provider=provider,
        embedding_provider=provider,
    )
    prepared = await orchestrator.prepare(
        payload("چطور گیتارم را کوک کنم؟"), request_id="request"
    )

    events = parse_events([chunk async for chunk in orchestrator.stream(prepared)])

    assert events[-1]["outcome"] == "out_of_scope"
    assert provider.stream_called is False


@pytest.mark.asyncio
async def test_model_abstention_is_not_shown_as_grounded_answer() -> None:
    store = FakeStore()
    provider = AbstainingProvider()
    orchestrator = ChatOrchestrator(
        settings=settings(),
        store=store,
        rate_limiter=FakeRateLimiter(),
        retriever=FakeRetriever(),
        llm_provider=provider,
        embedding_provider=provider,
    )
    prepared = await orchestrator.prepare(
        payload("آیا Pgvector لیارا از HNSW پشتیبانی می‌کند؟"),
        request_id="request",
    )

    events = parse_events([chunk async for chunk in orchestrator.stream(prepared)])

    assert not any(event["type"] == "sources" for event in events)
    assert events[-1]["outcome"] == "support"


@pytest.mark.asyncio
async def test_rate_limit_and_duplicate_fail_before_stream() -> None:
    store = FakeStore()
    orchestrator = ChatOrchestrator(
        settings=settings(),
        store=store,
        rate_limiter=FakeRateLimiter(allowed=False),
        retriever=FakeRetriever(),
        llm_provider=FakeProvider(),
        embedding_provider=FakeProvider(),
    )
    with pytest.raises(ChatPreparationError) as rate_error:
        await orchestrator.prepare(payload("سؤال درباره لیارا"), request_id="request")
    assert rate_error.value.status_code == 429
    assert rate_error.value.headers["Retry-After"] == "17"

    store.reservation = ReservationResult(acquired=False, status="in_progress")
    orchestrator.rate_limiter = FakeRateLimiter()
    with pytest.raises(ChatPreparationError) as duplicate_error:
        await orchestrator.prepare(payload("سؤال درباره لیارا"), request_id="request")
    assert duplicate_error.value.status_code == 409


@pytest.mark.asyncio
async def test_repeated_failure_stays_attached_to_original_issue() -> None:
    store = FakeStore()
    store.state.turns = [
        SessionTurn(role="user", text="اتصال Redis لیارا برقرار نمی‌شود"),
        SessionTurn(role="assistant", text="راه‌حل مستند", outcome="answered"),
    ]
    orchestrator = ChatOrchestrator(
        settings=settings(),
        store=store,
        rate_limiter=FakeRateLimiter(),
        retriever=FakeRetriever(),
        llm_provider=FakeProvider(),
        embedding_provider=FakeProvider(),
    )

    first = await orchestrator.prepare(
        payload("این راه‌حل کار نکرد"), request_id="request-1"
    )
    assert await orchestrator._failure_count(first) == 1
    store.state.turns.append(SessionTurn(role="user", text="این راه‌حل کار نکرد"))

    second = await orchestrator.prepare(
        payload("هنوز مشکل دارم و حل نشد"), request_id="request-2"
    )
    assert await orchestrator._failure_count(second) == 2


@pytest.mark.asyncio
async def test_valid_grounded_cache_hit_skips_generation() -> None:
    store = FakeStore()
    llm = FakeProvider()
    embedding = FakeProvider()
    cache = FakeCache(FakeProvider.answer())
    orchestrator = ChatOrchestrator(
        settings=settings(),
        store=store,
        rate_limiter=FakeRateLimiter(),
        retriever=FakeRetriever(),
        llm_provider=llm,
        embedding_provider=embedding,
        response_cache=cache,
    )
    prepared = await orchestrator.prepare(
        payload("آیا Pgvector لیارا از HNSW پشتیبانی می‌کند؟"),
        request_id="request",
    )

    events = parse_events([chunk async for chunk in orchestrator.stream(prepared)])

    usage = next(event["usage"] for event in events if event["type"] == "usage")
    assert isinstance(usage, dict)
    assert usage["cache_hit"] is True
    assert llm.called is False
    assert embedding.called is True
