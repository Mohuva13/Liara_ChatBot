import hashlib
import re
from collections.abc import Callable

from app.ingestion.models import Chunk, MarkdownUnit, ParsedDocument
from app.retrieval.normalizer import normalize_persian

TOKEN = re.compile(r"[\w\u0600-\u06ff]+|[^\s]", re.UNICODE)


def approximate_token_count(value: str) -> int:
    word_tokens = len(TOKEN.findall(value))
    char_tokens = (len(value) + 3) // 4
    return max(1, word_tokens, char_tokens)


def _split_large_unit(
    unit: MarkdownUnit, max_tokens: int, token_counter: Callable[[str], int]
) -> list[MarkdownUnit]:
    if token_counter(unit.content) <= max_tokens or unit.kind == "code":
        return [unit]

    def unit_with_content(content: str) -> MarkdownUnit:
        return MarkdownUnit(
            heading_path=unit.heading_path,
            content=content.strip(),
            kind=unit.kind,
            code_language=unit.code_language,
        )

    def split_oversized_text(value: str) -> list[str]:
        parts: list[str] = []
        remaining = value.strip()
        while remaining:
            low = 1
            high = len(remaining)
            best = 0
            while low <= high:
                middle = (low + high) // 2
                if token_counter(remaining[:middle]) <= max_tokens:
                    best = middle
                    low = middle + 1
                else:
                    high = middle - 1
            if best == 0:
                raise ValueError("token counter cannot fit a single character")
            boundary = best
            whitespace = remaining.rfind(" ", max(0, best // 2), best)
            if whitespace > 0:
                boundary = whitespace
            part = remaining[:boundary].strip()
            if part:
                parts.append(part)
            remaining = remaining[boundary:].strip()
        return parts

    lines = unit.content.splitlines(keepends=True)
    split_units: list[MarkdownUnit] = []
    current_lines: list[str] = []
    for line in lines:
        candidate = "".join([*current_lines, line]).strip()
        if current_lines and token_counter(candidate) > max_tokens:
            text = "".join(current_lines).strip()
            if text:
                split_units.append(unit_with_content(text))
            current_lines = []

        if token_counter(line) > max_tokens:
            if current_lines:
                text = "".join(current_lines).strip()
                if text:
                    split_units.append(unit_with_content(text))
                current_lines = []
            split_units.extend(
                unit_with_content(part) for part in split_oversized_text(line)
            )
            continue
        current_lines.append(line)

    if current_lines:
        text = "".join(current_lines).strip()
        if text:
            split_units.append(unit_with_content(text))
    return split_units or [unit]


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
        flattened_units: list[MarkdownUnit] = []
        for unit in units:
            flattened_units.extend(
                _split_large_unit(unit, self.max_tokens, self.token_counter)
            )

        groups: list[list[MarkdownUnit]] = []
        current: list[MarkdownUnit] = []
        current_tokens = 0

        for unit in flattened_units:
            unit_tokens = self.token_counter(unit.content)
            if current and current_tokens + unit_tokens > self.max_tokens:
                groups.append(current)
                current = self._overlap(current)
                current_tokens = sum(
                    self.token_counter(item.content) for item in current
                )
                while current and current_tokens + unit_tokens > self.max_tokens:
                    removed = current.pop(0)
                    current_tokens -= self.token_counter(removed.content)
            current.append(unit)
            current_tokens += unit_tokens
        if current:
            groups.append(current)

        if len(groups) > 1 and self._group_tokens(groups[-1]) < self.min_tokens:
            candidate = groups[-2] + groups[-1]
            if self._group_tokens(candidate) <= self.max_tokens:
                groups[-2:] = [candidate]

        chunks: list[Chunk] = []
        content_occurrences: dict[str, int] = {}
        for ordinal, group in enumerate(groups):
            content = "\n\n".join(unit.content for unit in group).strip()
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            occurrence = content_occurrences.get(content_hash, 0)
            content_occurrences[content_hash] = occurrence + 1
            stable_key = f"{document.stable_id}:{content_hash}"
            if occurrence:
                stable_key = f"{stable_key}:{occurrence}"
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
                    stable_id=hashlib.sha256(stable_key.encode()).hexdigest()[:24],
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
