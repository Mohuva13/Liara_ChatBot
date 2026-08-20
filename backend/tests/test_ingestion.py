from pathlib import Path

import pytest

from app.ingestion.chunker import DocumentChunker
from app.ingestion.models import Chunk, CorpusSnapshot, IngestionConfig, ParsedDocument
from app.ingestion.parser import DocumentParseError, parse_document, parse_units
from app.ingestion.pipeline import embed_snapshot, scan_corpus
from app.ingestion.redactor import redact_credentials
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
