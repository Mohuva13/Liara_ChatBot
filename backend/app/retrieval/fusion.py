from collections import defaultdict
from collections.abc import Sequence

from app.retrieval.models import RetrievedChunk
from app.retrieval.normalizer import retrieval_terms


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[RetrievedChunk]], *, k: int = 60
) -> list[RetrievedChunk]:
    scores: dict[str, float] = defaultdict(float)
    chunks: dict[str, RetrievedChunk] = {}
    for ranking in rankings:
        for rank, chunk in enumerate(ranking, start=1):
            chunks[chunk.chunk_id] = chunk
            scores[chunk.chunk_id] += 1.0 / (k + rank)
    return sorted(
        (
            chunk.with_scores(fused_score=scores[chunk_id])
            for chunk_id, chunk in chunks.items()
        ),
        key=lambda item: item.fused_score,
        reverse=True,
    )


def rerank(query: str, chunks: Sequence[RetrievedChunk]) -> list[RetrievedChunk]:
    query_terms = set(retrieval_terms(query))
    ranked: list[RetrievedChunk] = []
    for chunk in chunks:
        title_terms = set(retrieval_terms(chunk.title))
        heading_terms = set(retrieval_terms(" ".join(chunk.heading_path)))
        content_terms = set(retrieval_terms(chunk.content))
        title_overlap = len(query_terms & title_terms) / max(1, len(query_terms))
        heading_overlap = len(query_terms & heading_terms) / max(1, len(query_terms))
        content_overlap = len(query_terms & content_terms) / max(1, len(query_terms))
        score = (
            chunk.fused_score
            + (0.012 * title_overlap)
            + (0.008 * heading_overlap)
            + (0.004 * content_overlap)
        )
        ranked.append(chunk.with_scores(rerank_score=score))
    return sorted(ranked, key=lambda item: item.rerank_score, reverse=True)


def deduplicate_sections(
    chunks: Sequence[RetrievedChunk], *, limit: int
) -> list[RetrievedChunk]:
    selected: list[RetrievedChunk] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for chunk in chunks:
        key = (chunk.document_id, chunk.heading_path)
        if key in seen:
            continue
        seen.add(key)
        selected.append(chunk)
        if len(selected) >= limit:
            break
    return selected
