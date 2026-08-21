from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    stable_id: str
    source_path: str
    canonical_url: str
    title: str
    content: str
    content_hash: str
    language: str = "fa"


@dataclass(frozen=True, slots=True)
class MarkdownUnit:
    heading_path: tuple[str, ...]
    content: str
    kind: str
    code_language: str | None = None


@dataclass(frozen=True, slots=True)
class Chunk:
    stable_id: str
    document_id: str
    ordinal: int
    heading_path: tuple[str, ...]
    content: str
    normalized_content: str
    content_hash: str
    token_count: int
    code_languages: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CorpusSnapshot:
    source_commit: str
    manifest_hash: str
    documents: tuple[ParsedDocument, ...]
    chunks: tuple[Chunk, ...]
    discovered: int
    skipped: int
    failed: int
    failures: tuple[str, ...] = ()
    redactions: int = 0


@dataclass(frozen=True, slots=True)
class IngestionConfig:
    docs_root: Path
    max_tokens: int = 650
    min_tokens: int = 120
    overlap_tokens: int = 70
    embedding_batch_size: int = 16


@dataclass(slots=True)
class RedactionReport:
    count: int = 0
    rule_counts: dict[str, int] = field(default_factory=dict)

    def record(self, rule: str, count: int) -> None:
        if count <= 0:
            return
        self.count += count
        self.rule_counts[rule] = self.rule_counts.get(rule, 0) + count
