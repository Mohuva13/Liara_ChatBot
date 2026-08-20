from dataclasses import dataclass, replace


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    chunk_id: str
    document_id: str
    title: str
    canonical_url: str
    heading_path: tuple[str, ...]
    content: str
    token_count: int
    source_commit: str
    corpus_version: str
    lexical_score: float = 0.0
    vector_score: float = 0.0
    fused_score: float = 0.0
    rerank_score: float = 0.0

    def with_scores(
        self,
        *,
        lexical_score: float | None = None,
        vector_score: float | None = None,
        fused_score: float | None = None,
        rerank_score: float | None = None,
    ) -> "RetrievedChunk":
        return replace(
            self,
            lexical_score=(
                self.lexical_score if lexical_score is None else lexical_score
            ),
            vector_score=self.vector_score if vector_score is None else vector_score,
            fused_score=self.fused_score if fused_score is None else fused_score,
            rerank_score=self.rerank_score if rerank_score is None else rerank_score,
        )


@dataclass(frozen=True, slots=True)
class EvidenceDecision:
    sufficient: bool
    reason: str
    query_coverage: float
    contradictory: bool
    chunks: tuple[RetrievedChunk, ...]
