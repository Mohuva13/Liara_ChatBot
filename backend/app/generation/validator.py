import json
import re
from collections.abc import Sequence

from pydantic import ValidationError

from app.generation.models import GroundedAnswer, ValidatedAnswer
from app.retrieval.models import RetrievedChunk
from app.retrieval.normalizer import normalize_persian

MARKDOWN_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)
URL = re.compile(r"https?://\S+", re.IGNORECASE)
ABSTENTION_MARKERS = (
    "در evidence ارائه شده",
    "در evidence",
    "شاهد کافی",
    "اطلاعات کافی",
    "منبع کافی",
    "منابع کافی",
    "هیچ توضیحی درباره",
    "از روی این منابع",
    "پاسخ قابل اعتماد کافی",
)


class GroundingValidationError(ValueError):
    pass


class ModelAbstainedError(GroundingValidationError):
    """Raised when the model disguises a no-answer as a grounded answer."""


def _is_model_abstention(text: str) -> bool:
    normalized = normalize_persian(text).replace("ٔ", "")
    return any(marker in normalized for marker in ABSTENTION_MARKERS)


def validate_grounded_answer(
    raw: str, evidence: Sequence[RetrievedChunk]
) -> ValidatedAnswer:
    cleaned = MARKDOWN_FENCE.sub("", raw.strip()).strip()
    try:
        answer = GroundedAnswer.model_validate(json.loads(cleaned))
    except (json.JSONDecodeError, ValidationError) as error:
        raise GroundingValidationError("invalid structured answer") from error

    allowed = {chunk.chunk_id for chunk in evidence}
    cited: list[str] = []
    for claim in answer.claims:
        unknown = set(claim.source_ids) - allowed
        if unknown:
            raise GroundingValidationError("answer cites unknown evidence")
        cited.extend(claim.source_ids)
    if URL.search(answer.answer_markdown):
        raise GroundingValidationError("model-authored URLs are not allowed")
    if _is_model_abstention(answer.answer_markdown):
        raise ModelAbstainedError("model reported insufficient evidence")
    unique_citations = list(dict.fromkeys(cited))
    if not unique_citations:
        raise GroundingValidationError("answer has no validated citations")
    suggestions = list(
        dict.fromkeys(item.strip() for item in answer.suggestions if item.strip())
    )[:3]
    return ValidatedAnswer(
        answer_markdown=answer.answer_markdown.strip(),
        source_ids=unique_citations,
        suggestions=suggestions,
    )
