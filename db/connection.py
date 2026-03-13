"""
Database connection module.
Provides a Supabase client configured from environment variables.
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


def get_supabase_client() -> Client:
    """Returns a Supabase client using the anon key (respects RLS)."""
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def get_supabase_admin_client() -> Client:
    """Returns a Supabase client using the service role key (bypasses RLS).
    Use only for admin operations like seeding government rates."""
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)
