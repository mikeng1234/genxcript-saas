"""
GeNXcript Module Administration — Super Admin Only.
Manage enabled modules, subscription tiers, and employee limits per company.
This page is ONLY accessible to GeNXcript platform super-admins.
"""

import streamlit as st
import json
from app.db_helper import get_db
from app.auth import (
    is_super_admin, MODULE_DEFS, TIER_MODULES, TIER_LABELS,
    TIER_MAX_EMPLOYEES,
)
from app.styles import inject_css


def render():
    inject_css()

    if not is_super_admin():
        st.error("Access denied. This page is restricted to GeNXcript platform administrators.")
        return

    st.title("🔧 Module Administration")
    st.caption("GeNXcript internal — manage subscription tiers and module access per company.")

    db = get_db()

    # Load all companies
    companies = db.table("companies").select(
        "id, name, enabled_modules, subscription_tier, max_employees, "
        "subscription_start, subscription_end"
    ).order("name").execute().data or []

    if not companies:
        st.warning("No companies found.")
        return

    # ── Overview cards ──
    st.markdown("### Overview")
    cols = st.columns(4)
    cols[0].metric("Total Companies", len(companies))
    tier_counts = {}
    for c in companies:
        t = c.get("subscription_tier", "unknown")
        tier_counts[t] = tier_counts.get(t, 0) + 1
    for i, (tier, count) in enumerate(sorted(tier_counts.items())):
        if i + 1 < len(cols):
            cols[i + 1].metric(f"{TIER_LABELS.get(tier, tier.title())}", count)

    st.divider()

    # ── Company selector ──
    company_names = {c["id"]: c["name"] for c in companies}
    selected_id = st.selectbox(
        "Select Company",
        options=[c["id"] for c in companies],
        format_func=lambda x: company_names.get(x, x),
        key="mod_admin_company",
    )

    company = next((c for c in companies if c["id"] == selected_id), None)
    if not company:
        return

    current_modules = company.get("enabled_modules") or ["core"]
    current_tier = company.get("subscription_tier") or "enterprise"
    current_max = company.get("max_employees") or 999

    # Count active employees
    emp_count_result = db.table("employees").select("id", count="exact").eq(
        "company_id", selected_id
    ).eq("is_active", True).execute()
    active_emps = emp_count_result.count if emp_count_result.count is not None else 0

    st.markdown(f"### {company['name']}")
    info_cols = st.columns(3)
    info_cols[0].metric("Active Employees", f"{active_emps} / {current_max}")
    info_cols[1].metric("Current Tier", TIER_LABELS.get(current_tier, current_tier))
    info_cols[2].metric("Modules Enabled", f"{len(current_modules)} / {len(MODULE_DEFS)}")

    st.divider()

    # ── Quick Tier Selector ──
    st.markdown("#### Quick Tier Assignment")
    tier_col1, tier_col2 = st.columns([3, 1])
    with tier_col1:
        new_tier = st.selectbox(
            "Set Subscription Tier",
            options=list(TIER_MODULES.keys()),
            format_func=lambda x: f"{TIER_LABELS[x]} — {', '.join(TIER_MODULES[x])}",
            index=list(TIER_MODULES.keys()).index(current_tier) if current_tier in TIER_MODULES else 3,
            key="mod_admin_tier",
        )
    with tier_col2:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("Apply Tier", key="mod_admin_apply_tier", type="primary"):
            tier_modules = TIER_MODULES[new_tier]
            tier_max = TIER_MAX_EMPLOYEES[new_tier]
            db.table("companies").update({
                "enabled_modules": tier_modules,
                "subscription_tier": new_tier,
                "max_employees": tier_max,
            }).eq("id", selected_id).execute()
            # Update session if this is the current company
            if st.session_state.get("company_id") == selected_id:
                st.session_state["_company_data"] = {
                    "enabled_modules": tier_modules,
                    "subscription_tier": new_tier,
                    "max_employees": tier_max,
                }
            st.success(f"Set to **{TIER_LABELS[new_tier]}** — {len(tier_modules)} modules, {tier_max} max employees.")
            st.rerun()

    st.divider()

    # ── Custom Module Toggle ──
    st.markdown("#### Custom Module Control")
    st.caption("Override tier defaults — toggle individual modules on/off.")

    _changed = False
    new_modules = list(current_modules)

    for mod_key, (mod_label, mod_color, mod_desc) in MODULE_DEFS.items():
        is_core = mod_key == "core"
        is_enabled = mod_key in current_modules
        col_toggle, col_info = st.columns([1, 4])
        with col_toggle:
            toggled = st.toggle(
                mod_label,
                value=is_enabled,
                disabled=is_core,  # Core can't be disabled
                key=f"mod_toggle_{mod_key}",
            )
        with col_info:
            _status = "🟢 Always On" if is_core else ("🟢 Enabled" if toggled else "⚫ Disabled")
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;padding:4px 0;">'
                f'<span style="width:12px;height:12px;border-radius:50%;background:{mod_color};'
                f'display:inline-block;flex-shrink:0;"></span>'
                f'<span style="font-size:13px;font-weight:700;color:#191c1d;">{mod_label}</span>'
                f'<span style="font-size:11px;color:#727784;">— {mod_desc}</span>'
                f'<span style="font-size:10px;color:#9ca3af;margin-left:auto;">{_status}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        if not is_core:
            if toggled and mod_key not in new_modules:
                new_modules.append(mod_key)
                _changed = True
            elif not toggled and mod_key in new_modules:
                new_modules.remove(mod_key)
                _changed = True

    if _changed:
        st.markdown("---")
        if st.button("💾 Save Custom Modules", type="primary", key="mod_admin_save_custom"):
            db.table("companies").update({
                "enabled_modules": new_modules,
                "subscription_tier": "custom",  # Mark as custom since they overrode tier
            }).eq("id", selected_id).execute()
            if st.session_state.get("company_id") == selected_id:
                st.session_state["_company_data"] = {
                    "enabled_modules": new_modules,
                    "subscription_tier": "custom",
                    "max_employees": current_max,
                }
            st.success(f"Updated to {len(new_modules)} modules (custom configuration).")
            st.rerun()

    st.divider()

    # ── Employee Limit ──
    st.markdown("#### Employee Limit")
    new_max = st.number_input(
        "Max Employees",
        min_value=1,
        max_value=9999,
        value=current_max,
        key="mod_admin_max_emp",
    )
    if new_max != current_max:
        if st.button("Update Limit", key="mod_admin_save_limit"):
            db.table("companies").update({"max_employees": new_max}).eq("id", selected_id).execute()
            if st.session_state.get("company_id") == selected_id:
                cd = st.session_state.get("_company_data", {})
                cd["max_employees"] = new_max
                st.session_state["_company_data"] = cd
            st.success(f"Max employees updated to {new_max}.")
            st.rerun()

    st.divider()

    # ── Raw JSON view (debug) ──
    with st.expander("📋 Raw Company Module Data"):
        st.json({
            "company_id": selected_id,
            "name": company["name"],
            "enabled_modules": current_modules,
            "subscription_tier": current_tier,
            "max_employees": current_max,
            "active_employees": active_emps,
            "subscription_start": company.get("subscription_start"),
            "subscription_end": company.get("subscription_end"),
        })
