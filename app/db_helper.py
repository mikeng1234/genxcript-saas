"""
Shared database helper for Streamlit pages.
Provides a cached Supabase client and the current company ID.
"""

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from db.connection import get_supabase_admin_client


@st.cache_resource
def get_db():
    """Returns a Supabase admin client (cached across reruns).
    Uses service role key — RLS is bypassed, but all queries manually
    filter by company_id from the authenticated user's session."""
    return get_supabase_admin_client()


def get_company_id() -> str:
    """Returns the current user's company ID from the active session."""
    from app.auth import get_current_company_id
    return get_current_company_id()


def log_action(
    action: str,
    entity_type: str,
    entity_id: str = None,
    entity_label: str = "",
    details: dict = None,
) -> None:
    """Write one audit log entry. Never raises — logging must not break main operations."""
    try:
        company_id = get_company_id()
        get_db().table("audit_logs").insert({
            "company_id":   company_id,
            "user_id":      st.session_state.get("user_id", ""),
            "user_email":   st.session_state.get("user_email", ""),
            "action":       action,
            "entity_type":  entity_type,
            "entity_id":    str(entity_id) if entity_id else None,
            "entity_label": entity_label,
            "details":      details or {},
        }).execute()
    except Exception:
        pass
