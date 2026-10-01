"""Classifies a question's category and detects an explicit date reference (FR-027, FR-028)."""
from app.llm.provider_interface import LLMProvider
from app.models.schemas import IntentResult


def classify(question: str, provider: LLMProvider) -> IntentResult:
    return provider.classify_intent(question)
