"""Smoke tests for Phase 4: evidence evaluation/confidence, citation assembly, and the
answer/refuse decision gate (real embeddings/retrieval; LLM calls stubbed)."""
from datetime import date

import pytest

from app.generation import response_generator
from app.generation.confidence import compute_confidence
from app.generation.evidence_evaluator import evaluate
from app.ingestion import pipeline
from app.models.schemas import IntentResult, RetrievedChunk
from app.storage import documents_repo, vector_store
from app.storage.sqlite_db import init_db


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_store_ops.db"
    monkeypatch.setattr("app.core.config.settings.sqlite_db_path", str(db_path))
    monkeypatch.setattr("app.core.config.settings.vector_index_path", str(tmp_path / "vector_index"))
    vector_store._client = vector_store.chromadb.PersistentClient(path=str(tmp_path / "vector_index"))
    init_db()
    yield


class StubProvider:
    def __init__(self, category="Procedures", detected_date=None, answer_tokens=None):
        self._category = category
        self._detected_date = detected_date
        self._answer_tokens = answer_tokens or ["Yes", ", ", "30 days", "."]

    def classify_intent(self, question):
        return IntentResult(category=self._category, detected_date=self._detected_date)

    def generate_answer(self, question, evidence):
        yield from self._answer_tokens


def test_compute_confidence_weights_sum_to_one_and_respond_to_inputs():
    assert compute_confidence(1.0, 1.0, True, 1.0) == pytest.approx(1.0)
    assert compute_confidence(0.0, 0.0, False, 0.0) == 0.0
    with_date = compute_confidence(0.5, 0.5, True, 0.5)
    without_date = compute_confidence(0.5, 0.5, False, 0.5)
    assert with_date > without_date


def test_evaluate_returns_zero_confidence_for_no_evidence():
    result = evaluate("What is the return policy?", [])
    assert result.confidence == 0.0
    assert not result.sufficient
    assert not result.date_validity


def test_evaluate_sufficient_for_strong_matching_chunk():
    chunk = RetrievedChunk(
        chunk_id=1,
        document_version_id=1,
        document_title="Return Policy",
        section="General",
        version="v1",
        effective_from=date(2024, 1, 1),
        effective_to=None,
        chunk_text="Customers may return unopened items within 30 days of purchase with a receipt.",
        relevance_score=1.0,
    )
    result = evaluate("How many days do I have to return an item?", [chunk])
    assert result.sufficient
    assert result.confidence > 0.6


def test_evaluate_coverage_counts_heading_only_terms_and_plural_variants():
    # "beverage" only appears in the section heading (not chunk_text — see chunking.py,
    # which never puts the heading line inside the chunk body), and the question says
    # "beverages" (plural) against body text "beverage" (singular) — both must still count.
    chunk = RetrievedChunk(
        chunk_id=1,
        document_version_id=1,
        document_title="Store Promotions",
        section="Summer Beverage Promotion",
        version="v1",
        effective_from=date(2024, 1, 1),
        effective_to=None,
        chunk_text="Buy one get one free on all cold beverage every Friday through Sunday.",
        relevance_score=0.8,
    )
    result = evaluate("What is the current beverage promotion?", [chunk])
    assert result.coverage > 0.5


def test_response_generator_refuses_when_knowledge_base_is_empty():
    result = response_generator.generate("What is the return policy?", StubProvider())
    assert result.is_refusal
    assert result.refusal_reason
    assert result.citations == []


def test_response_generator_answers_with_citations_when_evidence_is_sufficient(tmp_path):
    sample_path = tmp_path / "return_policy.txt"
    sample_path.write_text(
        "Return Policy\nCustomers may return unopened items within 30 days of purchase with a receipt.",
        encoding="utf-8",
    )
    doc_id = documents_repo.create_document("Return Policy", "Procedures")
    version_id = documents_repo.create_pending_version(
        document_id=doc_id,
        version="v1",
        effective_from=date(2024, 1, 1),
        description="test",
        extracted_by="rule+llm",
        prompt_injection_flag=False,
    )
    documents_repo.set_version_file_path(version_id, str(sample_path))
    success, message = pipeline.process_pending_version(version_id)
    assert success, message

    result = response_generator.generate(
        "How many days do I have to return an item?", StubProvider(category="Procedures")
    )

    assert not result.is_refusal
    assert result.confidence > 0.6
    assert len(result.citations) >= 1
    assert result.citations[0].document_title == "Return Policy"
    assert "".join(result.text_stream) == "Yes, 30 days."
