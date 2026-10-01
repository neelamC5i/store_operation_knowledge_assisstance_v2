"""Ties retrieval, evidence evaluation, and the answer/refuse decision gate together
(FR-040–FR-044). This is the single entrypoint the Employee chat UI calls (Phase 5)."""
from datetime import date

from app.generation.evidence_evaluator import evaluate
from app.generation.refusal import build_refusal
from app.llm.provider_interface import LLMProvider
from app.models.schemas import AnswerResult, Citation, RetrievedChunk
from app.retrieval.orchestrator import retrieve_evidence


def _build_citations(chunks: list[RetrievedChunk]) -> list[Citation]:
    seen = set()
    citations = []
    for c in chunks:
        key = (c.document_title, c.version)
        if key in seen:
            continue
        seen.add(key)
        citations.append(
            Citation(
                document_title=c.document_title,
                section=c.section,
                version=c.version,
                effective_from=c.effective_from,
                effective_to=c.effective_to,
                confidence=c.relevance_score,
            )
        )
    return citations


def generate(question: str, provider: LLMProvider, override_date: date | None = None) -> AnswerResult:
    intent, chunks = retrieve_evidence(question, provider, override_date)
    evaluation = evaluate(question, chunks)

    if not evaluation.sufficient:
        return build_refusal(question, intent, evaluation)

    citations = _build_citations(chunks)
    stream = provider.generate_answer(question, chunks)
    return AnswerResult(
        is_refusal=False,
        text_stream=stream,
        citations=citations,
        confidence=evaluation.confidence,
    )
