"""Single entrypoint for the Employee read path: classify → route → date-filter → hybrid
retrieve. Evidence evaluation/confidence/generation (Phase 4) consume this output."""
from datetime import date

from app.llm.provider_interface import LLMProvider
from app.models.schemas import IntentResult, RetrievedChunk
from app.retrieval import date_filter, hybrid_search, intent_router, subcorpus_router


def retrieve_evidence(
    question: str, provider: LLMProvider, override_date: date | None = None
) -> tuple[IntentResult, list[RetrievedChunk]]:
    intent = intent_router.classify(question, provider)
    if override_date is not None:
        # The Employee UI's explicit date field (PRD §38) takes precedence over LLM date detection.
        intent = IntentResult(category=intent.category, detected_date=override_date)
    categories = subcorpus_router.route(intent)
    version_ids = date_filter.eligible_version_ids(categories, intent.detected_date)
    chunks = hybrid_search.retrieve(question, version_ids)
    return intent, chunks
