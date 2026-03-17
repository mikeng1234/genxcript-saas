"""
app/components/geolocation.py

Minimal Streamlit declared component that requests the browser's geolocation
once and returns the result back to Python via Streamlit.setComponentValue().

Usage:
    from app.components.geolocation import get_location

    loc = get_location(key="dtr_clock_in")
    # Returns None until the browser responds, then:
    # {"lat": 14.5995, "lng": 120.9842, "accuracy": 15.0, "error": None}
    # or on failure:
    # {"lat": None, "lng": None, "accuracy": None, "error": "User denied Geolocation"}

The component renders with height=0 — it is invisible and fires automatically
when the Python code calls get_location().
"""

import os
import streamlit.components.v1 as components

_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "geolocation_frontend")

get_location = components.declare_component(
    "get_location",
    path=_FRONTEND_DIR,
)
