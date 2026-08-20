import asyncio
import hashlib
import json
import uuid
from collections.abc import Sequence
from pathlib import Path

import asyncpg

from app.ingestion.chunker import DocumentChunker
from app.ingestion.models import CorpusSnapshot, IngestionConfig, ParsedDocument
from app.ingestion.parser import (
    DocumentParseError,
    DocumentSkipError,
    parse_document,
    parse_units,
)
from app.ingestion.redactor import redact_credentials


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

    async def ingest(self, snapshot: CorpusSnapshot, *, activate: bool) -> str:
        connection = await asyncpg.connect(self.database_url)
        version_id = str(uuid.uuid4())
        try:
            async with connection.transaction():
                existing = await connection.fetchval(
                    "SELECT id::text FROM corpus_versions "
                    "WHERE source_commit = $1 AND manifest_hash = $2",
                    snapshot.source_commit,
                    snapshot.manifest_hash,
                )
                if existing:
                    return str(existing)

                stats = {
                    "discovered": snapshot.discovered,
                    "documents": len(snapshot.documents),
                    "chunks": len(snapshot.chunks),
                    "failed": snapshot.failed,
                    "redactions": snapshot.redactions,
                }
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
                    "content_hash, language) VALUES ($1::uuid, $2, $3, $4, $5, $6, $7)",
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
                if activate:
                    await connection.execute(
                        "UPDATE corpus_versions SET activated_at = NULL, "
                        "status = CASE WHEN status = 'active' "
                        "THEN 'indexed' ELSE status END "
                        "WHERE activated_at IS NOT NULL"
                    )
                    await connection.execute(
                        "UPDATE corpus_versions SET status = 'active', "
                        "activated_at = now() "
                        "WHERE id = $1::uuid",
                        version_id,
                    )
            return version_id
        finally:
            await connection.close()


def scan_corpus(config: IngestionConfig, source_commit: str) -> CorpusSnapshot:
    return CorpusScanner(config).scan(source_commit)


async def ingest_corpus(
    config: IngestionConfig,
    source_commit: str,
    database_url: str,
    migrations_dir: Path,
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
    version_id = await repository.ingest(snapshot, activate=activate)
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
