"""Abstract LLM provider — Groq and Ollama both implement this so the rest of the app
never branches on provider (PG-04, NFR-003)."""
from abc import ABC, abstractmethod
from typing import Iterator

from app.models.schemas import IntentResult, MetadataDraft, RetrievedChunk


class LLMProvider(ABC):
    @abstractmethod
    def classify_intent(self, question: str) -> IntentResult: ...

    @abstractmethod
    def extract_metadata(self, text: str, filename: str) -> MetadataDraft: ...

    @abstractmethod
    def generate_answer(self, question: str, evidence: list[RetrievedChunk]) -> Iterator[str]: ...


def get_provider() -> "LLMProvider":
    """Selects Groq or Ollama based on LLM_PROVIDER — the only place that branches on provider."""
    from app.core.config import settings

    if settings.llm_provider == "ollama":
        from app.llm.ollama_provider import OllamaProvider

        return OllamaProvider()
    from app.llm.groq_provider import GroqProvider

    return GroqProvider()
