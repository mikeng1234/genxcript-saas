"""
hash_auth component — reads URL hash fragments in the browser and returns
them to Streamlit Python.

Supabase implicit-flow password-reset emails redirect to:
  http://localhost:8501/#access_token=...&type=recovery&...

The server never sees URL hashes, so we use a declare_component to run JS
in the browser, parse the hash, and call setComponentValue back to Python.

Usage:
    from app.components.hash_auth import read_hash_auth
    result = read_hash_auth(key="hash_auth")
    # result is None until the browser responds, then either:
    #   None  — no relevant hash params found
    #   {"type": "recovery", "access_token": "...", "refresh_token": "..."}
"""

import os
import streamlit.components.v1 as components

_COMPONENT_DIR = os.path.join(os.path.dirname(__file__), "hash_auth_frontend")

read_hash_auth = components.declare_component(
    "read_hash_auth",
    path=_COMPONENT_DIR,
)
