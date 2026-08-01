"""Unified identity: Google OAuth (st.login) or a simple no-password email form."""
import streamlit as st

import db


def normalize_email(email: str) -> str:
    return email.strip().lower()


def google_is_logged_in() -> bool:
    # st.user has no `is_logged_in` attribute at all until [auth] exists in secrets.toml.
    return bool(getattr(st.user, "is_logged_in", False))


def google_login_available() -> bool:
    return "auth" in st.secrets


def _sync_user(email: str, display_name: str | None) -> dict:
    email = normalize_email(email)
    cached = st.session_state.get("_current_user")
    if cached and cached["email"] == email:
        return cached
    user = db.upsert_user(email, display_name)
    st.session_state["_current_user"] = user
    return user


def get_current_user() -> dict | None:
    if google_is_logged_in():
        return _sync_user(st.user.email, getattr(st.user, "name", None))
    if st.session_state.get("simple_login_email"):
        return _sync_user(
            st.session_state["simple_login_email"],
            st.session_state.get("simple_login_name"),
        )
    return None


def render_login_screen(invited_group_name: str | None = None) -> None:
    st.title("Vakantie-lijst")
    if invited_group_name:
        st.info(
            f"Je bent uitgenodigd voor de groep **{invited_group_name}**. "
            "Log hieronder in en plak daarna je uitnodigingscode in de zijbalk."
        )

    if google_login_available():
        if st.button("Inloggen met Google"):
            st.login()
        st.divider()
        st.caption("Of log in met enkel je naam en e-mailadres:")

    with st.form("simple_login_form"):
        name = st.text_input("Naam")
        email = st.text_input("E-mailadres")
        submitted = st.form_submit_button("Inloggen")
        if submitted:
            if "@" not in email:
                st.error("Vul een geldig e-mailadres in.")
            else:
                st.session_state["simple_login_name"] = name.strip() or None
                st.session_state["simple_login_email"] = normalize_email(email)
                st.rerun()


def logout() -> None:
    was_google = google_is_logged_in()
    for key in ("simple_login_email", "simple_login_name", "_current_user", "active_group_id"):
        st.session_state.pop(key, None)
    if was_google:
        st.logout()
    else:
        st.rerun()
