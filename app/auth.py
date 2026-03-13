"""
Authentication helpers for GenXcript Payroll SaaS.

Session persistence strategy: st.query_params + server-side cache
- On login/signup, a random session token is generated and stored in:
    1. A server-side dict (cached for the Streamlit process lifetime)
    2. st.query_params["sid"] — survives F5 browser refresh
- On every page load, main.py calls restore_from_query_params() which
  reads the token from the URL and restores the session silently.
- On logout, the token is invalidated and removed from the URL.

No external packages needed — st.query_params is built into Streamlit.
"""

import os
import uuid
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


# ============================================================
# Server-side session store
# Cached for the lifetime of the Streamlit process.
# Users need to log in again only if the server restarts.
# ============================================================

@st.cache_resource
def _session_cache() -> dict:
    return {}


# ============================================================
# Auth Client
# ============================================================

def _get_auth_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)


# ============================================================
# Session helpers
# ============================================================

def is_logged_in() -> bool:
    return bool(st.session_state.get("user_id") and st.session_state.get("company_id"))


def get_current_user_email() -> str:
    return st.session_state.get("user_email", "")


def get_current_company_id() -> str:
    company_id = st.session_state.get("company_id")
    if not company_id:
        raise RuntimeError("No active session. Please log in.")
    return company_id


def _store_session(user_id: str, user_email: str, company_id: str):
    """
    Persist session to:
    1. st.session_state (current render)
    2. Server-side cache (survives reruns)
    3. st.query_params["sid"] (survives F5 refresh)
    """
    st.session_state.user_id    = user_id
    st.session_state.user_email = user_email
    st.session_state.company_id = company_id

    token = str(uuid.uuid4())
    _session_cache()[token] = {
        "user_id":    user_id,
        "user_email": user_email,
        "company_id": company_id,
    }
    st.query_params["sid"] = token


def restore_from_query_params() -> bool:
    """
    Try to restore session from URL query params.
    Called on every page load in main.py.
    Returns True if session was restored, False otherwise.
    """
    if is_logged_in():
        return True

    sid = st.query_params.get("sid")
    if not sid:
        return False

    session = _session_cache().get(sid)
    if not session:
        # Token exists in URL but not in cache (server restarted)
        st.query_params.clear()
        return False

    st.session_state.user_id    = session["user_id"]
    st.session_state.user_email = session["user_email"]
    st.session_state.company_id = session["company_id"]
    return True


def logout():
    """Invalidate session token and clear state."""
    sid = st.query_params.get("sid")
    if sid:
        _session_cache().pop(sid, None)
    st.query_params.clear()
    for key in ["user_id", "user_email", "company_id"]:
        st.session_state.pop(key, None)


# ============================================================
# Login
# ============================================================

def login(email: str, password: str) -> tuple[bool, str]:
    try:
        client = _get_auth_client()
        response = client.auth.sign_in_with_password({"email": email, "password": password})
        user = response.user

        if not user:
            return False, "Invalid email or password."

        from app.db_helper import get_db
        db = get_db()
        result = (
            db.table("user_company_access")
            .select("company_id")
            .eq("user_id", str(user.id))
            .execute()
        )

        if not result.data:
            return False, "No company linked to this account. Contact support."

        _store_session(str(user.id), user.email, result.data[0]["company_id"])
        return True, ""

    except Exception as e:
        msg = str(e)
        if "invalid login" in msg.lower() or "invalid credentials" in msg.lower():
            return False, "Incorrect email or password."
        return False, f"Login error: {msg}"


# ============================================================
# Signup
# ============================================================

def signup(
    email: str,
    password: str,
    company_name: str,
    region: str,
    pay_frequency: str,
) -> tuple[bool, str]:
    try:
        client = _get_auth_client()
        response = client.auth.sign_up({"email": email, "password": password})
        user = response.user

        if not user:
            return False, "Signup failed. Please try again."

        from app.db_helper import get_db
        db = get_db()

        company_result = db.table("companies").insert({
            "name": company_name.strip(),
            "region": region,
            "pay_frequency": pay_frequency,
        }).execute()

        if not company_result.data:
            return False, "Failed to create company. Please try again."

        company_id = company_result.data[0]["id"]

        db.table("user_company_access").insert({
            "user_id": str(user.id),
            "company_id": company_id,
            "role": "admin",
        }).execute()

        confirmed = (
            getattr(user, "email_confirmed_at", None)
            or getattr(user, "confirmed_at", None)
        )

        if confirmed:
            _store_session(str(user.id), user.email, company_id)
            return True, ""
        else:
            return True, "CHECK_EMAIL"

    except Exception as e:
        msg = str(e)
        if "already registered" in msg.lower():
            return False, "An account with this email already exists. Please log in."
        return False, f"Signup error: {msg}"
