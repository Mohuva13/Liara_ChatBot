from collections.abc import Sequence

from app.retrieval.models import EvidenceDecision, RetrievedChunk
from app.retrieval.normalizer import (
    RETRIEVAL_ENTITY_TERMS,
    normalize_persian,
    retrieval_terms,
)

NEGATIVE_MARKERS = ("پشتیبانی نمی کند", "امکان ندارد", "مجاز نیست")
POSITIVE_MARKERS = ("پشتیبانی می کند", "امکان دارد", "مجاز است")


def meaningful_terms(value: str) -> set[str]:
    return set(retrieval_terms(value))


def _has_contradiction(chunks: Sequence[RetrievedChunk]) -> bool:
    for index, left in enumerate(chunks):
        left_text = normalize_persian(left.content)
        left_terms = meaningful_terms(left.content)
        for right in chunks[index + 1 :]:
            if left.document_id == right.document_id:
                continue
            right_text = normalize_persian(right.content)
            shared = left_terms & meaningful_terms(right.content)
            if len(shared) < 3:
                continue
            left_negative = any(marker in left_text for marker in NEGATIVE_MARKERS)
            right_negative = any(marker in right_text for marker in NEGATIVE_MARKERS)
            left_positive = any(marker in left_text for marker in POSITIVE_MARKERS)
            right_positive = any(marker in right_text for marker in POSITIVE_MARKERS)
            if (left_negative and right_positive) or (right_negative and left_positive):
                return True
    return False


def assess_evidence(
    query: str,
    chunks: Sequence[RetrievedChunk],
    *,
    min_score: float,
    min_query_coverage: float,
    limit: int,
    max_tokens: int,
) -> EvidenceDecision:
    selected: list[RetrievedChunk] = []
    used_tokens = 0
    for chunk in chunks[:limit]:
        if selected and used_tokens + chunk.token_count > max_tokens:
            break
        selected.append(chunk)
        used_tokens += chunk.token_count

    query_terms = meaningful_terms(query)
    evidence_terms = (
        set().union(
            *(
                meaningful_terms(
                    " ".join((chunk.title, " ".join(chunk.heading_path), chunk.content))
                )
                for chunk in selected
            )
        )
        if selected
        else set()
    )
    coverage = len(query_terms & evidence_terms) / max(1, len(query_terms))
    required_entities = query_terms & RETRIEVAL_ENTITY_TERMS
    missing_entities = required_entities - evidence_terms
    contradictory = _has_contradiction(selected)
    top_score = selected[0].rerank_score if selected else 0.0

    if not selected:
        reason = "no_results"
    elif contradictory:
        reason = "contradictory_sources"
    elif top_score < min_score:
        reason = "low_relevance"
    elif missing_entities:
        reason = "missing_entity_coverage"
    elif coverage < min_query_coverage:
        reason = "insufficient_query_coverage"
    else:
        reason = "sufficient"
    return EvidenceDecision(
        sufficient=reason == "sufficient",
        reason=reason,
        query_coverage=coverage,
        contradictory=contradictory,
        chunks=tuple(selected),
    )
