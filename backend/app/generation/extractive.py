import re
from collections.abc import Sequence

from app.generation.models import ValidatedAnswer
from app.retrieval.models import RetrievedChunk
from app.retrieval.normalizer import (
    RETRIEVAL_ENTITY_TERMS,
    normalize_persian,
    retrieval_terms,
)

SENTENCE_BOUNDARY = re.compile(r"(?<=[.!؟])\s+|\n+")
MARKDOWN_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
URL = re.compile(r"https?://\S+", re.IGNORECASE)
SAFE_FACT_MARKERS = (
    "پشتیبانی نمی کند",
    "امکان ندارد",
    "مجاز نیست",
    "در دسترس نیست",
)


def _clean_sentence(value: str) -> str:
    cleaned = MARKDOWN_IMAGE.sub("", value)
    cleaned = MARKDOWN_LINK.sub(r"\1", cleaned)
    cleaned = URL.sub("", cleaned)
    cleaned = cleaned.strip().lstrip(">-* ").strip()
    return " ".join(cleaned.split())


def extractive_grounded_fallback(
    query: str, evidence: Sequence[RetrievedChunk]
) -> ValidatedAnswer | None:
    """Return a narrow documented negative fact when generation cannot be validated."""
    query_terms = set(retrieval_terms(query))
    required_entities = query_terms & RETRIEVAL_ENTITY_TERMS
    candidates: list[tuple[float, RetrievedChunk, str]] = []
    for chunk in evidence:
        metadata_terms = set(
            retrieval_terms(" ".join((chunk.title, " ".join(chunk.heading_path))))
        )
        for raw_sentence in SENTENCE_BOUNDARY.split(chunk.content):
            sentence = _clean_sentence(raw_sentence)
            if not sentence or len(sentence) > 800:
                continue
            normalized = normalize_persian(sentence)
            if not any(marker in normalized for marker in SAFE_FACT_MARKERS):
                continue
            sentence_terms = set(retrieval_terms(sentence))
            combined_terms = metadata_terms | sentence_terms
            if required_entities - combined_terms:
                continue
            overlap = len(query_terms & combined_terms) / max(1, len(query_terms))
            if overlap < 0.35:
                continue
            entity_overlap = len(required_entities & combined_terms) / max(
                1, len(required_entities)
            )
            candidates.append((overlap + entity_overlap, chunk, sentence))
    if not candidates:
        return None
    _, chunk, sentence = max(candidates, key=lambda item: item[0])
    return ValidatedAnswer(
        answer_markdown=f"طبق مستندات رسمی لیارا:\n\n> {sentence}",
        source_ids=[chunk.chunk_id],
        suggestions=[],
    )
