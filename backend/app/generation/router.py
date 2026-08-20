from dataclasses import dataclass

from app.policies.scope import Intent
from app.retrieval.models import EvidenceDecision


@dataclass(frozen=True, slots=True)
class ModelRoute:
    tier: str
    model: str
    reason: str
    max_output_tokens: int


def select_model_route(
    query: str,
    intent: Intent,
    evidence: EvidenceDecision,
    *,
    small_model: str,
    large_model: str,
    small_max_tokens: int,
    large_max_tokens: int,
) -> ModelRoute:
    complex_intent = intent in {Intent.TROUBLESHOOT, Intent.COMPARE}
    multi_document = len({chunk.document_id for chunk in evidence.chunks}) > 2
    long_query = len(query) > 600
    if complex_intent or multi_document or long_query or evidence.contradictory:
        return ModelRoute("large", large_model, "complex_grounded", large_max_tokens)
    return ModelRoute("small", small_model, "simple_grounded", small_max_tokens)
