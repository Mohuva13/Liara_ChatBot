import hashlib
import re
from pathlib import Path
from urllib.parse import urlparse

from app.ingestion.models import MarkdownUnit, ParsedDocument

ORIGINAL_LINK = re.compile(r"^Original link:\s*(https://\S+)\s*$", re.IGNORECASE)
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
FENCE = re.compile(r"^\s*(?:[-*+]\s+)?(```+|~~~+)\s*([^\s`]*)?.*$")
ALL_LINKS_HEADING = re.compile(r"^##\s+all links\s*$", re.IGNORECASE)


class DocumentParseError(ValueError):
    pass


class DocumentSkipError(ValueError):
    pass


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def parse_document(path: Path, docs_root: Path) -> ParsedDocument:
    raw = path.read_text(encoding="utf-8-sig")
    lines = raw.splitlines()
    if not lines:
        raise DocumentParseError("empty document")

    match = ORIGINAL_LINK.match(lines[0].strip())
    if match is None:
        raise DocumentParseError("missing canonical Original link")
    canonical_url = match.group(1)
    parsed_url = urlparse(canonical_url)
    if parsed_url.scheme != "https" or parsed_url.hostname != "docs.liara.ir":
        raise DocumentParseError("canonical URL is outside the Liara docs allowlist")

    title = next(
        (
            heading.group(2).strip()
            for line in lines[1:]
            if (heading := HEADING.match(line)) and len(heading.group(1)) == 1
        ),
        None,
    )
    if title is None:
        raise DocumentSkipError("missing level-one title")

    content_lines = lines[1:]
    for index, line in enumerate(content_lines):
        if ALL_LINKS_HEADING.match(line.strip()):
            content_lines = content_lines[:index]
            break
    content = "\n".join(content_lines).strip()
    if not content:
        raise DocumentParseError("document has no indexable content")

    source_path = path.relative_to(docs_root).as_posix()
    stable_id = _hash(source_path)[:24]
    return ParsedDocument(
        stable_id=stable_id,
        source_path=source_path,
        canonical_url=canonical_url,
        title=title,
        content=content,
        content_hash=_hash(content),
    )


def parse_units(content: str) -> list[MarkdownUnit]:
    heading_stack: list[str] = []
    units: list[MarkdownUnit] = []
    buffer: list[str] = []
    in_fence = False
    fence_marker = ""
    fence_language: str | None = None

    def flush(kind: str = "text", code_language: str | None = None) -> None:
        text = "\n".join(buffer).strip()
        buffer.clear()
        if text:
            units.append(
                MarkdownUnit(
                    heading_path=tuple(heading_stack),
                    content=text,
                    kind=kind,
                    code_language=code_language,
                )
            )

    lines = content.splitlines()
    for index, line in enumerate(lines):
        fence = FENCE.match(line)
        if fence:
            marker = fence.group(1)
            if not in_fence:
                language = (fence.group(2) or "").strip() or None
                if language is None and not any(
                    remaining.strip() for remaining in lines[index + 1 :]
                ):
                    continue
                flush()
                in_fence = True
                fence_marker = marker[0]
                fence_language = language
                buffer.append(line)
                continue
            buffer.append(line)
            if marker.startswith(fence_marker):
                flush("code", fence_language)
                in_fence = False
                fence_marker = ""
                fence_language = None
            continue

        if in_fence:
            buffer.append(line)
            continue

        heading = HEADING.match(line)
        if heading:
            flush()
            level = len(heading.group(1))
            title = heading.group(2).strip()
            heading_stack[level - 1 :] = [title]
            buffer.append(line)
            flush("heading")
            continue

        if not line.strip():
            flush()
            continue
        buffer.append(line)

    if in_fence:
        buffer.append(fence_marker * 3)
        flush("code", fence_language)
    flush()
    return units
