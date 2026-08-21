from collections.abc import Sequence

import asyncpg

from app.retrieval.fusion import deduplicate_sections, reciprocal_rank_fusion, rerank
from app.retrieval.models import RetrievedChunk
from app.retrieval.normalizer import normalize_search_query, websearch_or_query


def _vector_literal(vector: Sequence[float]) -> str:
    return "[" + ",".join(format(value, ".9g") for value in vector) + "]"


class PostgresHybridRetriever:
    def __init__(self, database_url: str, *, candidate_limit: int, rrf_k: int) -> None:
        self.database_url = database_url
        self.candidate_limit = candidate_limit
        self.rrf_k = rrf_k

    @staticmethod
    def _chunk(record: asyncpg.Record, *, score_name: str) -> RetrievedChunk:
        score = float(record["score"] or 0.0)
        return RetrievedChunk(
            chunk_id=record["chunk_id"],
            document_id=record["document_id"],
            title=record["title"],
            canonical_url=record["canonical_url"],
            heading_path=tuple(record["heading_path"]),
            content=record["content"],
            token_count=record["token_count"],
            source_commit=record["source_commit"],
            corpus_version=str(record["corpus_version"]),
            lexical_score=score if score_name == "lexical_score" else 0.0,
            vector_score=score if score_name == "vector_score" else 0.0,
        )

    async def retrieve(
        self, query: str, embedding: Sequence[float] | None
    ) -> list[RetrievedChunk]:
        normalized = normalize_search_query(query)
        lexical_query = websearch_or_query(query)
        connection = await asyncpg.connect(self.database_url)
        try:
            lexical_rows = await connection.fetch(
                """
                SELECT c.stable_id AS chunk_id, c.document_id, d.title,
                       d.canonical_url, c.heading_path, c.content, c.token_count,
                       v.source_commit, v.id AS corpus_version,
                       ts_rank_cd(c.search_vector, websearch_to_tsquery('simple', $2))
                         + (similarity(c.normalized_content, $1) * 0.3) AS score
                FROM chunks c
                JOIN documents d ON d.version_id = c.version_id
                                AND d.stable_id = c.document_id
                JOIN corpus_versions v ON v.id = c.version_id
                WHERE v.activated_at IS NOT NULL
                  AND (c.search_vector @@ websearch_to_tsquery('simple', $2)
                       OR similarity(c.normalized_content, $1) > 0.03)
                ORDER BY score DESC, c.stable_id
                LIMIT $3
                """,
                normalized,
                lexical_query,
                self.candidate_limit,
            )
            lexical = [
                self._chunk(record, score_name="lexical_score")
                for record in lexical_rows
            ]
            vector: list[RetrievedChunk] = []
            if embedding:
                vector_rows = await connection.fetch(
                    """
                    SELECT c.stable_id AS chunk_id, c.document_id, d.title,
                           d.canonical_url, c.heading_path, c.content, c.token_count,
                           v.source_commit, v.id AS corpus_version,
                           1 - (c.embedding <=> $1::vector) AS score
                    FROM chunks c
                    JOIN documents d ON d.version_id = c.version_id
                                    AND d.stable_id = c.document_id
                    JOIN corpus_versions v ON v.id = c.version_id
                    WHERE v.activated_at IS NOT NULL AND c.embedding IS NOT NULL
                    ORDER BY c.embedding <=> $1::vector, c.stable_id
                    LIMIT $2
                    """,
                    _vector_literal(embedding),
                    self.candidate_limit,
                )
                vector = [
                    self._chunk(record, score_name="vector_score")
                    for record in vector_rows
                ]
        finally:
            await connection.close()

        fused = reciprocal_rank_fusion([lexical, vector], k=self.rrf_k)
        return deduplicate_sections(rerank(query, fused), limit=self.candidate_limit)
