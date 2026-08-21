from pathlib import Path

import pytest

import app.ingestion.pipeline as ingestion_pipeline
from app.ingestion.chunker import DocumentChunker, approximate_token_count
from app.ingestion.cli import _commit_from_git_metadata
from app.ingestion.models import (
    Chunk,
    CorpusSnapshot,
    IngestionConfig,
    MarkdownUnit,
    ParsedDocument,
)
from app.ingestion.parser import DocumentParseError, parse_document, parse_units
from app.ingestion.pipeline import embed_snapshot, scan_corpus
from app.ingestion.redactor import redact_credentials
from app.providers.base import ProviderFailure
from app.retrieval.normalizer import normalize_persian


def test_parse_document_extracts_canonical_metadata(tmp_path: Path) -> None:
    docs_root = tmp_path
    path = docs_root / "public" / "llms" / "sample.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        "\ufeffOriginal link: https://docs.liara.ir/paas/test/\n\n"
        "# عنوان تست\n\nمتن معتبر\n\n"
        "## all links\n\n[All links](https://docs.liara.ir/all-links-llms.txt)\n",
        encoding="utf-8",
    )

    document = parse_document(path, docs_root)

    assert document.canonical_url == "https://docs.liara.ir/paas/test/"
    assert document.title == "عنوان تست"
    assert "all-links-llms" not in document.content
    assert document.source_path == "public/llms/sample.md"


def test_parse_document_rejects_non_liara_canonical_url(tmp_path: Path) -> None:
    path = tmp_path / "public" / "llms" / "unsafe.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        "Original link: https://example.com/unsafe/\n# عنوان\nمتن",
        encoding="utf-8",
    )

    with pytest.raises(DocumentParseError):
        parse_document(path, tmp_path)


def test_canonical_url_database_constraint_accepts_official_docs_only() -> None:
    migrations_dir = Path(__file__).parents[1] / "migrations"
    initial = (migrations_dir / "001_initial_corpus.sql").read_text(encoding="utf-8")
    repair = (migrations_dir / "002_fix_canonical_url_constraint.sql").read_text(
        encoding="utf-8"
    )

    expected = "canonical_url LIKE 'https://docs.liara.ir/%'"
    assert expected in initial
    assert expected in repair
    assert "DROP CONSTRAINT IF EXISTS documents_canonical_url_check" in repair
    assert "strpos(constraint_definition, 'https://docs.liara.ir/%')" in repair


def test_redaction_preserves_names_and_code_structure() -> None:
    source = (
        'DATABASE_PASSWORD="actual-example-password"\n'
        "Authorization: Bearer abcdefghijklmnopqrstuvwxyz\n"
        "redis://user:not-safe-password@example:6379/0"
    )

    redacted, report = redact_credentials(source)

    assert "actual-example-password" not in redacted
    assert "abcdefghijklmnopqrstuvwxyz" not in redacted
    assert "not-safe-password" not in redacted
    assert "DATABASE_PASSWORD" in redacted
    assert "<YOUR_DATABASE_PASSWORD>" in redacted
    assert report.count == 3


def test_redaction_removes_large_embedded_data_url() -> None:
    payload = "A" * 10_000
    source = f"```ts\nconst image = 'data:image/png;base64,{payload}'\n```"

    redacted, report = redact_credentials(source)

    assert payload not in redacted
    assert "data:image/png;base64,<REDACTED_EMBEDDED_ASSET>" in redacted
    assert redacted.count("```") == 2
    assert report.rule_counts["embedded_data_url"] == 1


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("كاربرد يک", "کاربرد یک"),
        ("نسخه ۱۲۳", "نسخه 123"),
        ("فاصله\u200cنیم", "فاصله نیم"),
    ],
)
def test_persian_normalization_equivalence(left: str, right: str) -> None:
    assert normalize_persian(left) == normalize_persian(right)


def test_chunker_keeps_code_fence_atomic() -> None:
    document = ParsedDocument(
        stable_id="doc",
        source_path="public/llms/test.md",
        canonical_url="https://docs.liara.ir/test/",
        title="تست",
        content="",
        content_hash="hash",
    )
    long_code = (
        "```bash\n" + "\n".join(f"echo {index}" for index in range(80)) + "\n```"
    )
    content = "# تست\n\nپاراگراف قبل\n\n" + long_code + "\n\nپاراگراف بعد"

    chunks = DocumentChunker(max_tokens=30, min_tokens=1, overlap_tokens=5).chunk(
        document, parse_units(content)
    )

    code_chunks = [chunk for chunk in chunks if "```bash" in chunk.content]
    assert len(code_chunks) == 1
    assert code_chunks[0].content.count("```") == 2
    assert code_chunks[0].code_languages == ("bash",)


def test_chunker_splits_long_non_code_line_within_limit() -> None:
    document = ParsedDocument(
        stable_id="doc",
        source_path="public/llms/test.md",
        canonical_url="https://docs.liara.ir/test/",
        title="تست",
        content="",
        content_hash="hash",
    )
    content = "# تست\n\n" + "واژه " * 200

    chunks = DocumentChunker(max_tokens=30, min_tokens=1, overlap_tokens=5).chunk(
        document, parse_units(content)
    )

    assert len(chunks) > 1
    assert all(chunk.token_count <= 30 for chunk in chunks)
    assert "واژه" in " ".join(chunk.content for chunk in chunks)


def test_chunker_disambiguates_repeated_content_deterministically() -> None:
    document = ParsedDocument(
        stable_id="doc",
        source_path="public/llms/test.md",
        canonical_url="https://docs.liara.ir/test/",
        title="تست",
        content="",
        content_hash="hash",
    )
    units = [
        MarkdownUnit(("اول",), "متن یکسان", "text"),
        MarkdownUnit(("میانی",), "متن متفاوت", "text"),
        MarkdownUnit(("آخر",), "متن یکسان", "text"),
    ]
    chunker = DocumentChunker(
        max_tokens=1,
        min_tokens=1,
        overlap_tokens=0,
        token_counter=lambda _: 1,
    )

    first = chunker.chunk(document, units)
    second = chunker.chunk(document, units)

    assert len({chunk.stable_id for chunk in first}) == len(first)
    assert [chunk.stable_id for chunk in first] == [chunk.stable_id for chunk in second]
    assert first[0].content_hash == first[2].content_hash
    assert first[0].stable_id != first[2].stable_id


def test_token_estimate_accounts_for_long_unbroken_values() -> None:
    assert approximate_token_count("A" * 40_000) >= 10_000


def test_source_commit_fallback_resolves_packed_ref(tmp_path: Path) -> None:
    commit = "a" * 40
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git_dir / "packed-refs").write_text(
        f"# pack-refs\n{commit} refs/heads/main\n", encoding="utf-8"
    )

    assert _commit_from_git_metadata(tmp_path) == commit


def test_source_commit_fallback_rejects_unresolved_ref(tmp_path: Path) -> None:
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="cannot resolve"):
        _commit_from_git_metadata(tmp_path)


def test_parser_repairs_generated_unclosed_fence() -> None:
    units = parse_units("# نمونه\n\n```yaml\nkey: value")

    code = next(unit for unit in units if unit.kind == "code")
    assert code.content.endswith("```")


@pytest.mark.asyncio
async def test_embedding_pipeline_batches_and_validates_dimensions() -> None:
    document = ParsedDocument(
        stable_id="doc",
        source_path="public/llms/test.md",
        canonical_url="https://docs.liara.ir/test/",
        title="عنوان سند",
        content="متن",
        content_hash="doc-hash",
    )
    chunks = tuple(
        Chunk(
            stable_id=f"chunk-{index}",
            document_id="doc",
            ordinal=index,
            heading_path=("بخش",),
            content=f"متن {index}",
            normalized_content=f"متن {index}",
            content_hash=f"hash-{index}",
            token_count=2,
        )
        for index in range(3)
    )
    snapshot = CorpusSnapshot(
        source_commit="commit",
        manifest_hash="manifest",
        documents=(document,),
        chunks=chunks,
        discovered=1,
        skipped=0,
        failed=0,
    )

    class FakeEmbeddingProvider:
        def __init__(self) -> None:
            self.requests: list[tuple[list[str], str]] = []

        async def embed(
            self,
            inputs: list[str],
            *,
            model: str,
            dimensions: int | None,
            request_id: str,
        ) -> list[list[float]]:
            assert model == "embedding-model"
            assert dimensions == 2
            self.requests.append((list(inputs), request_id))
            return [[float(index), 1.0] for index, _ in enumerate(inputs)]

    provider = FakeEmbeddingProvider()
    vectors = await embed_snapshot(  # type: ignore[arg-type]
        snapshot,
        provider,
        model="embedding-model",
        dimensions=2,
        batch_size=2,
        request_id_prefix="ingest-test",
    )

    assert len(vectors) == 3
    assert [request_id for _, request_id in provider.requests] == [
        "ingest-test-1",
        "ingest-test-2",
    ]
    assert all("عنوان سند" in text for batch, _ in provider.requests for text in batch)


@pytest.mark.asyncio
async def test_embedding_pipeline_rejects_provider_dimension_mismatch() -> None:
    snapshot = CorpusSnapshot(
        source_commit="commit",
        manifest_hash="manifest",
        documents=(),
        chunks=(
            Chunk(
                stable_id="chunk",
                document_id="doc",
                ordinal=0,
                heading_path=(),
                content="متن",
                normalized_content="متن",
                content_hash="hash",
                token_count=1,
            ),
        ),
        discovered=1,
        skipped=0,
        failed=0,
    )

    class WrongDimensionProvider:
        async def embed(
            self,
            inputs: list[str],
            *,
            model: str,
            dimensions: int | None,
            request_id: str,
        ) -> list[list[float]]:
            return [[1.0] for _ in inputs]

    with pytest.raises(ValueError, match="dimensions"):
        await embed_snapshot(  # type: ignore[arg-type]
            snapshot,
            WrongDimensionProvider(),
            model="embedding-model",
            dimensions=2,
            batch_size=8,
            request_id_prefix="ingest-test",
        )


@pytest.mark.asyncio
async def test_ingestion_checkpoints_batches_and_resumes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    document = ParsedDocument(
        stable_id="doc",
        source_path="public/llms/test.md",
        canonical_url="https://docs.liara.ir/test/",
        title="عنوان سند",
        content="متن",
        content_hash="doc-hash",
    )
    chunks = tuple(
        Chunk(
            stable_id=f"chunk-{index}",
            document_id="doc",
            ordinal=index,
            heading_path=("بخش",),
            content=f"متن {index}",
            normalized_content=f"متن {index}",
            content_hash=f"hash-{index}",
            token_count=2,
        )
        for index in range(3)
    )
    snapshot = CorpusSnapshot(
        source_commit="commit",
        manifest_hash="manifest",
        documents=(document,),
        chunks=chunks,
        discovered=1,
        skipped=0,
        failed=0,
    )

    class FakeRepository:
        def __init__(self) -> None:
            self.embedded: set[str] = set()
            self.finalized = False

        async def apply_migrations(self, migrations_dir: Path) -> None:
            return None

        async def prepare(
            self,
            prepared_snapshot: CorpusSnapshot,
            *,
            embedding_model: str,
            embedding_dimensions: int,
        ) -> tuple[str, str]:
            return "version", "parsed"

        async def pending_chunks(
            self, version_id: str, prepared_snapshot: CorpusSnapshot
        ) -> tuple[Chunk, ...]:
            return tuple(
                chunk
                for chunk in prepared_snapshot.chunks
                if chunk.stable_id not in self.embedded
            )

        async def store_embedding_batch(
            self,
            version_id: str,
            stored_chunks: tuple[Chunk, ...],
            embeddings: list[list[float]],
            dimensions: int,
        ) -> int:
            self.embedded.update(chunk.stable_id for chunk in stored_chunks)
            return len(self.embedded)

        async def finalize(
            self,
            version_id: str,
            finalized_snapshot: CorpusSnapshot,
            *,
            embedding_model: str,
            embedding_dimensions: int,
            activate: bool,
        ) -> None:
            assert self.embedded == {chunk.stable_id for chunk in chunks}
            self.finalized = True

    class InterruptingProvider:
        def __init__(self) -> None:
            self.calls = 0

        async def embed(
            self,
            inputs: list[str],
            *,
            model: str,
            dimensions: int | None,
            request_id: str,
        ) -> list[list[float]]:
            self.calls += 1
            if self.calls == 2:
                raise ProviderFailure("provider_unavailable", retryable=True)
            return [[1.0, 2.0] for _ in inputs]

    class SuccessfulProvider:
        def __init__(self) -> None:
            self.inputs: list[str] = []

        async def embed(
            self,
            inputs: list[str],
            *,
            model: str,
            dimensions: int | None,
            request_id: str,
        ) -> list[list[float]]:
            self.inputs.extend(inputs)
            return [[1.0, 2.0] for _ in inputs]

    repository = FakeRepository()
    monkeypatch.setattr(ingestion_pipeline, "scan_corpus", lambda *_: snapshot)

    async def scan_without_thread(function: object, *args: object) -> CorpusSnapshot:
        del function, args
        return snapshot

    monkeypatch.setattr(ingestion_pipeline.asyncio, "to_thread", scan_without_thread)
    monkeypatch.setattr(
        ingestion_pipeline,
        "PostgresCorpusRepository",
        lambda database_url: repository,
    )
    config = IngestionConfig(docs_root=tmp_path, embedding_batch_size=2)

    with pytest.raises(ProviderFailure, match="provider_unavailable"):
        await ingestion_pipeline.ingest_corpus(
            config,
            "commit",
            "postgresql://test",
            tmp_path,
            InterruptingProvider(),  # type: ignore[arg-type]
            "embedding-model",
            2,
            activate=True,
        )

    assert repository.embedded == {"chunk-0", "chunk-1"}
    resumed_provider = SuccessfulProvider()
    version_id, _ = await ingestion_pipeline.ingest_corpus(
        config,
        "commit",
        "postgresql://test",
        tmp_path,
        resumed_provider,  # type: ignore[arg-type]
        "embedding-model",
        2,
        activate=True,
    )

    assert version_id == "version"
    assert len(resumed_provider.inputs) == 1
    assert repository.finalized is True


def test_real_corpus_inventory_is_complete() -> None:
    docs_root = Path("/home/mohuva/Desktop/hackaton/docs")
    if not docs_root.exists():
        pytest.skip("Liara documentation checkout is not available")

    snapshot = scan_corpus(IngestionConfig(docs_root=docs_root), "test-commit")

    discovered = len(list((docs_root / "public" / "llms").rglob("*.md")))
    assert snapshot.discovered == discovered
    assert len(snapshot.documents) + snapshot.skipped == discovered
    assert snapshot.failed == 0
    assert snapshot.chunks
    assert all(
        source.canonical_url.startswith("https://docs.liara.ir/")
        for source in snapshot.documents
    )
