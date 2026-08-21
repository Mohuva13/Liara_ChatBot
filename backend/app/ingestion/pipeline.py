import asyncio
import hashlib
import json
import math
import uuid
from collections.abc import Sequence
from pathlib import Path

import asyncpg

from app.core.logging import telemetry_event
from app.ingestion.chunker import DocumentChunker
from app.ingestion.models import CorpusSnapshot, IngestionConfig, ParsedDocument
from app.ingestion.parser import (
    DocumentParseError,
    DocumentSkipError,
    parse_document,
    parse_units,
)
from app.ingestion.redactor import redact_credentials
from app.providers.base import AIProvider


class CorpusScanner:
    def __init__(self, config: IngestionConfig) -> None:
        self.config = config
        self.chunker = DocumentChunker(
            max_tokens=config.max_tokens,
            min_tokens=config.min_tokens,
            overlap_tokens=config.overlap_tokens,
        )

    def scan(self, source_commit: str) -> CorpusSnapshot:
        root = self.config.docs_root / "public" / "llms"
        paths = sorted(root.rglob("*.md"))
        documents: list[ParsedDocument] = []
        chunks = []
        failures: list[str] = []
        redactions = 0
        skipped = 0

        for path in paths:
            try:
                parsed = parse_document(path, self.config.docs_root)
                safe_content, report = redact_credentials(parsed.content)
                redactions += report.count
                safe_document = ParsedDocument(
                    stable_id=parsed.stable_id,
                    source_path=parsed.source_path,
                    canonical_url=parsed.canonical_url,
                    title=parsed.title,
                    content=safe_content,
                    content_hash=hashlib.sha256(safe_content.encode()).hexdigest(),
                    language=parsed.language,
                )
                parsed_units = parse_units(safe_content)
                documents.append(safe_document)
                chunks.extend(self.chunker.chunk(safe_document, parsed_units))
            except DocumentSkipError:
                skipped += 1
            except (OSError, UnicodeError, DocumentParseError, ValueError) as error:
                relative = path.relative_to(self.config.docs_root).as_posix()
                failures.append(f"{relative}: {error}")

        manifest = hashlib.sha256()
        for document in documents:
            manifest.update(document.source_path.encode())
            manifest.update(document.content_hash.encode())
        return CorpusSnapshot(
            source_commit=source_commit,
            manifest_hash=manifest.hexdigest(),
            documents=tuple(documents),
            chunks=tuple(chunks),
            discovered=len(paths),
            skipped=skipped,
            failed=len(failures),
            failures=tuple(failures),
            redactions=redactions,
        )


class PostgresCorpusRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    async def apply_migrations(self, migrations_dir: Path) -> None:
        connection = await asyncpg.connect(self.database_url)
        try:
            for migration in sorted(migrations_dir.glob("*.sql")):
                await connection.execute(migration.read_text(encoding="utf-8"))
        finally:
            await connection.close()

    async def find_version(self, snapshot: CorpusSnapshot) -> tuple[str, str] | None:
        connection = await asyncpg.connect(self.database_url)
        try:
            row = await connection.fetchrow(
                "SELECT id::text, status FROM corpus_versions "
                "WHERE source_commit = $1 AND manifest_hash = $2",
                snapshot.source_commit,
                snapshot.manifest_hash,
            )
            if row is None:
                return None
            return str(row["id"]), str(row["status"])
        finally:
            await connection.close()

    @staticmethod
    async def _activate(connection: asyncpg.Connection, version_id: str) -> None:
        missing = await connection.fetchval(
            "SELECT count(*) FROM chunks "
            "WHERE version_id = $1::uuid AND embedding IS NULL",
            version_id,
        )
        if missing:
            raise RuntimeError(
                f"cannot activate corpus version with {missing} missing embedding(s)"
            )
        await connection.execute(
            "UPDATE corpus_versions SET activated_at = NULL, "
            "status = CASE WHEN status = 'active' THEN 'indexed' ELSE status END "
            "WHERE activated_at IS NOT NULL AND id <> $1::uuid",
            version_id,
        )
        await connection.execute(
            "UPDATE corpus_versions SET status = 'active', activated_at = now() "
            "WHERE id = $1::uuid",
            version_id,
        )

    async def activate(self, version_id: str) -> None:
        connection = await asyncpg.connect(self.database_url)
        try:
            async with connection.transaction():
                await self._activate(connection, version_id)
        finally:
            await connection.close()

    async def ingest(
        self,
        snapshot: CorpusSnapshot,
        embeddings: Sequence[Sequence[float]],
        *,
        embedding_model: str,
        embedding_dimensions: int,
        activate: bool,
    ) -> str:
        _validate_embeddings(snapshot, embeddings, embedding_dimensions)
        connection = await asyncpg.connect(self.database_url)
        version_id = str(uuid.uuid4())
        try:
            async with connection.transaction():
                existing = await connection.fetchrow(
                    "SELECT id::text, status FROM corpus_versions "
                    "WHERE source_commit = $1 AND manifest_hash = $2",
                    snapshot.source_commit,
                    snapshot.manifest_hash,
                )
                if existing:
                    version_id = str(existing["id"])
                    if existing["status"] in {
                        "embedded",
                        "indexed",
                        "evaluated",
                        "active",
                    }:
                        if activate and existing["status"] != "active":
                            await self._activate(connection, version_id)
                        return version_id

                stats = {
                    "discovered": snapshot.discovered,
                    "documents": len(snapshot.documents),
                    "chunks": len(snapshot.chunks),
                    "failed": snapshot.failed,
                    "redactions": snapshot.redactions,
                    "embedding_model": embedding_model,
                    "embedding_dimensions": embedding_dimensions,
                }
                if not existing:
                    await connection.execute(
                        "INSERT INTO corpus_versions "
                        "(id, source_commit, manifest_hash, status, stats) "
                        "VALUES ($1::uuid, $2, $3, 'parsed', $4::jsonb)",
                        version_id,
                        snapshot.source_commit,
                        snapshot.manifest_hash,
                        json.dumps(stats),
                    )
                    await connection.executemany(
                        "INSERT INTO documents "
                        "(version_id, stable_id, source_path, canonical_url, title, "
                        "content_hash, language) "
                        "VALUES ($1::uuid, $2, $3, $4, $5, $6, $7)",
                        [
                            (
                                version_id,
                                document.stable_id,
                                document.source_path,
                                document.canonical_url,
                                document.title,
                                document.content_hash,
                                document.language,
                            )
                            for document in snapshot.documents
                        ],
                    )
                    await connection.executemany(
                        "INSERT INTO chunks "
                        "(version_id, document_id, stable_id, ordinal, heading_path, "
                        "content, normalized_content, content_hash, token_count, "
                        "code_languages) "
                        "VALUES ($1::uuid, $2, $3, $4, $5, $6, $7, $8, $9, $10)",
                        [
                            (
                                version_id,
                                chunk.document_id,
                                chunk.stable_id,
                                chunk.ordinal,
                                list(chunk.heading_path),
                                chunk.content,
                                chunk.normalized_content,
                                chunk.content_hash,
                                chunk.token_count,
                                list(chunk.code_languages),
                            )
                            for chunk in snapshot.chunks
                        ],
                    )
                await connection.executemany(
                    "UPDATE chunks SET embedding = $3::vector "
                    "WHERE version_id = $1::uuid AND stable_id = $2",
                    [
                        (version_id, chunk.stable_id, _vector_literal(vector))
                        for chunk, vector in zip(
                            snapshot.chunks, embeddings, strict=True
                        )
                    ],
                )
                await connection.execute(
                    "UPDATE corpus_versions SET status = 'embedded', stats = $2::jsonb "
                    "WHERE id = $1::uuid",
                    version_id,
                    json.dumps(stats),
                )
                if activate:
                    await self._activate(connection, version_id)
            return version_id
        finally:
            await connection.close()


def _vector_literal(values: Sequence[float]) -> str:
    return "[" + ",".join(format(value, ".12g") for value in values) + "]"


def _validate_embeddings(
    snapshot: CorpusSnapshot,
    embeddings: Sequence[Sequence[float]],
    dimensions: int,
) -> None:
    if len(embeddings) != len(snapshot.chunks):
        raise ValueError("embedding count does not match chunk count")
    for vector in embeddings:
        if len(vector) != dimensions:
            raise ValueError("embedding dimensions do not match configuration")
        if not all(math.isfinite(value) for value in vector):
            raise ValueError("embedding contains a non-finite value")


async def embed_snapshot(
    snapshot: CorpusSnapshot,
    provider: AIProvider,
    *,
    model: str,
    dimensions: int,
    batch_size: int,
    request_id_prefix: str,
) -> tuple[tuple[float, ...], ...]:
    if batch_size < 1:
        raise ValueError("embedding batch size must be positive")
    titles = {document.stable_id: document.title for document in snapshot.documents}
    vectors: list[tuple[float, ...]] = []
    total_batches = (len(snapshot.chunks) + batch_size - 1) // batch_size
    for offset in range(0, len(snapshot.chunks), batch_size):
        batch_num = offset // batch_size + 1
        batch = snapshot.chunks[offset : offset + batch_size]
        inputs = [
            "\n".join(
                part
                for part in (
                    titles.get(chunk.document_id, ""),
                    " > ".join(chunk.heading_path),
                    chunk.content,
                )
                if part
            )
            for chunk in batch
        ]
        telemetry_event(
            "ingestion_embedding_batch_started",
            batch=batch_num,
            total_batches=total_batches,
            batch_size=len(batch),
        )
        result = await provider.embed(
            inputs,
            model=model,
            dimensions=dimensions,
            request_id=f"{request_id_prefix}-{batch_num}",
        )
        vectors.extend(tuple(vector) for vector in result)
    telemetry_event(
        "ingestion_embedding_completed",
        chunks=len(snapshot.chunks),
    )
    embedded = tuple(vectors)
    _validate_embeddings(snapshot, embedded, dimensions)
    return embedded


def scan_corpus(config: IngestionConfig, source_commit: str) -> CorpusSnapshot:
    return CorpusScanner(config).scan(source_commit)


async def ingest_corpus(
    config: IngestionConfig,
    source_commit: str,
    database_url: str,
    migrations_dir: Path,
    embedding_provider: AIProvider,
    embedding_model: str,
    embedding_dimensions: int,
    *,
    activate: bool = False,
) -> tuple[str, CorpusSnapshot]:
    snapshot = await asyncio.to_thread(scan_corpus, config, source_commit)
    if snapshot.failed:
        raise RuntimeError(
            f"corpus validation failed for {snapshot.failed} document(s): "
            + "; ".join(snapshot.failures[:5])
        )
    repository = PostgresCorpusRepository(database_url)
    await repository.apply_migrations(migrations_dir)
    existing = await repository.find_version(snapshot)
    if existing and existing[1] in {"embedded", "indexed", "evaluated", "active"}:
        if activate and existing[1] != "active":
            await repository.activate(existing[0])
        return existing[0], snapshot
    embeddings = await embed_snapshot(
        snapshot,
        embedding_provider,
        model=embedding_model,
        dimensions=embedding_dimensions,
        batch_size=config.embedding_batch_size,
        request_id_prefix=f"ingest-{snapshot.manifest_hash[:12]}",
    )
    version_id = await repository.ingest(
        snapshot,
        embeddings,
        embedding_model=embedding_model,
        embedding_dimensions=embedding_dimensions,
        activate=activate,
    )
    return version_id, snapshot


def snapshot_report(snapshot: CorpusSnapshot) -> dict[str, int | str | Sequence[str]]:
    return {
        "source_commit": snapshot.source_commit,
        "manifest_hash": snapshot.manifest_hash,
        "discovered": snapshot.discovered,
        "documents": len(snapshot.documents),
        "chunks": len(snapshot.chunks),
        "skipped": snapshot.skipped,
        "failed": snapshot.failed,
        "redactions": snapshot.redactions,
        "failures": snapshot.failures,
    }
