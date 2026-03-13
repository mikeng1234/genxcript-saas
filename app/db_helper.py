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
