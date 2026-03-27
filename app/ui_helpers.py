"""
Shared UI helpers for GeNXcript Payroll SaaS.
Reusable HTML generation functions used across multiple pages.
"""

from __future__ import annotations
import streamlit as st


# ── Hierarchy badge cache (computed once per session refresh) ──

def _get_hierarchy_data(company_id: str) -> dict:
    """Return cached hierarchy data: {emp_id: {"depth": int, "is_mgr": bool}}."""
    cache_key = f"_hierarchy_data_{company_id}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    from app.db_helper import get_db
    db = get_db()
    rows = (
        db.table("employees")
        .select("id, reports_to")
        .eq("company_id", company_id)
        .eq("is_active", True)
        .execute()
        .data or []
    )

    all_ids = {r["id"] for r in rows}
    parent_map = {}
    has_subordinates = set()
    for r in rows:
        rt = r.get("reports_to")
        if rt and rt in all_ids:
            parent_map[r["id"]] = rt
            has_subordinates.add(rt)

    def _depth(eid, seen=None):
        if seen is None:
            seen = set()
        if eid in seen:
            return 0
        seen.add(eid)
        p = parent_map.get(eid)
        return 0 if not p else 1 + _depth(p, seen)

    result = {}
    for r in rows:
        eid = r["id"]
        result[eid] = {
            "depth": _depth(eid),
            "is_mgr": eid in has_subordinates,
        }

    st.session_state[cache_key] = result
    return result


def hierarchy_badge_html(emp_id: str, company_id: str, is_active: bool = True) -> str:
    """Return HTML for a hierarchy shape badge.

    Depth 0 (top exec): hexagon
    Depth 1 (dept head): star
    Depth 2 (mid-level): square
    Depth 3 (team member): triangle
    Depth 4+ (rank-and-file): circle

    Gold = has subordinates, Green = individual contributor.
    Inactive = grey circle.
    """
    if not is_active:
        return (
            "<span style='width:11px;height:11px;border-radius:50%;background:#bdbdbd;"
            "border:2px solid #fff;display:inline-block;"
            "box-shadow:0 0 0 1px #bdbdbd55;'></span>"
        )

    data = _get_hierarchy_data(company_id)
    info = data.get(emp_id, {"depth": 99, "is_mgr": False})
    depth = info["depth"]
    is_mgr = info["is_mgr"]

    clr = "#f59e0b" if is_mgr else "#4caf50"
    border = f"border:2px solid #fff;box-shadow:0 0 0 1px {clr}55;"
    base = f"width:13px;height:13px;display:inline-block;{border}"

    if depth == 0:
        return (
            f"<span style='width:15px;height:15px;display:inline-flex;align-items:center;"
            f"justify-content:center;filter:drop-shadow(0 0 1px {clr}55);'>"
            f"<svg width='15' height='15' viewBox='0 0 16 16'>"
            f"<polygon points='8,1 14,4.5 14,11.5 8,15 2,11.5 2,4.5' "
            f"fill='{clr}' stroke='#fff' stroke-width='1.5'/></svg></span>"
        )
    elif depth == 1:
        return (
            f"<span style='width:15px;height:15px;display:inline-flex;align-items:center;"
            f"justify-content:center;filter:drop-shadow(0 0 1px {clr}55);'>"
            f"<svg width='15' height='15' viewBox='0 0 16 16'>"
            f"<polygon points='8,1 9.8,5.8 15,6.2 11,9.6 12.2,15 8,12 3.8,15 5,9.6 1,6.2 6.2,5.8' "
            f"fill='{clr}' stroke='#fff' stroke-width='1'/></svg></span>"
        )
    elif depth == 2:
        return f"<span style='{base}border-radius:3px;background:{clr};'></span>"
    elif depth == 3:
        return (
            f"<span style='width:15px;height:15px;display:inline-flex;align-items:center;"
            f"justify-content:center;filter:drop-shadow(0 0 1px {clr}55);'>"
            f"<svg width='15' height='15' viewBox='0 0 16 16'>"
            f"<polygon points='8,2 15,14 1,14' "
            f"fill='{clr}' stroke='#fff' stroke-width='1.5'/></svg></span>"
        )
    else:
        return f"<span style='{base}border-radius:50%;background:{clr};'></span>"


def avatar_with_badge(
    avatar_inner_html: str,
    emp_id: str,
    company_id: str,
    is_active: bool = True,
    size: int = 52,
) -> str:
    """Wrap an avatar in a position:relative container with a hierarchy badge at bottom-left."""
    badge = hierarchy_badge_html(emp_id, company_id, is_active)
    return (
        f"<div style='position:relative;flex-shrink:0;width:{size}px;height:{size}px;'>"
        f"{avatar_inner_html}"
        f"<div style='position:absolute;bottom:-2px;left:-2px;'>{badge}</div>"
        f"</div>"
    )
