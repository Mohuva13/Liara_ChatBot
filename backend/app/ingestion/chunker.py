import hashlib
import re
from collections.abc import Callable

from app.ingestion.models import Chunk, MarkdownUnit, ParsedDocument
from app.retrieval.normalizer import normalize_persian

TOKEN = re.compile(r"[\w\u0600-\u06ff]+|[^\s]", re.UNICODE)


def approximate_token_count(value: str) -> int:
    return max(1, len(TOKEN.findall(value)))


class DocumentChunker:
    def __init__(
        self,
        *,
        max_tokens: int = 650,
        min_tokens: int = 120,
        overlap_tokens: int = 70,
        token_counter: Callable[[str], int] = approximate_token_count,
    ) -> None:
        if not 0 <= overlap_tokens < max_tokens:
            raise ValueError("overlap_tokens must be smaller than max_tokens")
        self.max_tokens = max_tokens
        self.min_tokens = min_tokens
        self.overlap_tokens = overlap_tokens
        self.token_counter = token_counter

    def chunk(self, document: ParsedDocument, units: list[MarkdownUnit]) -> list[Chunk]:
        groups: list[list[MarkdownUnit]] = []
        current: list[MarkdownUnit] = []
        current_tokens = 0

        for unit in units:
            unit_tokens = self.token_counter(unit.content)
            if current and current_tokens + unit_tokens > self.max_tokens:
                groups.append(current)
                current = self._overlap(current)
                current_tokens = sum(
                    self.token_counter(item.content) for item in current
                )
            current.append(unit)
            current_tokens += unit_tokens
        if current:
            groups.append(current)

        if len(groups) > 1 and self._group_tokens(groups[-1]) < self.min_tokens:
            candidate = groups[-2] + groups[-1]
            if self._group_tokens(candidate) <= self.max_tokens:
                groups[-2:] = [candidate]

        chunks: list[Chunk] = []
        for ordinal, group in enumerate(groups):
            content = "\n\n".join(unit.content for unit in group).strip()
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            heading_path = next(
                (unit.heading_path for unit in reversed(group) if unit.heading_path),
                (),
            )
            languages = tuple(
                dict.fromkeys(
                    unit.code_language
                    for unit in group
                    if unit.code_language is not None
                )
            )
            chunks.append(
                Chunk(
                    stable_id=hashlib.sha256(
                        f"{document.stable_id}:{content_hash}".encode()
                    ).hexdigest()[:24],
                    document_id=document.stable_id,
                    ordinal=ordinal,
                    heading_path=heading_path,
                    content=content,
                    normalized_content=normalize_persian(content),
                    content_hash=content_hash,
                    token_count=self.token_counter(content),
                    code_languages=languages,
                )
            )
        return chunks

    def _group_tokens(self, group: list[MarkdownUnit]) -> int:
        return sum(self.token_counter(unit.content) for unit in group)

    def _overlap(self, group: list[MarkdownUnit]) -> list[MarkdownUnit]:
        overlap: list[MarkdownUnit] = []
        tokens = 0
        for unit in reversed(group):
            if unit.kind == "code":
                break
            unit_tokens = self.token_counter(unit.content)
            if overlap and tokens + unit_tokens > self.overlap_tokens:
                break
            overlap.append(unit)
            tokens += unit_tokens
            if tokens >= self.overlap_tokens:
                break
        overlap.reverse()
        return overlap
