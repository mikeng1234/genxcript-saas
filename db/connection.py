"""
Database connection module.
Provides a Supabase client configured from environment variables.
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions

load_dotenv()


def get_supabase_client() -> Client:
    """Returns a Supabase client using the anon key (respects RLS)."""
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def get_supabase_admin_client() -> Client:
    """Returns a Supabase client using the service role key (bypasses RLS).
    Use only for admin operations like seeding government rates.

    auto_refresh_token=False: The service role key is a static JWT, not a
    user session. Disabling auto-refresh prevents gotrue from attempting to
    refresh it as a regular session token (which would fail after ~1 hour
    and leave the client in a broken JWT-expired state).
    """
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    return create_client(
        url, key,
        options=ClientOptions(auto_refresh_token=False, persist_session=False),
    )
