"""Smoke tests for Phase 5: conversation/feedback persistence and the UI's date-override
path through the retrieval orchestrator."""
from datetime import date

import pytest

from app.ingestion import pipeline
from app.models.schemas import IntentResult
from app.retrieval import orchestrator
from app.storage import conversation_repo, documents_repo, vector_store
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
    def classify_intent(self, question):
        return IntentResult(category="Procedures", detected_date=None)


def test_get_or_create_conversation_is_stable_per_session():
    first = conversation_repo.get_or_create_conversation("session-123")
    second = conversation_repo.get_or_create_conversation("session-123")
    other = conversation_repo.get_or_create_conversation("session-456")
    assert first == second
    assert other != first


def test_message_and_feedback_roundtrip():
    conversation_id = conversation_repo.get_or_create_conversation("session-abc")
    user_msg_id = conversation_repo.add_message(conversation_id, "user", "What is the return policy?", None, None, False)
    assistant_msg_id = conversation_repo.add_message(
        conversation_id, "assistant", "Items may be returned within 30 days.", '[{"document_title": "Return Policy"}]', 0.85, False
    )
    conversation_repo.add_feedback(assistant_msg_id, helpful=True)

    messages = conversation_repo.list_messages(conversation_id)
    assert len(messages) == 2
    assert messages[0]["id"] == user_msg_id
    assert messages[1]["id"] == assistant_msg_id
    assert messages[1]["confidence"] == 0.85


def test_orchestrator_override_date_selects_historical_version(tmp_path):
    def ingest(version, effective_from, text, filename):
        path = tmp_path / filename
        path.write_text(text, encoding="utf-8")
        existing = documents_repo.get_document_by_title("Return Policy")
        doc_id = existing.id if existing else documents_repo.create_document("Return Policy", "Procedures")
        version_id = documents_repo.create_pending_version(
            document_id=doc_id, version=version, effective_from=effective_from,
            description="test", extracted_by="rule+llm", prompt_injection_flag=False,
        )
        documents_repo.set_version_file_path(version_id, str(path))
        success, message = pipeline.process_pending_version(version_id)
        assert success, message
        return version_id

    v1_id = ingest("v1", date(2024, 1, 1), "Return Policy\nItems may be returned within 14 days.", "v1.txt")
    v2_id = ingest("v2", date(2024, 6, 1), "Return Policy\nItems may be returned within 30 days.", "v2.txt")

    # No override: should resolve to the current (v2) version.
    _intent, current_chunks = orchestrator.retrieve_evidence(
        "How many days can I return an item?", StubProvider()
    )
    assert all(c.document_version_id == v2_id for c in current_chunks)

    # Override with a date inside v1's effective range: should resolve to v1, not v2.
    _intent, historical_chunks = orchestrator.retrieve_evidence(
        "How many days can I return an item?", StubProvider(), override_date=date(2024, 3, 1)
    )
    assert all(c.document_version_id == v1_id for c in historical_chunks)
