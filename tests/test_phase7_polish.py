"""Smoke tests for Phase 7: KB dashboard stats."""
from datetime import date

import pytest

from app.storage import documents_repo
from app.storage.sqlite_db import init_db


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_store_ops.db"
    monkeypatch.setattr("app.core.config.settings.sqlite_db_path", str(db_path))
    init_db()
    yield


def test_kb_stats_empty_kb():
    stats = documents_repo.get_kb_stats()
    assert stats["total_documents"] == 0
    assert stats["status_counts"] == {}
    assert stats["category_counts"] == {}


def test_kb_stats_counts_active_and_superseded():
    doc_id = documents_repo.create_document("Return Policy", "Procedures")
    v1_id = documents_repo.create_pending_version(
        document_id=doc_id, version="v1", effective_from=date(2024, 1, 1),
        description="v1", extracted_by="rule+llm", prompt_injection_flag=False,
    )
    documents_repo.activate_version(doc_id, v1_id, "2024-01-01")

    v2_id = documents_repo.create_pending_version(
        document_id=doc_id, version="v2", effective_from=date(2024, 6, 1),
        description="v2", extracted_by="rule+llm", prompt_injection_flag=False,
    )
    documents_repo.activate_version(doc_id, v2_id, "2024-06-01")

    documents_repo.create_document("Safety Rules", "Safety")

    stats = documents_repo.get_kb_stats()
    assert stats["total_documents"] == 2
    assert stats["status_counts"]["active"] == 1
    assert stats["status_counts"]["superseded"] == 1
    assert stats["category_counts"]["Procedures"] == 1
    assert stats["category_counts"]["Safety"] == 1
