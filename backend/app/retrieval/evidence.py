import re
from collections.abc import Sequence

from app.retrieval.models import EvidenceDecision, RetrievedChunk
from app.retrieval.normalizer import (
    RETRIEVAL_ENTITY_TERMS,
    normalize_persian,
    retrieval_terms,
)

NEGATIVE_MARKERS = ("پشتیبانی نمی کند", "امکان ندارد", "مجاز نیست")
POSITIVE_MARKERS = ("پشتیبانی می کند", "امکان دارد", "مجاز است")
SENTENCE_BOUNDARY = re.compile(r"[\n.!؟؛]+")
POLARITY_NOISE_TERMS = {
    "آن",
    "این",
    "افزونه",
    "است",
    "امکان",
    "پشتیبانی",
    "قابلیت",
    "کند",
    "می",
    "مجاز",
    "موارد",
    "نمی",
    "نیست",
    "هست",
}


def meaningful_terms(value: str) -> set[str]:
    return set(retrieval_terms(value))


def _polarized_subjects(content: str, markers: Sequence[str]) -> list[set[str]]:
    subjects: list[set[str]] = []
    for sentence in SENTENCE_BOUNDARY.split(normalize_persian(content)):
        if not any(marker in sentence for marker in markers):
            continue
        terms = meaningful_terms(sentence) - POLARITY_NOISE_TERMS
        if terms:
            subjects.append(terms)
    return subjects


def _same_proposition(left: set[str], right: set[str]) -> bool:
    shared = left & right
    return bool(shared) and len(shared) / max(1, len(left | right)) >= 0.6


def _has_contradiction(chunks: Sequence[RetrievedChunk]) -> bool:
    polarities = [
        (
            chunk.document_id,
            _polarized_subjects(chunk.content, NEGATIVE_MARKERS),
            _polarized_subjects(chunk.content, POSITIVE_MARKERS),
        )
        for chunk in chunks
    ]
    for index, (left_document, left_negative, left_positive) in enumerate(polarities):
        for right_document, right_negative, right_positive in polarities[index + 1 :]:
            if left_document == right_document:
                continue
            opposing = (
                (negative, positive)
                for negatives, positives in (
                    (left_negative, right_positive),
                    (right_negative, left_positive),
                )
                for negative in negatives
                for positive in positives
            )
            if any(
                _same_proposition(negative, positive) for negative, positive in opposing
            ):
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
