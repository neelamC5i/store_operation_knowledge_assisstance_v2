"""Refusal message + logging when evidence is insufficient (FR-043, FR-044, BRULE-04)."""
from app.core.logging import get_logger
from app.models.schemas import AnswerResult, EvidenceEvaluation, IntentResult

logger = get_logger(__name__)

REFUSAL_MESSAGE = (
    "I don't have enough verified evidence in the knowledge base to answer that confidently. "
    "Please check with your supervisor for the current guidance."
)


def build_refusal(question: str, intent: IntentResult, evaluation: EvidenceEvaluation) -> AnswerResult:
    logger.info(
        "REFUSAL | question=%r category=%s confidence=%.2f relevance=%.2f coverage=%.2f",
        question,
        intent.category,
        evaluation.confidence,
        evaluation.relevance,
        evaluation.coverage,
    )
    return AnswerResult(
        is_refusal=True,
        confidence=evaluation.confidence,
        refusal_reason=REFUSAL_MESSAGE,
    )
