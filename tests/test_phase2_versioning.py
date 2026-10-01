"""Smoke tests for Phase 2: chunking, supersede/activate logic, and the full ingestion
pipeline with a stubbed embedding model (no model download required for these tests)."""
from datetime import date

import pytest

from app.ingestion import chunking, pipeline
from app.ingestion.extraction import ExtractedDocument, Section
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


def test_chunk_sections_splits_long_text():
    extracted = ExtractedDocument(
        sections=[
            Section(
                label="Returns",
                page=1,
                text="Sentence one is short. " * 40,
            )
        ]
    )
    chunks = chunking.chunk_sections(extracted, max_chars=200)
    assert len(chunks) > 1
    assert all(c.section == "Returns" for c in chunks)
    assert all(len(c.chunk_text) <= 260 for c in chunks)  # allows one trailing sentence overflow


def test_activate_version_supersedes_prior_active(tmp_path):
    doc_id = documents_repo.create_document("Return Policy", "Procedures")

    v1_id = documents_repo.create_pending_version(
        document_id=doc_id,
        version="v1",
        effective_from=date(2024, 1, 1),
        description="v1",
        extracted_by="rule+llm",
        prompt_injection_flag=False,
    )
    documents_repo.activate_version(doc_id, v1_id, "2024-01-01")

    v1 = documents_repo.get_version(v1_id)
    assert v1.status == "active"
    assert documents_repo.get_document(doc_id).current_version_id == v1_id

    v2_id = documents_repo.create_pending_version(
        document_id=doc_id,
        version="v2",
        effective_from=date(2024, 6, 1),
        description="v2",
        extracted_by="rule+llm",
        prompt_injection_flag=False,
    )
    documents_repo.activate_version(doc_id, v2_id, "2024-06-01")

    v1_after = documents_repo.get_version(v1_id)
    v2_after = documents_repo.get_version(v2_id)
    assert v1_after.status == "superseded"
    assert v1_after.effective_to == "2024-05-31"
    assert v2_after.status == "active"
    assert documents_repo.get_document(doc_id).current_version_id == v2_id


def test_pipeline_activates_version_and_indexes_chunks(tmp_path, monkeypatch):
    def fake_embed_texts(texts):
        return [[0.1, 0.2, 0.3] for _ in texts]

    monkeypatch.setattr("app.ingestion.embedding.embed_texts", fake_embed_texts)

    sample_path = tmp_path / "return_policy_v1.txt"
    sample_path.write_text(
        "Return Policy\nCustomers may return items within 30 days of purchase with a receipt.",
        encoding="utf-8",
    )

    doc_id = documents_repo.create_document("Return Policy", "Procedures")
    version_id = documents_repo.create_pending_version(
        document_id=doc_id,
        version="v1",
        effective_from=date(2024, 1, 1),
        description="Initial version",
        extracted_by="rule+llm",
        prompt_injection_flag=False,
    )
    documents_repo.set_version_file_path(version_id, str(sample_path))

    success, message = pipeline.process_pending_version(version_id)
    assert success, message

    version = documents_repo.get_version(version_id)
    assert version.status == "active"

    chunks = documents_repo.list_chunks(version_id)
    assert len(chunks) >= 1
    assert all(c.embedding_ref for c in chunks)

    results = vector_store.query(query_embedding=[0.1, 0.2, 0.3], top_k=5)
    assert len(results["ids"][0]) == len(chunks)


def test_pipeline_marks_failed_on_embedding_error(tmp_path, monkeypatch):
    def broken_embed_texts(texts):
        raise RuntimeError("embedding service unavailable")

    monkeypatch.setattr("app.ingestion.embedding.embed_texts", broken_embed_texts)

    sample_path = tmp_path / "safety_rules_v1.txt"
    sample_path.write_text("Safety Rules\nAlways wear gloves when handling raw food.", encoding="utf-8")

    doc_id = documents_repo.create_document("Safety Rules", "Safety")
    version_id = documents_repo.create_pending_version(
        document_id=doc_id,
        version="v1",
        effective_from=date(2024, 1, 1),
        description="Initial version",
        extracted_by="rule+llm",
        prompt_injection_flag=False,
    )
    documents_repo.set_version_file_path(version_id, str(sample_path))

    success, message = pipeline.process_pending_version(version_id)
    assert not success

    version = documents_repo.get_version(version_id)
    assert version.status == "failed"
    assert documents_repo.list_chunks(version_id) == []
