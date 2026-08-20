import json
import re
from collections.abc import Sequence

from pydantic import ValidationError

from app.generation.models import GroundedAnswer, ValidatedAnswer
from app.retrieval.models import RetrievedChunk

MARKDOWN_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)
URL = re.compile(r"https?://\S+", re.IGNORECASE)


class GroundingValidationError(ValueError):
    pass


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
    unique_citations = list(dict.fromkeys(cited))
    if not unique_citations:
        raise GroundingValidationError("answer has no validated citations")
    suggestions = [item.strip() for item in answer.suggestions if item.strip()][:4]
    return ValidatedAnswer(
        answer_markdown=answer.answer_markdown.strip(),
        source_ids=unique_citations,
        suggestions=suggestions,
    )
