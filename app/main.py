"""Single Streamlit entrypoint: one login page, then routes to the Admin or Employee view
based on the authenticated role (per user decision — one app, one login, role-gated views)."""
import streamlit as st

from app.auth import authenticate
from app.storage.sqlite_db import init_db
from app.ui import admin_view, employee_view

st.set_page_config(page_title="Store Operations Knowledge Assistant", page_icon="🗂️", layout="wide")

init_db()

if "user" not in st.session_state:
    st.session_state.user = None


def login_form() -> None:
    st.title("Store Operations Knowledge Assistant")
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")
    if submitted:
        user = authenticate(username, password)
        if user:
            st.session_state.user = user
            st.rerun()
        else:
            st.error("Invalid username or password.")


def main() -> None:
    user = st.session_state.user
    if user is None:
        login_form()
        return

    if user.role == "admin":
        admin_view.render(user.username, user.role)
    else:
        employee_view.render(user.username, user.role)


main()
