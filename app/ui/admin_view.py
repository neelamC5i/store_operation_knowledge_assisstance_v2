"""Admin dashboard UI. Dashboard/Documents/Knowledge Base screens are wired to the real
ingestion pipeline (FR-001–FR-018, FR-050) — upload → review/approve → chunk → embed →
index → activate — so uploaded documents actually become retrievable. Only the
Document Activity sparkline on the dashboard remains illustrative dummy data, since
there's no historical activity log to source it from."""
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from app.core.logging import get_logger
from app.ingestion import pipeline
from app.ingestion.extraction import extract_text
from app.ingestion.metadata_extraction import propose_metadata
from app.ingestion.validation import validate_upload
from app.llm.provider_interface import get_provider
from app.storage import documents_repo
from app.storage.file_storage import save_original
from app.ui.layout import NavItem, render_footer, render_header, render_sidebar

logger = get_logger(__name__)

_NAV_ITEMS = [
    NavItem("Dashboard", ":material/dashboard:"),
    NavItem("Documents", ":material/description:"),
    NavItem("Knowledge Base", ":material/menu_book:"),
    NavItem("Users", ":material/group:"),
    NavItem("Settings", ":material/settings:"),
]

# Must match the DB's CHECK constraint on documents.category (sqlite_db.py) and the
# Category literal in models/schemas.py — this is also what retrieval routes on.
_CATEGORIES = ["Procedures", "Promotions", "Safety", "Unknown"]

_STATUS_COLOR = {
    "Active": "green",
    "Superseded": "violet",
    "Failed": "red",
    "Pending": "orange",
    "Processing": "blue",
    "Rejected": "gray",
}

_TYPE_ICON = {
    "PDF": (":material/picture_as_pdf:", "red"),
    "DOCX": (":material/description:", "blue"),
    "TXT": (":material/article:", "gray"),
    "CSV": (":material/table_chart:", "green"),
}

_ACTIVITY_DATA = pd.DataFrame(
    {
        "Uploaded": [5, 8, 6, 9, 14, 16, 11, 13],
        "Updated": [2, 4, 3, 6, 8, 11, 7, 9],
    },
    index=["Aug 22", "Aug 23", "Aug 24", "Aug 25", "Aug 26", "Aug 27", "Aug 28", "Aug 29"],
)


def _format_timestamp(value: str | None) -> str:
    if not value:
        return "—"
    try:
        dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return value
    return dt.strftime("%b %d, %Y %I:%M %p")


def _list_version_rows() -> list[dict]:
    """Flattens every document version (across all documents) into one row per version,
    newest first — sourced live from SQLite so the UI always reflects the real DB status."""
    rows = []
    for doc in documents_repo.list_all_documents():
        for version in documents_repo.list_versions(doc.id):
            suffix = Path(version.file_path).suffix.lstrip(".").upper() if version.file_path else "—"
            rows.append(
                {
                    "title": doc.title,
                    "type": suffix or "—",
                    "category": doc.category,
                    "version": version.version,
                    "uploaded_on": _format_timestamp(version.created_at),
                    "status": version.status.capitalize(),
                    "_created_at": version.created_at or "",
                }
            )
    rows.sort(key=lambda r: r["_created_at"], reverse=True)
    return rows


def _status_counts(rows: list[dict]) -> dict[str, int]:
    counts = {"Active": 0, "Superseded": 0, "Failed/Pending": 0}
    for row in rows:
        if row["status"] in ("Active", "Superseded"):
            counts[row["status"]] += 1
        else:  # Pending, Processing, Failed, Rejected all roll into this KPI bucket
            counts["Failed/Pending"] += 1
    return counts


def _doc_label(doc: dict) -> str:
    icon, color = _TYPE_ICON.get(doc["type"], (":material/draft:", "gray"))
    return f":{color}[{icon}] **{doc['title']}**"


def _render_document_row(doc: dict, show_category: bool = False) -> None:
    with st.container(border=True):
        cols = st.columns([3, 1.4, 1.6, 1] if not show_category else [2.4, 1.2, 1, 1.6, 1])
        cols[0].markdown(_doc_label(doc))
        if show_category:
            cols[1].write(doc["category"])
            cols[2].write(doc["version"])
            cols[3].write(doc["uploaded_on"])
            cols[4].badge(doc["status"], color=_STATUS_COLOR[doc["status"]])
        else:
            cols[1].write(doc["type"])
            cols[2].write(doc["uploaded_on"])
            cols[3].badge(doc["status"], color=_STATUS_COLOR[doc["status"]])


def _render_dashboard(username: str) -> None:
    st.subheader(f"Good Morning, {username.title()} :material/waving_hand:")
    st.caption("Here's what's happening with your knowledge base today.")

    stats = documents_repo.get_kb_stats()
    status_counts = stats["status_counts"]
    total = stats["total_documents"]
    active = status_counts.get("active", 0)
    superseded = status_counts.get("superseded", 0)
    failed_pending = (
        status_counts.get("failed", 0) + status_counts.get("pending", 0) + status_counts.get("processing", 0)
    )

    with st.container(horizontal=True):
        st.metric("Total Documents", total, border=True, icon=":material/description:")
        st.metric("Active Versions", active, border=True, icon=":material/check_circle:")
        st.metric("Superseded Versions", superseded, border=True, icon=":material/sync_alt:")
        st.metric("Failed/Pending", failed_pending, border=True, icon=":material/error:")

    col1, col2 = st.columns([1.6, 1])
    with col1:
        with st.container(border=True):
            header_col, filter_col = st.columns([3, 1])
            header_col.markdown("**:material/calendar_month: Document Activity**")
            filter_col.selectbox(
                "Range", ["Last 7 days", "Last 30 days", "Last 90 days"],
                label_visibility="collapsed", key="activity_range",
            )
            st.line_chart(_ACTIVITY_DATA, color=["#4F7CFF", "#9B6BFF"])

    with col2:
        with st.container(border=True):
            title_col, link_col = st.columns([2, 1])
            title_col.markdown("**Recent Documents**")
            link_col.button("View all", key="view_all_recent", type="tertiary")
            recent = _list_version_rows()[:5]
            if not recent:
                st.caption("No documents uploaded yet.")
            for row in recent:
                _render_document_row(row)


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


def _render_documents(username: str) -> None:
    st.subheader("Upload Document")

    if "pending_upload" in st.session_state:
        _render_review_form()
        return

    with st.container(border=True):
        uploaded_file = st.file_uploader(
            "Drag & drop your file here, or click to browse",
            type=["pdf", "docx", "txt", "csv"],
        )
        st.caption("Supported formats: PDF, DOCX, TXT, CSV · Max file size: 20 MB")

    title = st.text_input("Document Title", placeholder="Enter document title (e.g. 'Return Policy')")
    if st.button("Process Upload", type="primary"):
        if not uploaded_file or not title.strip():
            st.error("Please choose a file and provide a document title.")
        else:
            _process_upload(uploaded_file, title.strip())
            st.rerun()


def _render_knowledge_base(username: str) -> None:
    documents = _list_version_rows()
    counts = _status_counts(documents)

    header_col, button_col = st.columns([3, 1])
    with header_col:
        st.subheader("Knowledge Base")
        st.caption("Manage and organize your knowledge base documents.")
    with button_col:
        st.write("")
        if st.button("Upload Document", icon=":material/upload:", type="primary", width="stretch"):
            st.session_state.admin_nav = "Documents"
            st.rerun()

    filter_col, search_col = st.columns([2, 1.3])
    with filter_col:
        choice = st.segmented_control(
            "Filter",
            [
                f"All ({len(documents)})",
                f"Active ({counts['Active']})",
                f"Superseded ({counts['Superseded']})",
                f"Failed/Pending ({counts['Failed/Pending']})",
            ],
            default=f"All ({len(documents)})",
            label_visibility="collapsed",
        )
    with search_col:
        search = st.text_input(
            "Search", placeholder="Search documents...",
            icon=":material/search:", label_visibility="collapsed",
        )

    filtered = documents
    if choice and choice.startswith("Active"):
        filtered = [d for d in documents if d["status"] == "Active"]
    elif choice and choice.startswith("Superseded"):
        filtered = [d for d in documents if d["status"] == "Superseded"]
    elif choice and choice.startswith("Failed/Pending"):
        filtered = [d for d in documents if d["status"] in ("Failed", "Pending")]
    if search:
        filtered = [d for d in filtered if search.lower() in d["title"].lower()]

    header = st.columns([2.4, 1.2, 1, 1.6, 1])
    header[0].caption("Title")
    header[1].caption("Category")
    header[2].caption("Version")
    header[3].caption("Uploaded On")
    header[4].caption("Status")

    page_size = 10
    st.session_state.setdefault("kb_page", 1)
    total_pages = max(1, -(-len(filtered) // page_size))
    page = min(st.session_state.kb_page, total_pages)
    start = (page - 1) * page_size
    page_rows = filtered[start : start + page_size]

    if not page_rows:
        st.caption("No documents match this filter.")
    for doc in page_rows:
        _render_document_row(doc, show_category=True)

    if total_pages > 1:
        st.caption(
            f"Showing {start + 1}-{start + len(page_rows)} of {len(filtered)} documents"
        )
        nav_cols = st.columns(total_pages)
        for i, col in enumerate(nav_cols, start=1):
            if col.button(str(i), key=f"kb_page_{i}", type="primary" if i == page else "secondary"):
                st.session_state.kb_page = i
                st.rerun()


def _render_placeholder(title: str) -> None:
    st.subheader(title)
    st.info(f"{title} is not part of this UI pass yet — coming soon.")


def render(username: str, role: str = "admin") -> None:
    nav = render_sidebar(_NAV_ITEMS, "admin_nav", username, role)
    render_header(username, role)

    if nav == "Dashboard":
        _render_dashboard(username)
    elif nav == "Documents":
        _render_documents(username)
    elif nav == "Knowledge Base":
        _render_knowledge_base(username)
    else:
        _render_placeholder(nav)

    render_footer()
