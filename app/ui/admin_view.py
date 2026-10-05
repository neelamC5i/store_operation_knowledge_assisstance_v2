"""Admin dashboard UI (display-only, dummy data) — mirrors the Dashboard / Documents
upload / Knowledge Base mockups. UI-only pass: no backend wiring, all data is dummy
and lives in session state purely so the screens look alive when clicked through."""
from datetime import datetime

import pandas as pd
import streamlit as st

from app.ui.layout import NavItem, render_footer, render_header, render_sidebar

_NAV_ITEMS = [
    NavItem("Dashboard", ":material/dashboard:"),
    NavItem("Documents", ":material/description:"),
    NavItem("Knowledge Base", ":material/menu_book:"),
    NavItem("Users", ":material/group:"),
    NavItem("Settings", ":material/settings:"),
]

_CATEGORIES = ["Policies", "HR", "Product", "IT", "Marketing", "Support", "Safety", "Promotions"]

_STATUS_COLOR = {"Active": "green", "Superseded": "violet", "Failed": "red", "Pending": "orange"}

_TYPE_ICON = {
    "PDF": (":material/picture_as_pdf:", "red"),
    "DOCX": (":material/description:", "blue"),
    "TXT": (":material/article:", "gray"),
    "CSV": (":material/table_chart:", "green"),
    "XLSX": (":material/table_chart:", "green"),
    "PPTX": (":material/slideshow:", "orange"),
}

_DUMMY_DOCUMENTS = [
    ("Return Policy", "PDF", "Policies", "v2.1", "Aug 28, 2025 10:24 AM", "Active"),
    ("Employee Handbook", "DOCX", "HR", "v1.3", "Aug 27, 2025 03:15 PM", "Active"),
    ("Product Guidelines", "PDF", "Product", "v1.0", "Aug 26, 2025 11:40 AM", "Active"),
    ("HR Policies", "DOCX", "HR", "v3.0", "Aug 25, 2025 02:30 PM", "Superseded"),
    ("IT Security Policy", "PDF", "IT", "v1.0", "Aug 24, 2025 09:12 AM", "Active"),
    ("Marketing Strategy", "PDF", "Marketing", "v1.0", "Aug 23, 2025 01:20 PM", "Active"),
    ("Customer Support Guide", "PDF", "Support", "v2.0", "Aug 22, 2025 11:05 AM", "Failed"),
    ("Store Safety Checklist", "PDF", "Safety", "v1.4", "Aug 21, 2025 04:50 PM", "Active"),
    ("Summer Promotions", "DOCX", "Promotions", "v1.1", "Aug 20, 2025 09:30 AM", "Pending"),
    ("Onboarding Guide", "PDF", "HR", "v1.0", "Aug 19, 2025 12:10 PM", "Active"),
    ("Refund Procedure", "PDF", "Policies", "v1.2", "Aug 18, 2025 03:45 PM", "Active"),
    ("Inventory Audit SOP", "DOCX", "Product", "v2.0", "Aug 17, 2025 10:05 AM", "Active"),
    ("Fire Drill Procedure", "PDF", "Safety", "v1.0", "Aug 16, 2025 02:00 PM", "Active"),
    ("POS Troubleshooting", "PDF", "IT", "v1.1", "Aug 15, 2025 11:25 AM", "Active"),
    ("Holiday Promotions", "DOCX", "Promotions", "v1.0", "Aug 14, 2025 09:50 AM", "Superseded"),
    ("Visual Merchandising", "PDF", "Marketing", "v1.0", "Aug 13, 2025 01:15 PM", "Active"),
    ("Customer Escalation Flow", "PDF", "Support", "v1.3", "Aug 12, 2025 04:20 PM", "Active"),
    ("New Hire Checklist", "DOCX", "HR", "v1.0", "Aug 11, 2025 10:40 AM", "Active"),
    ("Price Adjustment Policy", "PDF", "Policies", "v1.1", "Aug 10, 2025 03:05 PM", "Active"),
    ("Data Handling Policy", "PDF", "IT", "v2.0", "Aug 9, 2025 09:15 AM", "Superseded"),
    ("Warehouse Safety Rules", "PDF", "Safety", "v1.0", "Aug 8, 2025 02:35 PM", "Active"),
    ("Loyalty Program Guide", "DOCX", "Marketing", "v1.0", "Aug 7, 2025 11:50 AM", "Active"),
    ("Support Escalation SLA", "PDF", "Support", "v1.0", "Aug 6, 2025 01:30 PM", "Active"),
    ("Back-to-School Promotions", "PDF", "Promotions", "v1.0", "Aug 5, 2025 10:00 AM", "Pending"),
]

_ACTIVITY_DATA = pd.DataFrame(
    {
        "Uploaded": [5, 8, 6, 9, 14, 16, 11, 13],
        "Updated": [2, 4, 3, 6, 8, 11, 7, 9],
    },
    index=["Aug 22", "Aug 23", "Aug 24", "Aug 25", "Aug 26", "Aug 27", "Aug 28", "Aug 29"],
)


def _ensure_state() -> None:
    st.session_state.setdefault(
        "admin_documents",
        [
            {"title": t, "type": ty, "category": c, "version": v, "uploaded_on": d, "status": s}
            for t, ty, c, v, d, s in _DUMMY_DOCUMENTS
        ],
    )


def _status_counts(documents: list[dict]) -> dict[str, int]:
    counts = {"Active": 0, "Superseded": 0, "Failed/Pending": 0}
    for doc in documents:
        if doc["status"] in ("Failed", "Pending"):
            counts["Failed/Pending"] += 1
        else:
            counts[doc["status"]] += 1
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

    documents = st.session_state.admin_documents
    counts = _status_counts(documents)
    total = len(documents)

    with st.container(horizontal=True):
        st.metric("Total Documents", total, "+12%", border=True, icon=":material/description:")
        st.metric("Active Versions", counts["Active"], "+20%", border=True, icon=":material/check_circle:")
        st.metric(
            "Superseded Versions", counts["Superseded"], "-33%", border=True,
            icon=":material/sync_alt:",
        )
        st.metric(
            "Failed/Pending", counts["Failed/Pending"], "-50%", border=True,
            icon=":material/error:",
        )
    st.caption("vs. last 7 days")

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
            for doc in documents[:5]:
                _render_document_row(doc)


def _render_documents(username: str) -> None:
    st.subheader("Upload Document")

    with st.container(border=True):
        uploaded_file = st.file_uploader(
            "Drag & drop your file here, or click to browse",
            type=["pdf", "docx", "txt", "csv", "xlsx", "pptx"],
        )
        st.caption("Supported formats: PDF, DOCX, TXT, CSV, XLSX, PPTX · Max file size: 50 MB")

    st.markdown("**Upload Details**")
    with st.form("dummy_upload_form", border=False):
        col1, col2 = st.columns(2)
        title = col1.text_input("Document Title", placeholder="Enter document title")
        category = col2.selectbox("Category", _CATEGORIES)
        description = st.text_area("Description (optional)", placeholder="Add a short description")
        submitted = st.form_submit_button("Upload Document", type="primary")

    if submitted:
        if not uploaded_file or not title.strip():
            st.error("Please choose a file and provide a document title.")
        else:
            suffix = uploaded_file.name.rsplit(".", 1)[-1].upper()
            st.session_state.admin_documents.insert(
                0,
                {
                    "title": title.strip(),
                    "type": suffix,
                    "category": category,
                    "version": "v1.0",
                    "uploaded_on": datetime.now().strftime("%b %d, %Y %I:%M %p"),
                    "status": "Pending",
                },
            )
            st.success(f"'{title.strip()}' uploaded — it now shows up in the Knowledge Base as Pending.")


def _render_knowledge_base(username: str) -> None:
    documents = st.session_state.admin_documents
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
    _ensure_state()
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
