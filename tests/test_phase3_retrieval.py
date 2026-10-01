"""Smoke tests for Phase 3: sub-corpus routing, effective-date eligibility, and hybrid
retrieval (real embeddings — small texts keep this fast; no network LLM calls needed)."""
from datetime import date

import pytest

from app.ingestion import pipeline
from app.models.schemas import IntentResult
from app.retrieval import date_filter, hybrid_search, orchestrator, subcorpus_router
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


def _ingest(tmp_path, title, category, version, effective_from, text, filename):
    path = tmp_path / filename
    path.write_text(text, encoding="utf-8")
    existing = documents_repo.get_document_by_title(title)
    doc_id = existing.id if existing else documents_repo.create_document(title, category)
    version_id = documents_repo.create_pending_version(
        document_id=doc_id,
        version=version,
        effective_from=effective_from,
        description="test",
        extracted_by="rule+llm",
        prompt_injection_flag=False,
    )
    documents_repo.set_version_file_path(version_id, str(path))
    success, message = pipeline.process_pending_version(version_id)
    assert success, message
    return doc_id, version_id


def test_subcorpus_router():
    assert subcorpus_router.route(IntentResult(category="Safety")) == ["Safety"]
    assert set(subcorpus_router.route(IntentResult(category="Unknown"))) == set(
        subcorpus_router.ALL_CATEGORIES
    )


def test_eligible_version_ids_excludes_superseded_for_current(tmp_path):
    doc_id, v1_id = _ingest(
        tmp_path, "Return Policy", "Procedures", "v1", date(2024, 1, 1),
        "Return Policy\nItems may be returned within 14 days.", "rp_v1.txt",
    )
    _doc_id2, v2_id = _ingest(
        tmp_path, "Return Policy", "Procedures", "v2", date(2024, 6, 1),
        "Return Policy\nItems may be returned within 30 days.", "rp_v2.txt",
    )

    current_ids = date_filter.eligible_version_ids(["Procedures"], None)
    assert v2_id in current_ids
    assert v1_id not in current_ids

    historical_ids = date_filter.eligible_version_ids(["Procedures"], date(2024, 3, 1))
    assert v1_id in historical_ids
    assert v2_id not in historical_ids


def test_hybrid_search_scopes_to_eligible_versions_and_category(tmp_path):
    _ingest(
        tmp_path, "Return Policy", "Procedures", "v1", date(2024, 1, 1),
        "Return Policy\nCustomers may return unopened items within 30 days with a receipt.",
        "rp.txt",
    )
    _ingest(
        tmp_path, "Summer Promotion", "Promotions", "v1", date(2024, 1, 1),
        "Summer Promotion\nBuy one get one free on all beverages during July.",
        "promo.txt",
    )

    procedures_ids = date_filter.eligible_version_ids(["Procedures"], None)
    results = hybrid_search.retrieve("How many days do I have to return an item?", procedures_ids)

    assert len(results) >= 1
    assert all(r.document_title == "Return Policy" for r in results)
    assert results[0].relevance_score > 0


def test_orchestrator_combines_routing_and_retrieval(tmp_path):
    _ingest(
        tmp_path, "Food Safety Rules", "Safety", "v1", date(2024, 1, 1),
        "Food Safety Rules\nAlways wear gloves when handling raw meat.",
        "safety.txt",
    )

    class StubProvider:
        def classify_intent(self, question):
            return IntentResult(category="Safety", detected_date=None)

    intent, chunks = orchestrator.retrieve_evidence("What gloves rule applies?", StubProvider())
    assert intent.category == "Safety"
    assert len(chunks) >= 1
    assert chunks[0].document_title == "Food Safety Rules"
