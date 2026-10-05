"""Reusable application shell — sidebar nav and top header — shared by every
authenticated page (admin + employee). UI-only: no backend/business logic lives
here, it only renders chrome and returns the active nav selection/session state
that each page already manages itself."""
from dataclasses import dataclass

import streamlit as st


@dataclass(frozen=True)
class NavItem:
    label: str
    icon: str


def render_sidebar(nav_items: list[NavItem], state_key: str, username: str, role: str) -> str:
    """Renders the shared sidebar (logo, nav, user/logout footer).

    Returns the currently active nav label (stored in st.session_state[state_key]).
    """
    st.session_state.setdefault(state_key, nav_items[0].label)

    with st.sidebar:
        st.markdown("### :material/hub: Knowledge Hub")
        st.write("")

        for item in nav_items:
            active = st.session_state[state_key] == item.label
            if st.button(
                item.label,
                icon=item.icon,
                key=f"{state_key}_{item.label}",
                type="primary" if active else "tertiary",
                width="stretch",
            ):
                st.session_state[state_key] = item.label
                st.rerun()

        st.container(height=1, border=False)  # spacer, pushes the user card down
        with st.container(border=True):
            st.write(f"**{username}**")
            st.caption(role.capitalize())
            if st.button("Log out", icon=":material/logout:", width="stretch", key=f"{state_key}_logout"):
                st.session_state.user = None
                st.rerun()

    return st.session_state[state_key]


def render_header(username: str, role: str) -> None:
    """Shared top header: global search, notifications, and the user menu.

    Purely presentational — search has no backend to query yet, and the bell/menu
    are static placeholders matching the reference design.
    """
    _, search_col, bell_col, user_col = st.columns([2.4, 3, 0.6, 1.6], vertical_alignment="center")

    with search_col:
        st.text_input(
            "Search",
            placeholder="Search documents, topics, or keywords...",
            icon=":material/search:",
            label_visibility="collapsed",
            key="header_search",
        )
    with bell_col:
        st.button("", icon=":material/notifications:", key="header_notifications", type="tertiary")
    with user_col:
        with st.popover(f":material/account_circle: {username}", width="stretch"):
            st.write(f"**{username}**")
            st.caption(role.capitalize())

    st.divider()


def render_footer() -> None:
    """Minimal footer for dashboard-style pages. Skipped on pages (like chat) where
    a docked input already owns the bottom of the viewport."""
    st.divider()
    st.caption("Store Operations Knowledge Assistant")
