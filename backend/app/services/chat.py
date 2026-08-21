import asyncio
import hashlib
import secrets
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Protocol, cast
from urllib.parse import urlparse

from app.core.config import Settings
from app.core.logging import telemetry_event
from app.core.metrics import metrics
from app.generation.models import ValidatedAnswer
from app.generation.prompt import build_grounded_messages
from app.generation.router import select_model_route
from app.generation.validator import (
    GroundingValidationError,
    ModelAbstainedError,
    validate_grounded_answer,
)
from app.ingestion.redactor import redact_credentials
from app.models.chat import ChatStreamRequest
from app.models.events import ChatEvent, SourcePayload, UsagePayload
from app.policies.rate_limit import (
    RateLimitDecision,
    RateLimitUnavailable,
    RedisRateLimiter,
)
from app.policies.scope import ScopeDecision, classify_scope
from app.providers.base import (
    AIProvider,
    CompletionResult,
    ProviderFailure,
    ProviderMessage,
    ProviderUsage,
)
from app.retrieval.evidence import assess_evidence
from app.retrieval.models import EvidenceDecision, RetrievedChunk
from app.retrieval.normalizer import retrieval_terms
from app.services.response_cache import ResponseCache, response_cache_key
from app.sessions.models import ReservationResult, SessionState, SessionTurn


class Retriever(Protocol):
    async def retrieve(
        self, query: str, embedding: Sequence[float] | None
    ) -> list[RetrievedChunk]: ...


class ConversationStore(Protocol):
    async def load(self, session_id: str) -> SessionState | None: ...

    async def append_turns(
        self, session_id: str, turns: list[SessionTurn]
    ) -> SessionState: ...

    async def reserve_message(
        self, session_id: str, message_id: str
    ) -> ReservationResult: ...

    async def finish_message(self, session_id: str, message_id: str) -> None: ...

    async def release_message(self, session_id: str, message_id: str) -> None: ...

    async def record_issue_failure(
        self, session_id: str, issue_key: str
    ) -> SessionState: ...


class RateLimiter(Protocol):
    async def check(self, identity: str) -> RateLimitDecision: ...


class ChatPreparationError(RuntimeError):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.headers = headers or {}


@dataclass(frozen=True, slots=True)
class PreparedChat:
    payload: ChatStreamRequest
    state: SessionState
    scope: ScopeDecision
    response_id: str
    request_id: str


FAILURE_MARKERS = (
    "جواب نداد",
    "کار نکرد",
    "حل نشد",
    "نتیجه نداد",
    "هنوز مشکل دارم",
)
RETRIEVAL_CONTEXT_ANCHORS = {
    "django",
    "docker",
    "laravel",
    "mongodb",
    "mssql",
    "mysql",
    "nextjs",
    "nodejs",
    "php",
    "postgresql",
    "python",
    "redis",
}
RETRIEVAL_TOPIC_ANCHORS = RETRIEVAL_CONTEXT_ANCHORS | {
    "دامنه",
    "dns",
    "شبکه",
    "object",
    "storage",
    "کوبرنتیز",
}
FOLLOW_UP_PREFIXES = (
    "پس ",
    "حالا ",
    "بعد ",
    "کجا ",
    "چطور ",
    "چجوری ",
    "این ",
    "اون ",
    "آن ",
)


class ChatOrchestrator:
    def __init__(
        self,
        *,
        settings: Settings,
        store: ConversationStore,
        rate_limiter: RateLimiter,
        retriever: Retriever,
        llm_provider: AIProvider,
        embedding_provider: AIProvider,
        response_cache: ResponseCache | None = None,
    ) -> None:
        self.settings = settings
        self.store = store
        self.rate_limiter = rate_limiter
        self.retriever = retriever
        self.llm_provider = llm_provider
        self.embedding_provider = embedding_provider
        self.response_cache = response_cache

    async def aclose(self) -> None:
        closed: set[int] = set()
        for provider in (self.llm_provider, self.embedding_provider):
            if id(provider) in closed:
                continue
            closed.add(id(provider))
            close = getattr(provider, "aclose", None)
            if close is not None:
                await cast(Callable[[], Awaitable[None]], close)()

    async def prepare(
        self,
        payload: ChatStreamRequest,
        *,
        request_id: str,
        rate_identity: str | None = None,
    ) -> PreparedChat:
        state = await self.store.load(payload.session_id)
        if state is None:
            raise ChatPreparationError(
                status_code=404,
                code="session_not_found",
                message="نشست گفتگو پیدا نشد یا منقضی شده است.",
            )
        try:
            rate = await self.rate_limiter.check(
                rate_identity or f"{payload.session_id}:chat"
            )
        except RateLimitUnavailable as error:
            raise ChatPreparationError(
                status_code=503,
                code="rate_limit_unavailable",
                message="کنترل ظرفیت سرویس موقتاً در دسترس نیست.",
            ) from error
        if not rate.allowed:
            metrics.increment("liara_rate_limits_total", route="chat")
            raise ChatPreparationError(
                status_code=429,
                code="rate_limited",
                message="تعداد درخواست‌ها بیش از حد مجاز است.",
                headers={"Retry-After": str(rate.retry_after_seconds)},
            )
        reservation = await self.store.reserve_message(
            payload.session_id, payload.message_id
        )
        if not reservation.acquired:
            raise ChatPreparationError(
                status_code=409,
                code=(
                    "duplicate_completed"
                    if reservation.status == "complete"
                    else "duplicate_in_progress"
                ),
                message="این پیام قبلاً دریافت شده است.",
            )
        return PreparedChat(
            payload=payload,
            state=state,
            scope=classify_scope(payload.text),
            response_id=uuid.uuid4().hex,
            request_id=request_id,
        )

    async def stream(self, prepared: PreparedChat) -> AsyncIterator[bytes]:
        payload = prepared.payload
        completed = False
        stream_started = time.perf_counter()
        try:
            yield ChatEvent(
                type="message_start",
                response_id=prepared.response_id,
                session_id=payload.session_id,
            ).to_sse()
            if not prepared.scope.in_scope:
                async for event in self._out_of_scope(prepared):
                    yield event
                completed = True
                return

            repeated_failure = await self._failure_count(prepared)
            if repeated_failure >= 2:
                async for event in self._support(
                    prepared, reason="repeated_failure", evidence=()
                ):
                    yield event
                completed = True
                return
            if self._follows_terminal_support(prepared):
                async for event in self._support(
                    prepared, reason="support_continuation", evidence=()
                ):
                    yield event
                completed = True
                return

            yield ChatEvent(type="status", text="در حال جست‌وجوی مستندات…").to_sse()
            retrieval_started = time.perf_counter()
            evidence, decision = await self._retrieve(prepared)
            metrics.increment(
                "liara_retrieval_latency_milliseconds_total",
                (time.perf_counter() - retrieval_started) * 1000,
                outcome="sufficient" if decision.sufficient else decision.reason,
            )
            metrics.increment(
                "liara_retrieval_requests_total",
                outcome="sufficient" if decision.sufficient else decision.reason,
            )
            if not decision.sufficient:
                if self._follows_retrieval_clarification(prepared):
                    async for event in self._support(
                        prepared, reason=decision.reason, evidence=evidence
                    ):
                        yield event
                elif (
                    prepared.scope.reason == "domain_unverified"
                    and not self._is_contextual_follow_up(prepared)
                ):
                    async for event in self._out_of_scope(prepared):
                        yield event
                elif self._clarification_can_help(prepared):
                    async for event in self._clarification(prepared, decision.reason):
                        yield event
                else:
                    async for event in self._support(
                        prepared, reason=decision.reason, evidence=evidence
                    ):
                        yield event
                completed = True
                return

            yield ChatEvent(type="status", text="در حال آماده‌سازی پاسخ مستند…").to_sse()
            route = select_model_route(
                payload.text,
                prepared.scope.intent,
                decision,
                small_model=self._required(self.settings.llm_small_model),
                large_model=self._required(self.settings.llm_large_model),
                small_max_tokens=self.settings.max_output_tokens_small,
                large_max_tokens=self.settings.max_output_tokens_large,
            )
            messages = build_grounded_messages(
                payload.text,
                decision.chunks,
                intent=prepared.scope.intent,
                summary=prepared.state.summary,
                recent_turns=prepared.state.turns,
                max_context_tokens=self.settings.max_context_tokens,
            )
            cache_key: str | None = None
            cache_status = "bypass"
            answer: ValidatedAnswer | None = None
            usage = ProviderUsage()
            finish_reason = "cache"
            raw = ""
            cache_eligible = (
                self.response_cache is not None
                and self.settings.response_cache_ttl_seconds > 0
                and not prepared.state.turns
                and not any(
                    marker in payload.text.casefold() for marker in FAILURE_MARKERS
                )
            )
            if cache_eligible:
                cache_key = response_cache_key(
                    query=payload.text,
                    intent=prepared.scope.intent.value,
                    corpus_versions=[chunk.corpus_version for chunk in decision.chunks],
                    locale=payload.locale,
                )
                assert self.response_cache is not None
                cached = await self.response_cache.get(cache_key)
                if cached is not None:
                    try:
                        answer = validate_grounded_answer(cached, decision.chunks)
                        cache_status = "hit"
                    except GroundingValidationError:
                        cache_status = "invalid"
                else:
                    cache_status = "miss"

            if answer is None:
                if (
                    self._message_tokens(messages)
                    > self.settings.max_provider_input_tokens
                ):
                    async for event in self._support(
                        prepared,
                        reason="token_budget_exceeded",
                        evidence=evidence,
                    ):
                        yield event
                    completed = True
                    return
                raw, usage, finish_reason = await self._generate_validated_raw(
                    messages,
                    model=route.model,
                    max_tokens=route.max_output_tokens,
                    request_id=prepared.request_id,
                )
                try:
                    answer = validate_grounded_answer(raw, decision.chunks)
                except ModelAbstainedError:
                    async for event in self._grounding_fallback(
                        prepared, evidence=evidence
                    ):
                        yield event
                    completed = True
                    return
                except GroundingValidationError:
                    repair = await self._repair(
                        messages,
                        model=route.model,
                        max_tokens=route.max_output_tokens,
                        request_id=prepared.request_id,
                    )
                    raw = repair.text
                    try:
                        answer = validate_grounded_answer(raw, decision.chunks)
                    except ModelAbstainedError:
                        async for event in self._grounding_fallback(
                            prepared, evidence=evidence
                        ):
                            yield event
                        completed = True
                        return
                    usage = ProviderUsage(
                        input_tokens=usage.input_tokens + repair.usage.input_tokens,
                        output_tokens=usage.output_tokens + repair.usage.output_tokens,
                        cached_tokens=usage.cached_tokens + repair.usage.cached_tokens,
                        provider_name=repair.usage.provider_name or usage.provider_name,
                    )
                    finish_reason = repair.finish_reason
                if cache_key is not None and self.response_cache is not None:
                    await self.response_cache.set(
                        cache_key,
                        raw,
                        ttl_seconds=self.settings.response_cache_ttl_seconds,
                    )

            cited = {
                chunk.chunk_id: chunk
                for chunk in decision.chunks
                if chunk.chunk_id in answer.source_ids
            }
            for index, text in enumerate(self._text_chunks(answer.answer_markdown)):
                if index == 0:
                    metrics.increment(
                        "liara_chat_ttft_milliseconds_total",
                        (time.perf_counter() - stream_started) * 1000,
                        model_tier=route.tier,
                    )
                yield ChatEvent(type="text_delta", text=text).to_sse()
                await asyncio.sleep(0)
            sources = [
                self._source(cited[source_id]) for source_id in answer.source_ids
            ]
            yield ChatEvent(type="sources", sources=sources).to_sse()
            if answer.suggestions:
                yield ChatEvent(
                    type="suggestions", suggestions=answer.suggestions
                ).to_sse()
            yield ChatEvent(
                type="usage",
                usage=UsagePayload(
                    model_tier=route.tier,
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    cached_tokens=usage.cached_tokens,
                    cache_hit=cache_status == "hit",
                    provider_name=usage.provider_name,
                    estimated_cost_usd=self._estimated_cost(
                        route.tier, usage.input_tokens, usage.output_tokens
                    ),
                ),
            ).to_sse()
            yield ChatEvent(
                type="message_end",
                finish_reason=finish_reason,
                outcome="answered",
            ).to_sse()
            telemetry_event(
                "chat_outcome",
                request_id=prepared.request_id,
                response_id=prepared.response_id,
                outcome="answered",
                model_tier=route.tier,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cached_tokens=usage.cached_tokens,
                provider_name=usage.provider_name,
                estimated_cost_usd=self._estimated_cost(
                    route.tier, usage.input_tokens, usage.output_tokens
                ),
                corpus_versions=sorted(
                    {chunk.corpus_version for chunk in cited.values()}
                ),
                cache_status=cache_status,
            )
            metrics.increment(
                "liara_chat_outcomes_total",
                outcome="answered",
                model_tier=route.tier,
                cache_status=cache_status,
                provider=usage.provider_name or "cache",
            )
            metrics.increment(
                "liara_provider_tokens_total",
                usage.input_tokens,
                direction="input",
                model_tier=route.tier,
            )
            metrics.increment(
                "liara_provider_tokens_total",
                usage.output_tokens,
                direction="output",
                model_tier=route.tier,
            )
            await self.store.append_turns(
                payload.session_id,
                [
                    SessionTurn(role="user", text=self._safe_user_text(payload.text)),
                    SessionTurn(
                        role="assistant",
                        text=answer.answer_markdown,
                        outcome="answered",
                        source_ids=answer.source_ids,
                    ),
                ],
            )
            completed = True
        except GroundingValidationError:
            yield ChatEvent(
                type="error",
                code="grounding_failed",
                message="پاسخ قابل استناد تولید نشد.",
                retryable=False,
            ).to_sse()
        except ProviderFailure as error:
            metrics.increment(
                "liara_chat_outcomes_total",
                outcome=error.code,
                model_tier="unknown",
                cache_status="error",
                provider="unknown",
            )
            yield ChatEvent(
                type="error",
                code=error.code,
                message="سرویس تولید پاسخ موقتاً در دسترس نیست.",
                retryable=error.retryable,
            ).to_sse()
        except asyncio.CancelledError:
            raise
        except Exception:
            yield ChatEvent(
                type="error",
                code="generation_failed",
                message="پاسخ مستند تکمیل نشد.",
                retryable=True,
            ).to_sse()
        finally:
            try:
                if completed:
                    await self.store.finish_message(
                        payload.session_id, payload.message_id
                    )
                else:
                    await self.store.release_message(
                        payload.session_id, payload.message_id
                    )
            except Exception:
                telemetry_event(
                    "session_finalize_failed",
                    request_id=prepared.request_id,
                    response_id=prepared.response_id,
                    outcome="error",
                )

    async def _retrieve(
        self, prepared: PreparedChat
    ) -> tuple[list[RetrievedChunk], EvidenceDecision]:
        settings = self.settings
        retrieval_query = self._retrieval_query(prepared)
        embedding: Sequence[float] | None = None
        fallback_reason: str | None = None
        try:
            async with asyncio.timeout(settings.query_embedding_timeout_seconds):
                vectors = await self.embedding_provider.embed(
                    [retrieval_query],
                    model=self._required(settings.embedding_model),
                    dimensions=settings.embedding_dimensions,
                    request_id=prepared.request_id,
                )
                embedding = vectors[0]
        except TimeoutError:
            fallback_reason = "timeout"
        except ProviderFailure as error:
            fallback_reason = error.code
        if fallback_reason is not None:
            telemetry_event(
                "query_embedding_fallback",
                request_id=prepared.request_id,
                reason=fallback_reason,
            )
            metrics.increment(
                "liara_query_embedding_fallback_total", reason=fallback_reason
            )
        evidence = await self.retriever.retrieve(retrieval_query, embedding)
        decision = assess_evidence(
            retrieval_query,
            evidence,
            min_score=settings.evidence_min_score,
            min_query_coverage=settings.evidence_min_query_coverage,
            limit=settings.evidence_limit,
            max_tokens=settings.max_evidence_tokens,
        )
        return evidence, decision

    @staticmethod
    def _retrieval_query(prepared: PreparedChat) -> str:
        if not ChatOrchestrator._is_contextual_follow_up(prepared):
            return prepared.payload.text
        recent_user_turns = [
            turn.text
            for turn in reversed(prepared.state.turns[-12:])
            if turn.role == "user"
        ]
        if not recent_user_turns:
            return prepared.payload.text
        current_terms = set(retrieval_terms(prepared.payload.text))
        anchors: list[str] = []
        substantive: str | None = None
        for text in recent_user_turns:
            terms = retrieval_terms(text)
            for term in terms:
                if (
                    term in RETRIEVAL_CONTEXT_ANCHORS
                    and term not in current_terms
                    and term not in anchors
                    and len(anchors) < 4
                ):
                    anchors.append(term)
            if substantive is None and len(terms) >= 5:
                substantive = text
        parts = [prepared.payload.text]
        if substantive is not None:
            parts.append(substantive[:500])
        if anchors:
            parts.append(" ".join(anchors))
        return " ".join(parts)[:800]

    @staticmethod
    def _is_contextual_follow_up(prepared: PreparedChat) -> bool:
        if not prepared.state.turns:
            return False
        previous_assistant = next(
            (
                turn
                for turn in reversed(prepared.state.turns)
                if turn.role == "assistant"
            ),
            None,
        )
        if (
            previous_assistant is not None
            and previous_assistant.outcome is not None
            and previous_assistant.outcome.startswith("clarification:")
        ):
            return True
        normalized = " ".join(prepared.payload.text.casefold().split())
        terms = retrieval_terms(normalized)
        current_topics = set(terms) & RETRIEVAL_TOPIC_ANCHORS
        recent_topics = {
            term
            for turn in prepared.state.turns[-12:]
            if turn.role == "user"
            for term in retrieval_terms(turn.text)
            if term in RETRIEVAL_TOPIC_ANCHORS
        }
        if (
            current_topics
            and recent_topics
            and current_topics.isdisjoint(recent_topics)
        ):
            return False
        return len(terms) <= 4 or any(
            normalized.startswith(prefix) for prefix in FOLLOW_UP_PREFIXES
        )

    @staticmethod
    def _clarification_can_help(prepared: PreparedChat) -> bool:
        terms = set(retrieval_terms(prepared.payload.text))
        if prepared.scope.intent.value == "troubleshoot":
            return True
        return not bool(terms & RETRIEVAL_CONTEXT_ANCHORS)

    async def _grounding_fallback(
        self,
        prepared: PreparedChat,
        *,
        evidence: Sequence[RetrievedChunk],
    ) -> AsyncIterator[bytes]:
        if self._follows_retrieval_clarification(prepared):
            async for event in self._support(
                prepared, reason="model_abstained", evidence=evidence
            ):
                yield event
        elif self._clarification_can_help(prepared):
            async for event in self._clarification(prepared, "model_abstained"):
                yield event
        else:
            async for event in self._support(
                prepared, reason="model_abstained", evidence=evidence
            ):
                yield event

    async def _generate_validated_raw(
        self,
        messages: Sequence[ProviderMessage],
        *,
        model: str,
        max_tokens: int,
        request_id: str,
    ) -> tuple[str, ProviderUsage, str]:
        parts: list[str] = []
        usage = ProviderUsage()
        finish_reason = "unknown"
        async for delta in self.llm_provider.stream(
            messages,
            model=model,
            max_output_tokens=max_tokens,
            request_id=request_id,
        ):
            parts.append(delta.text)
            if delta.usage is not None:
                usage = delta.usage
            if delta.finish_reason is not None:
                finish_reason = delta.finish_reason
        return "".join(parts), usage, finish_reason

    async def _repair(
        self,
        messages: Sequence[ProviderMessage],
        *,
        model: str,
        max_tokens: int,
        request_id: str,
    ) -> CompletionResult:
        repair_messages = [
            *messages,
            ProviderMessage(
                role="user",
                content=(
                    "خروجی قبلی قرارداد JSON یا citation معتبر را رعایت نکرد. "
                    "فقط JSON معتبر مطابق schema و فقط با source_idهای EVIDENCE "
                    "برگردان."
                ),
            ),
        ]
        return await self.llm_provider.complete(
            repair_messages,
            model=model,
            max_output_tokens=max_tokens,
            request_id=request_id,
            json_mode=True,
        )

    async def _failure_count(self, prepared: PreparedChat) -> int:
        normalized = prepared.payload.text.casefold()
        if not any(marker in normalized for marker in FAILURE_MARKERS):
            return 0
        previous_user = next(
            (
                turn.text
                for turn in reversed(prepared.state.turns)
                if turn.role == "user"
                and not any(
                    marker in turn.text.casefold() for marker in FAILURE_MARKERS
                )
            ),
            prepared.payload.text,
        )
        issue_key = hashlib.sha256(previous_user.encode()).hexdigest()[:20]
        state = await self.store.record_issue_failure(
            prepared.payload.session_id, issue_key
        )
        return state.issue.failure_count

    async def _out_of_scope(self, prepared: PreparedChat) -> AsyncIterator[bytes]:
        text = (
            "این دستیار فقط درباره خدمات و مستندات رسمی لیارا پاسخ می‌دهد. "
            "می‌توانید درباره استقرار برنامه، دیتابیس، دامنه یا شبکه خصوصی بپرسید."
        )
        yield ChatEvent(type="text_delta", text=text).to_sse()
        yield ChatEvent(
            type="suggestions",
            suggestions=[
                "چطور یک برنامه را روی لیارا مستقر کنم؟",
                "چطور به دیتابیس لیارا متصل شوم؟",
            ],
        ).to_sse()
        yield ChatEvent(type="usage", usage=UsagePayload(model_tier="none")).to_sse()
        yield ChatEvent(
            type="message_end", finish_reason="policy", outcome="out_of_scope"
        ).to_sse()
        await self.store.append_turns(
            prepared.payload.session_id,
            [
                SessionTurn(
                    role="user", text=self._safe_user_text(prepared.payload.text)
                ),
                SessionTurn(role="assistant", text=text, outcome="out_of_scope"),
            ],
        )

    async def _clarification(
        self, prepared: PreparedChat, reason: str
    ) -> AsyncIterator[bytes]:
        if reason in {"low_relevance", "insufficient_query_coverage"}:
            text = (
                "چند سند نزدیک پیدا کردم، اما برای پاسخ دقیق‌تر لطفاً نام پلتفرم "
                "یا فریم‌ورک برنامه (مثلاً Node.js، Python یا Laravel) و کاری که "
                "می‌خواهید انجام دهید را بگویید."
            )
        else:
            text = (
                "برای پیدا کردن سند درست، لطفاً نام سرویس یا پلتفرم لیارا و هدف یا "
                "خطایی که می‌بینید را مشخص کنید."
            )
        yield ChatEvent(type="text_delta", text=text).to_sse()
        yield ChatEvent(
            type="message_end", finish_reason="policy", outcome="clarification"
        ).to_sse()
        await self.store.append_turns(
            prepared.payload.session_id,
            [
                SessionTurn(
                    role="user", text=self._safe_user_text(prepared.payload.text)
                ),
                SessionTurn(
                    role="assistant", text=text, outcome=f"clarification:{reason}"
                ),
            ],
        )

    @staticmethod
    def _follows_retrieval_clarification(prepared: PreparedChat) -> bool:
        previous_assistant = next(
            (
                turn
                for turn in reversed(prepared.state.turns)
                if turn.role == "assistant"
            ),
            None,
        )
        return bool(
            previous_assistant is not None
            and previous_assistant.outcome is not None
            and previous_assistant.outcome.startswith("clarification:")
        )

    @staticmethod
    def _follows_terminal_support(prepared: PreparedChat) -> bool:
        if not ChatOrchestrator._is_contextual_follow_up(prepared):
            return False
        previous_assistant = next(
            (
                turn
                for turn in reversed(prepared.state.turns)
                if turn.role == "assistant"
            ),
            None,
        )
        return bool(
            previous_assistant is not None and previous_assistant.outcome == "support"
        )

    async def _support(
        self,
        prepared: PreparedChat,
        *,
        reason: str,
        evidence: Sequence[RetrievedChunk],
    ) -> AsyncIterator[bytes]:
        support_query = self._retrieval_query(prepared)
        safe_query, _ = redact_credentials(support_query)
        titles = "، ".join(dict.fromkeys(chunk.title for chunk in evidence[:3]))
        summary = f"هدف/سؤال: {safe_query[:500]}"
        if titles:
            summary += f"\nمستندات بررسی‌شده: {titles}"
        yield ChatEvent(
            type="support",
            reason_code=reason,
            ticket_url=str(self.settings.support_ticket_url),
            summary=summary,
            text="برای این مورد پاسخ قابل‌اعتماد کافی پیدا نشد.",
        ).to_sse()
        yield ChatEvent(
            type="message_end", finish_reason="policy", outcome="support"
        ).to_sse()
        await self.store.append_turns(
            prepared.payload.session_id,
            [
                SessionTurn(
                    role="user", text=self._safe_user_text(prepared.payload.text)
                ),
                SessionTurn(role="assistant", text=summary, outcome="support"),
            ],
        )

    @staticmethod
    def _source(chunk: RetrievedChunk) -> SourcePayload:
        parsed = urlparse(chunk.canonical_url)
        if parsed.scheme != "https" or parsed.hostname != "docs.liara.ir":
            raise GroundingValidationError("source URL is outside allowlist")
        snippet = " ".join(chunk.content.split())[:280]
        return SourcePayload(
            id=chunk.chunk_id,
            title=chunk.title,
            url=chunk.canonical_url,
            section=" > ".join(chunk.heading_path),
            snippet=snippet,
            source_commit=chunk.source_commit,
        )

    @staticmethod
    def _text_chunks(text: str, size: int = 120) -> list[str]:
        return [text[index : index + size] for index in range(0, len(text), size)]

    @staticmethod
    def _message_tokens(messages: Sequence[ProviderMessage]) -> int:
        return sum(max(1, len(message.content) // 4) for message in messages)

    def _estimated_cost(
        self, tier: str, input_tokens: int, output_tokens: int
    ) -> float:
        if tier == "small":
            input_rate = self.settings.llm_small_input_usd_per_million
            output_rate = self.settings.llm_small_output_usd_per_million
        else:
            input_rate = self.settings.llm_large_input_usd_per_million
            output_rate = self.settings.llm_large_output_usd_per_million
        return round(
            (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000,
            8,
        )

    @staticmethod
    def _safe_user_text(text: str) -> str:
        safe, _ = redact_credentials(text)
        return safe[:20000]

    @staticmethod
    def _required(value: str | None) -> str:
        if not value:
            raise ProviderFailure("provider_configuration_missing", retryable=False)
        return value


def build_chat_orchestrator(settings: Settings) -> ChatOrchestrator | None:
    required = (
        settings.database_url,
        settings.redis_url,
        settings.llm_base_url,
        settings.llm_api_key,
        settings.llm_small_model,
        settings.llm_large_model,
        settings.embedding_base_url,
        settings.embedding_api_key,
        settings.embedding_model,
        settings.embedding_dimensions,
    )
    if not all(required):
        return None
    assert settings.database_url is not None
    assert settings.llm_base_url is not None
    assert settings.llm_api_key is not None
    assert settings.embedding_base_url is not None
    assert settings.embedding_api_key is not None
    from app.providers.openai_compat import OpenAICompatibleProvider
    from app.providers.resilient import ProviderTarget, ResilientProvider
    from app.retrieval.postgres import PostgresHybridRetriever
    from app.services.response_cache import RedisResponseCache
    from app.services.sessions import RedisSessionStore

    store = RedisSessionStore(settings)
    primary_credentials_shared = str(settings.llm_base_url).rstrip("/") == str(
        settings.embedding_base_url
    ).rstrip("/") and secrets.compare_digest(
        settings.llm_api_key.get_secret_value(),
        settings.embedding_api_key.get_secret_value(),
    )
    llm_backup_key = (
        settings.llm_backup_api_key.get_secret_value()
        if settings.llm_backup_api_key is not None
        else None
    )
    embedding_backup_key = (
        settings.embedding_backup_api_key.get_secret_value()
        if settings.embedding_backup_api_key is not None
        else None
    )
    backup_credentials_shared = (
        llm_backup_key is None and embedding_backup_key is None
    ) or (
        llm_backup_key is not None
        and embedding_backup_key is not None
        and secrets.compare_digest(llm_backup_key, embedding_backup_key)
        and str(settings.llm_backup_base_url or settings.llm_base_url).rstrip("/")
        == str(
            settings.embedding_backup_base_url or settings.embedding_base_url
        ).rstrip("/")
    )
    share_provider = primary_credentials_shared and backup_credentials_shared
    llm_targets = [
        ProviderTarget(
            "primary",
            OpenAICompatibleProvider(
                base_url=str(settings.llm_base_url),
                api_key=settings.llm_api_key.get_secret_value(),
                timeout_seconds=settings.llm_request_timeout_seconds,
                connect_timeout_seconds=settings.provider_connect_timeout_seconds,
                max_retries=settings.llm_max_retries,
            ),
        )
    ]
    if settings.llm_backup_api_key is not None:
        llm_targets.append(
            ProviderTarget(
                "backup",
                OpenAICompatibleProvider(
                    base_url=str(settings.llm_backup_base_url or settings.llm_base_url),
                    api_key=settings.llm_backup_api_key.get_secret_value(),
                    timeout_seconds=settings.llm_request_timeout_seconds,
                    connect_timeout_seconds=settings.provider_connect_timeout_seconds,
                    max_retries=settings.llm_max_retries,
                ),
            )
        )
    llm = ResilientProvider(
        llm_targets,
        failure_threshold=settings.provider_circuit_failure_threshold,
        reset_seconds=settings.provider_circuit_reset_seconds,
        concurrency_limit=settings.provider_concurrency_limit,
        queue_timeout_seconds=settings.provider_queue_timeout_seconds,
    )
    if share_provider:
        embedding = llm
    else:
        embedding_targets = [
            ProviderTarget(
                "primary",
                OpenAICompatibleProvider(
                    base_url=str(settings.embedding_base_url),
                    api_key=settings.embedding_api_key.get_secret_value(),
                    timeout_seconds=settings.embedding_request_timeout_seconds,
                    connect_timeout_seconds=settings.provider_connect_timeout_seconds,
                    max_retries=settings.llm_max_retries,
                ),
            )
        ]
        if settings.embedding_backup_api_key is not None:
            embedding_targets.append(
                ProviderTarget(
                    "backup",
                    OpenAICompatibleProvider(
                        base_url=str(
                            settings.embedding_backup_base_url
                            or settings.embedding_base_url
                        ),
                        api_key=settings.embedding_backup_api_key.get_secret_value(),
                        timeout_seconds=settings.embedding_request_timeout_seconds,
                        connect_timeout_seconds=(
                            settings.provider_connect_timeout_seconds
                        ),
                        max_retries=settings.llm_max_retries,
                    ),
                )
            )
        embedding = ResilientProvider(
            embedding_targets,
            failure_threshold=settings.provider_circuit_failure_threshold,
            reset_seconds=settings.provider_circuit_reset_seconds,
            concurrency_limit=settings.provider_concurrency_limit,
            queue_timeout_seconds=settings.provider_queue_timeout_seconds,
        )
    return ChatOrchestrator(
        settings=settings,
        store=store,
        rate_limiter=RedisRateLimiter(settings),
        retriever=PostgresHybridRetriever(
            settings.database_url.get_secret_value(),
            candidate_limit=settings.retrieval_candidate_limit,
            rrf_k=settings.rrf_k,
        ),
        llm_provider=llm,
        embedding_provider=embedding,
        response_cache=RedisResponseCache(settings),
    )
