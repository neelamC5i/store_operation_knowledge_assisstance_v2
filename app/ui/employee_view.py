"""Employee chat screen: question input (optional date), streamed answer, citations,
confidence, feedback, session-scoped conversation history (FR-045–FR-049, PRD §38)."""
import json
import uuid
from dataclasses import asdict
from datetime import date

import streamlit as st

from app.core.logging import get_logger
from app.generation.response_generator import generate
from app.llm.provider_interface import get_provider
from app.storage import conversation_repo

logger = get_logger(__name__)


def _citation_to_dict(citation) -> dict:
    d = asdict(citation)
    d["effective_from"] = citation.effective_from.isoformat() if citation.effective_from else None
    d["effective_to"] = citation.effective_to.isoformat() if citation.effective_to else None
    return d


def _render_citations(msg: dict) -> None:
    if msg.get("is_refusal") or not msg.get("citations"):
        return
    st.caption(f"Confidence: {msg['confidence']:.2f}")
    for c in msg["citations"]:
        effective = c["effective_from"] or "unknown"
        st.caption(
            f"📄 {c['document_title']} — {c['section'] or 'General'} — "
            f"version {c['version']} — effective {effective}"
        )


def _render_feedback(msg: dict) -> None:
    if msg.get("is_refusal") or msg.get("message_id") is None:
        return
    message_id = msg["message_id"]
    col1, col2 = st.columns(2)
    if col1.button("👍 Helpful", key=f"helpful_{message_id}"):
        conversation_repo.add_feedback(message_id, helpful=True)
        st.toast("Thanks for the feedback!")
    if col2.button("👎 Not helpful", key=f"unhelpful_{message_id}"):
        conversation_repo.add_feedback(message_id, helpful=False)
        st.toast("Thanks for the feedback!")


def render(username: str) -> None:
    st.header("Store Operations Assistant")
    st.caption(f"Signed in as {username}")

    if "employee_session_id" not in st.session_state:
        st.session_state.employee_session_id = f"{username}-{uuid.uuid4()}"
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = conversation_repo.get_or_create_conversation(
            st.session_state.employee_session_id
        )
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.write(msg["text"])
            if msg["role"] == "assistant":
                _render_citations(msg)
                _render_feedback(msg)

    with st.expander("Ask about a specific past date (optional)"):
        use_date = st.checkbox("Specify a date", key="use_as_of_date")
        as_of_date = st.date_input("As of date", value=date.today()) if use_date else None

    question = st.chat_input("Ask a question about store procedures, promotions, or safety…")
    if not question:
        return

    conversation_repo.add_message(st.session_state.conversation_id, "user", question, None, None, False)
    st.session_state.chat_messages.append({"role": "user", "text": question})
    with st.chat_message("user"):
        st.write(question)

    provider = get_provider()
    with st.chat_message("assistant"):
        try:
            result = generate(question, provider, override_date=as_of_date)
            if result.is_refusal:
                full_text = result.refusal_reason
                st.write(full_text)
                citations_json = None
            else:
                full_text = st.write_stream(result.text_stream)
                citations_json = json.dumps([_citation_to_dict(c) for c in result.citations])
        except Exception:  # noqa: BLE001 — FR-050/FR-051: a clear message, not a raw traceback
            logger.exception("Answer generation failed for question: %r", question)
            full_text = (
                "Sorry, I couldn't reach the answer service just now (check the configured "
                "LLM provider/connection). Please try again in a moment."
            )
            st.error(full_text)
            result = None
            citations_json = None

        confidence = result.confidence if result is not None else None
        is_refusal = result.is_refusal if result is not None else True
        citations = [_citation_to_dict(c) for c in result.citations] if result is not None else []

        message_id = conversation_repo.add_message(
            st.session_state.conversation_id,
            "assistant",
            full_text,
            citations_json,
            confidence,
            is_refusal,
        )
        msg = {
            "role": "assistant",
            "text": full_text,
            "citations": citations,
            "confidence": confidence,
            "is_refusal": is_refusal,
            "message_id": message_id,
        }
        _render_citations(msg)
        _render_feedback(msg)
        st.session_state.chat_messages.append(msg)
