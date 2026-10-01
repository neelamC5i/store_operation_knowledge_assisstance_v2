"""Tests for Phase 6: percentile/grading math in isolation, and a full run of the real
golden dataset against the real sample documents (LLM calls stubbed; retrieval/embedding
are real, exercising the same path a live Groq run would take)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evaluation"))
import run_evaluation  # noqa: E402

from app.models.schemas import AnswerResult, Citation, IntentResult  # noqa: E402
from app.storage import vector_store  # noqa: E402
from app.storage.sqlite_db import init_db  # noqa: E402
from scripts import seed_sample_documents  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_store_ops.db"
    monkeypatch.setattr("app.core.config.settings.sqlite_db_path", str(db_path))
    monkeypatch.setattr("app.core.config.settings.vector_index_path", str(tmp_path / "vector_index"))
    vector_store._client = vector_store.chromadb.PersistentClient(path=str(tmp_path / "vector_index"))
    init_db()
    yield


def test_percentile_basic_cases():
    assert run_evaluation._percentile([], 0.95) is None
    assert run_evaluation._percentile([5], 0.95) == 5
    assert run_evaluation._percentile([1, 2, 3, 4, 5], 0.5) == 3


def test_grade_answer_question_checks_title_and_version():
    question = {
        "id": "Q-TEST-1",
        "test_category": "A",
        "question": "What is the current return policy?",
        "expected_outcome": "answer",
        "expected_document_title": "Return Policy",
        "expected_version": "v2",
    }
    good_result = AnswerResult(
        is_refusal=False,
        citations=[Citation("Return Policy", "General", "v2", None, None, 0.9)],
        confidence=0.9,
    )
    wrong_version_result = AnswerResult(
        is_refusal=False,
        citations=[Citation("Return Policy", "General", "v1", None, None, 0.9)],
        confidence=0.9,
    )
    assert run_evaluation._grade(question, good_result, 0.1, 0.05)["correct"] is True
    assert run_evaluation._grade(question, wrong_version_result, 0.1, 0.05)["correct"] is False


def test_grade_refusal_question():
    question = {
        "id": "Q-TEST-2",
        "test_category": "F",
        "question": "What is the employee dress code?",
        "expected_outcome": "refusal",
    }
    refusal_result = AnswerResult(is_refusal=True, confidence=0.1)
    answer_result = AnswerResult(is_refusal=False, citations=[], confidence=0.9)
    assert run_evaluation._grade(question, refusal_result, 0.1, None)["correct"] is True
    assert run_evaluation._grade(question, answer_result, 0.1, 0.05)["correct"] is False


def test_grade_soft_categories_are_not_strictly_graded():
    question = {
        "id": "Q-TEST-3",
        "test_category": "G",
        "question": "What's the policy?",
        "expected_outcome": "refusal_or_clarify",
    }
    result = AnswerResult(is_refusal=False, citations=[], confidence=0.9)
    graded = run_evaluation._grade(question, result, 0.1, 0.05)
    assert graded["graded"] is False
    assert graded["correct"] is None


class KeywordStubProvider:
    """Maps question keywords to a category deterministically, without any network call."""

    def classify_intent(self, question: str) -> IntentResult:
        q = question.lower()
        if any(w in q for w in ("return", "exchange", "clearance", "inventory", "register", "drawer")):
            category = "Procedures"
        elif any(w in q for w in ("promotion", "coupon", "discount")):
            category = "Promotions"
        elif any(w in q for w in ("food", "glove", "compactor", "fire", "safety")):
            category = "Safety"
        else:
            category = "Unknown"
        return IntentResult(category=category, detected_date=None)

    def generate_answer(self, question: str, evidence):
        yield "Based on the retrieved evidence, here is the answer."


def test_full_golden_dataset_run_against_seeded_sample_documents():
    seed_sample_documents.seed()

    metrics = run_evaluation.run(
        golden_dataset_path=Path(__file__).resolve().parents[1] / "evaluation" / "golden_dataset.json",
        provider=KeywordStubProvider(),
    )

    assert metrics["total_questions"] == 18
    assert set(metrics["by_category"].keys()) == set("ABCDEFGHI")

    # Strict categories (A-F, H) should all resolve correctly with this KB + keyword router.
    strict_results = [r for r in metrics["results"] if r["graded"]]
    assert len(strict_results) > 0
    incorrect = [r for r in strict_results if not r["correct"]]
    assert incorrect == [], f"Unexpected grading failures: {incorrect}"

    assert metrics["overall"]["answer_accuracy"] == pytest.approx(1.0)
    assert metrics["overall"]["refusal_correctness"] == pytest.approx(1.0)
    assert metrics["overall"]["date_citation_accuracy"] == pytest.approx(1.0)
    assert metrics["overall"]["p95_latency_seconds"] is not None
    assert metrics["evaluation_run_id"] is not None
