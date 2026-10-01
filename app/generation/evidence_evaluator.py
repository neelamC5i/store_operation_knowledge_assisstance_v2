"""Evaluates retrieved chunks for relevance and coverage, and feeds the confidence
calculation (FR-036–FR-039)."""
import re

from app.core.config import settings
from app.generation.confidence import compute_confidence
from app.models.schemas import EvidenceEvaluation, RetrievedChunk

_STOPWORDS = {
    "the", "a", "an", "is", "are", "what", "how", "when", "where", "who", "does", "do",
    "to", "of", "in", "on", "for", "and", "or", "i", "my", "can", "will", "was", "it",
    "this", "that", "be", "as", "at", "by", "with", "about",
}


def _tokenize(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOPWORDS}


def _evaluate_relevance(chunks: list[RetrievedChunk]) -> float:
    if not chunks:
        return 0.0
    top = chunks[: min(3, len(chunks))]
    return sum(c.relevance_score for c in top) / len(top)


def _stem(word: str) -> str:
    for suffix in ("ies", "es", "ed", "ing", "s"):
        if len(word) > len(suffix) + 2 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def _evaluate_coverage(question: str, chunks: list[RetrievedChunk]) -> float:
    question_terms = _tokenize(question)
    if not question_terms:
        return 1.0
    if not chunks:
        return 0.0
    # Section headings and the document's own title carry key nouns that aren't part of
    # chunk_text (see chunking.py/extraction.py — a title heading immediately followed by
    # a sub-heading never accrues body text, so e.g. "Return Policy" itself never appears
    # in any chunk). A question naming the document by its title is legitimately covered.
    combined = " ".join(
        f"{c.chunk_text} {c.section or ''} {c.document_title}" for c in chunks
    )
    doc_stems = {_stem(w) for w in _tokenize(combined)}
    covered = {t for t in question_terms if _stem(t) in doc_stems}
    return len(covered) / len(question_terms)


def _evaluate_source_consistency(chunks: list[RetrievedChunk]) -> float:
    if not chunks:
        return 0.0
    titles = [c.document_title for c in chunks]
    most_common_count = max(titles.count(t) for t in set(titles))
    return most_common_count / len(titles)


def evaluate(question: str, chunks: list[RetrievedChunk]) -> EvidenceEvaluation:
    relevance = _evaluate_relevance(chunks)
    coverage = _evaluate_coverage(question, chunks)
    date_validity = bool(chunks)  # retrieval already scoped to date-eligible versions
    source_consistency = _evaluate_source_consistency(chunks)

    confidence = compute_confidence(relevance, coverage, date_validity, source_consistency)
    sufficient = bool(chunks) and confidence >= settings.confidence_threshold

    return EvidenceEvaluation(
        relevance=relevance,
        coverage=coverage,
        date_validity=date_validity,
        source_consistency=source_consistency,
        confidence=confidence,
        sufficient=sufficient,
    )
