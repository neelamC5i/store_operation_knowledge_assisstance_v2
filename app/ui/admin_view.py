"""Admin screens: upload, metadata review/approve, version history, KB dashboard
(FR-001–FR-018, FR-050)."""
import tempfile
from pathlib import Path

import streamlit as st

from app.core.logging import get_logger
from app.ingestion import pipeline
from app.ingestion.extraction import extract_text
from app.ingestion.metadata_extraction import propose_metadata
from app.ingestion.validation import validate_upload
from app.llm.provider_interface import get_provider
from app.storage import documents_repo
from app.storage.file_storage import save_original

logger = get_logger(__name__)

_CATEGORIES = ["Procedures", "Promotions", "Safety", "Unknown"]


def _process_upload(uploaded_file, title: str) -> None:
    suffix = Path(uploaded_file.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        temp_path = tmp.name

    validation = validate_upload(temp_path, uploaded_file.name)
    if not validation.ok:
        st.error(validation.error)
        Path(temp_path).unlink(missing_ok=True)
        return

    try:
        extracted = extract_text(temp_path, uploaded_file.name)
        if not extracted.full_text.strip():
            st.error("No extractable text was found in this file.")
            Path(temp_path).unlink(missing_ok=True)
            return

        draft = propose_metadata(extracted.full_text, uploaded_file.name, get_provider())
    except Exception:  # noqa: BLE001 — FR-050: a clear, non-technical message to the Admin
        logger.exception("Extraction/metadata proposal failed for %s", uploaded_file.name)
        st.error(
            "Something went wrong while reading this document or contacting the metadata "
            "service (check your GROQ_API_KEY/connection). The file was not added — please try again."
        )
        Path(temp_path).unlink(missing_ok=True)
        return

    st.session_state.pending_upload = {
        "temp_path": temp_path,
        "filename": uploaded_file.name,
        "title": title,
        "draft": draft,
    }


def _render_upload_form() -> None:
    st.subheader("Upload a Document")
    with st.form("upload_form"):
        title = st.text_input("Document Title (e.g. 'Return Policy')")
        uploaded_file = st.file_uploader("File", type=["pdf", "docx", "txt", "csv"])
        submitted = st.form_submit_button("Process Upload")
    if submitted:
        if not title.strip():
            st.error("Please provide a document title.")
        elif uploaded_file is None:
            st.error("Please choose a file.")
        else:
            _process_upload(uploaded_file, title.strip())
            st.rerun()


def _render_review_form() -> None:
    pending = st.session_state.pending_upload
    draft = pending["draft"]
    title = pending["title"]

    st.subheader("Review Extracted Metadata")
    st.caption(f"File: {pending['filename']}")

    if draft.prompt_injection_suspected:
        st.warning(
            "This document contains text resembling an instruction-override attempt "
            "(e.g. 'ignore previous instructions'). Review its content carefully before approving."
        )
    if draft.low_confidence:
        st.warning("One or more fields could not be confidently extracted — please verify them.")

    existing_doc = documents_repo.get_document_by_title(title)
    if existing_doc:
        active_version = documents_repo.get_active_version(existing_doc.id)
        if active_version:
            st.info(
                f"An active version of '{title}' already exists "
                f"(version {active_version.version}, effective {active_version.effective_from}). "
                "Approving this upload will supersede it."
            )

    with st.form("review_form"):
        category = st.selectbox(
            "Category", _CATEGORIES, index=_CATEGORIES.index(draft.category)
        )
        doc_type = st.text_input("Document Type", value=draft.doc_type)
        version = st.text_input("Version", value=draft.version)
        effective_from = st.date_input("Effective From", value=draft.effective_from)
        description = st.text_area("Description", value=draft.description)

        col1, col2 = st.columns(2)
        approve = col1.form_submit_button("Approve", type="primary")
        reject = col2.form_submit_button("Reject")

    if approve:
        document_id = existing_doc.id if existing_doc else documents_repo.create_document(title, category)
        version_id = documents_repo.create_pending_version(
            document_id=document_id,
            version=version,
            effective_from=effective_from,
            description=description,
            extracted_by=draft.extracted_by,
            prompt_injection_flag=draft.prompt_injection_suspected,
        )
        file_path = save_original(pending["temp_path"], version_id, pending["filename"])
        documents_repo.set_version_file_path(version_id, file_path)
        Path(pending["temp_path"]).unlink(missing_ok=True)
        del st.session_state.pending_upload

        with st.spinner("Chunking, embedding, and indexing…"):
            success, message = pipeline.process_pending_version(version_id)
        if success:
            st.success(f"'{title}' (version {version}) approved. {message}")
        else:
            st.error(f"'{title}' (version {version}) approved but indexing failed: {message}")
        st.rerun()

    if reject:
        Path(pending["temp_path"]).unlink(missing_ok=True)
        del st.session_state.pending_upload
        st.info("Upload discarded — not added to the knowledge base.")
        st.rerun()


def _render_kb_dashboard() -> None:
    st.subheader("Knowledge Base Health")
    stats = documents_repo.get_kb_stats()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Documents", stats["total_documents"])
    col2.metric("Active versions", stats["status_counts"].get("active", 0))
    col3.metric("Superseded versions", stats["status_counts"].get("superseded", 0))
    col4.metric("Failed/pending", stats["status_counts"].get("failed", 0) + stats["status_counts"].get("pending", 0))
    if stats["category_counts"]:
        st.caption(" · ".join(f"{cat}: {count}" for cat, count in stats["category_counts"].items()))


def _render_version_history() -> None:
    st.subheader("Document & Version History")
    documents = documents_repo.list_all_documents()
    if not documents:
        st.caption("No documents uploaded yet.")
        return
    for doc in documents:
        with st.expander(f"{doc.title} ({doc.category})"):
            for version in documents_repo.list_versions(doc.id):
                st.write(
                    f"**{version.version}** — status: `{version.status}` — "
                    f"effective {version.effective_from} to {version.effective_to or 'present'}"
                )


def render(username: str) -> None:
    st.header("Store Admin")
    st.caption(f"Signed in as {username}")

    _render_kb_dashboard()
    st.divider()

    if "pending_upload" in st.session_state:
        _render_review_form()
    else:
        _render_upload_form()

    st.divider()
    _render_version_history()
