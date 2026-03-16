"""
Company Setup — Streamlit page.

One-time onboarding and settings:
- Company name, address, region
- BIR TIN, SSS/PhilHealth/Pag-IBIG employer numbers
- Pay frequency + leave replenishment policy
- Leave Entitlement Templates (named tiers, assignable per employee)
"""

import streamlit as st
from datetime import datetime, timezone, timedelta
from app.db_helper import get_db, get_company_id, log_action


# ============================================================
# Constants
# ============================================================

PAY_FREQUENCIES = ["semi-monthly", "monthly", "weekly"]

REGIONS = [
    "NCR", "CAR", "Region I", "Region II", "Region III",
    "Region IV-A", "Region IV-B", "Region V", "Region VI",
    "Region VII", "Region VIII", "Region IX", "Region X",
    "Region XI", "Region XII", "Region XIII", "BARMM",
]


# ============================================================
# Database operations — Company
# ============================================================

def _load_company() -> dict:
    db = get_db()
    result = db.table("companies").select("*").eq("id", get_company_id()).execute()
    return result.data[0] if result.data else {}


def _update_company(data: dict) -> dict:
    db = get_db()
    result = db.table("companies").update(data).eq("id", get_company_id()).execute()
    return result.data[0]


# ============================================================
# Database operations — Leave Entitlement Templates
# ============================================================

def _load_templates() -> list[dict]:
    db = get_db()
    result = (
        db.table("leave_entitlement_templates")
        .select("*")
        .eq("company_id", get_company_id())
        .order("min_service_months")
        .execute()
    )
    return result.data or []


def _create_template(data: dict) -> dict:
    db = get_db()
    data["company_id"] = get_company_id()
    result = db.table("leave_entitlement_templates").insert(data).execute()
    return result.data[0]


def _update_template(tmpl_id: str, data: dict) -> dict:
    db = get_db()
    result = (
        db.table("leave_entitlement_templates")
        .update(data)
        .eq("id", tmpl_id)
        .execute()
    )
    return result.data[0]


def _delete_template(tmpl_id: str):
    db = get_db()
    db.table("leave_entitlement_templates").delete().eq("id", tmpl_id).execute()


# ============================================================
# Database operations — Audit Log
# ============================================================

def _load_audit_logs(limit: int = 200) -> list[dict]:
    db = get_db()
    result = (
        db.table("audit_logs")
        .select("*")
        .eq("company_id", get_company_id())
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


# ============================================================
# Helpers
# ============================================================

def _service_range_label(min_mo: int, max_mo: int | None) -> str:
    """Human-readable service-range label."""
    def _mo(m: int) -> str:
        if m % 12 == 0 and m > 0:
            y = m // 12
            return f"{y} yr{'s' if y != 1 else ''}"
        return f"{m} mo"

    lo = _mo(min_mo) if min_mo > 0 else "Start"
    if max_mo is None:
        return f"{lo}+"
    return f"{lo} – {_mo(max_mo + 1)}"  # show as exclusive upper bound for clarity


def _template_form(
    form_key: str,
    defaults: dict | None = None,
    submit_label: str = "Save Template",
) -> dict | None:
    """
    Render a template add/edit form.
    Returns the validated data dict on submit, None otherwise.
    """
    d = defaults or {}

    with st.form(form_key, clear_on_submit=(defaults is None)):
        c1, c2 = st.columns([2, 1])
        with c1:
            name = st.text_input("Template Name *", value=d.get("name", ""),
                                 placeholder="e.g. 0–1 Year, Probationary, Senior Staff")
        with c2:
            st.markdown("")  # spacer

        col1, col2 = st.columns(2)
        with col1:
            min_mo = st.number_input(
                "Min. Service (months) *",
                min_value=0, max_value=600,
                value=int(d.get("min_service_months", 0)),
                step=1,
                help="0 = from day one",
            )
        with col2:
            max_mo_raw = d.get("max_service_months")
            max_mo_default = int(max_mo_raw) if max_mo_raw is not None else 0
            max_mo = st.number_input(
                "Max. Service (months) — enter 0 for no upper limit",
                min_value=0, max_value=600,
                value=max_mo_default,
                step=1,
                help=(
                    "Example: enter 11 for 'up to 11 months'. "
                    "Enter 0 to leave this tier open-ended (e.g. senior staff)."
                ),
            )

        st.markdown("**Leave Days Per Year**")
        dc1, dc2, dc3 = st.columns(3)
        with dc1:
            vl = st.number_input("Vacation Leave (VL)", min_value=0, max_value=60,
                                 value=int(d.get("vl_days", 15)), step=1)
        with dc2:
            sl = st.number_input("Sick Leave (SL)", min_value=0, max_value=60,
                                 value=int(d.get("sl_days", 15)), step=1)
        with dc3:
            cl = st.number_input("Casual / Emergency Leave (CL)", min_value=0, max_value=30,
                                 value=int(d.get("cl_days", 5)), step=1)

        submitted = st.form_submit_button(submit_label, type="primary", use_container_width=True)

    if submitted:
        if not name.strip():
            st.error("Template name is required.")
            return None
        if max_mo != 0 and max_mo < min_mo:
            st.error("Max. service must be ≥ Min. service (or 0 for no upper limit).")
            return None
        return {
            "name":               name.strip(),
            "min_service_months": int(min_mo),
            "max_service_months": None if max_mo == 0 else int(max_mo),
            "vl_days":            int(vl),
            "sl_days":            int(sl),
            "cl_days":            int(cl),
        }
    return None


# ============================================================
# Template section (outside main form)
# ============================================================

def _render_template_section():
    st.subheader("Leave Entitlement Templates")
    st.caption(
        "Create named leave tiers (e.g. by years of service) and assign one to each employee. "
        "Employees without an assigned template use company defaults (15 VL / 15 SL / 5 CL)."
    )

    # ── Add Template button ──────────────────────────────────────────────────
    add_col, _ = st.columns([1, 3])
    with add_col:
        if st.button("+ Add Template", key="tmpl_add_btn"):
            st.session_state.show_add_template = True

    if st.session_state.get("show_add_template"):
        st.markdown("**New Template**")
        new_data = _template_form("add_template_form", submit_label="Add Template")
        if new_data is not None:
            try:
                result = _create_template(new_data)
                log_action("created", "leave_template", result["id"], new_data["name"])
                st.session_state.show_add_template = False
                st.success(f"Template **{new_data['name']}** added.")
                st.rerun()
            except Exception as e:
                st.error(f"Error creating template: {e}")
        cancel_col, _ = st.columns([1, 4])
        with cancel_col:
            if st.button("Cancel", key="tmpl_add_cancel"):
                st.session_state.show_add_template = False
                st.rerun()

    templates = _load_templates()

    if not templates:
        st.info("No templates yet. Click **+ Add Template** to create your first leave tier.")
        return

    # ── Templates table ──────────────────────────────────────────────────────
    hdr = st.columns([2.5, 2, 1, 1, 1, 1.8])
    for col, lbl in zip(hdr, ["Name", "Service Range", "VL", "SL", "CL", "Actions"]):
        col.markdown(f"**{lbl}**")

    for tmpl in templates:
        row = st.columns([2.5, 2, 1, 1, 1, 1.8])
        row[0].text(tmpl["name"])
        row[1].text(_service_range_label(tmpl["min_service_months"], tmpl["max_service_months"]))
        row[2].text(str(tmpl["vl_days"]))
        row[3].text(str(tmpl["sl_days"]))
        row[4].text(str(tmpl["cl_days"]))

        act1, act2 = row[5].columns(2)
        with act1:
            if st.button("Edit", key=f"tmpl_edit_{tmpl['id']}", use_container_width=True):
                # Toggle: if already editing this one, close it
                if st.session_state.get("editing_template_id") == tmpl["id"]:
                    st.session_state.editing_template_id = None
                else:
                    st.session_state.editing_template_id = tmpl["id"]
                    st.session_state.show_add_template = False
                st.rerun()
        with act2:
            if st.button("Del", key=f"tmpl_del_{tmpl['id']}", use_container_width=True,
                         help="Delete this template. Employees assigned to it will revert to default."):
                st.session_state[f"del_confirm_{tmpl['id']}"] = True
                st.rerun()

        # Delete confirmation
        if st.session_state.get(f"del_confirm_{tmpl['id']}"):
            st.warning(
                f"Delete **{tmpl['name']}**? Employees assigned to this template will revert "
                "to the company default entitlement."
            )
            dc1, dc2, _ = st.columns([1, 1, 3])
            with dc1:
                if st.button("Confirm Delete", key=f"tmpl_del_yes_{tmpl['id']}", type="primary"):
                    try:
                        _delete_template(tmpl["id"])
                        log_action("deleted", "leave_template", tmpl["id"], tmpl["name"])
                        st.session_state.pop(f"del_confirm_{tmpl['id']}", None)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
            with dc2:
                if st.button("Cancel", key=f"tmpl_del_no_{tmpl['id']}"):
                    st.session_state.pop(f"del_confirm_{tmpl['id']}", None)
                    st.rerun()

        # Inline edit form
        if st.session_state.get("editing_template_id") == tmpl["id"]:
            st.markdown(f"**Editing: {tmpl['name']}**")
            updated = _template_form(
                f"edit_template_{tmpl['id']}",
                defaults=tmpl,
                submit_label="Save Changes",
            )
            if updated is not None:
                try:
                    _update_template(tmpl["id"], updated)
                    log_action("updated", "leave_template", tmpl["id"], updated["name"])
                    st.session_state.editing_template_id = None
                    st.success(f"Template **{updated['name']}** updated.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error updating template: {e}")
            cancel2, _ = st.columns([1, 4])
            with cancel2:
                if st.button("Cancel Edit", key=f"tmpl_edit_cancel_{tmpl['id']}"):
                    st.session_state.editing_template_id = None
                    st.rerun()

        st.divider()


# ============================================================
# Main Page Render
# ============================================================

_ACTION_COLORS = {
    "created":   ("#16a34a", "#dcfce7"),
    "updated":   ("#2563eb", "#dbeafe"),
    "finalized": ("#1e3a5f", "#e0f2fe"),
    "reviewed":  ("#7c3aed", "#ede9fe"),
    "paid":      ("#0d9488", "#ccfbf1"),
    "approved":  ("#16a34a", "#dcfce7"),
    "rejected":  ("#dc2626", "#fee2e2"),
    "deleted":   ("#dc2626", "#fee2e2"),
}

_ENTITY_LABELS = {
    "employee":         "Employee",
    "pay_period":       "Pay Period",
    "payroll_entries":  "Payroll Entries",
    "leave_request":    "Leave Request",
    "overtime_request": "OT Request",
    "company":          "Company",
    "leave_template":   "Leave Template",
}

_PH_TZ = timezone(timedelta(hours=8))


def _action_badge(action: str) -> str:
    fg, bg = _ACTION_COLORS.get(action, ("#6b7280", "#f3f4f6"))
    return (
        f'<span style="background:{bg};color:{fg};padding:2px 10px;border-radius:12px;'
        f'font-size:11px;font-weight:700;letter-spacing:.3px;white-space:nowrap">'
        f'{action.upper()}</span>'
    )


def _log_matches_search(log: dict, q: str) -> bool:
    """Return True if any searchable field in the log entry contains q (case-insensitive)."""
    haystack = " ".join([
        log.get("entity_label") or "",
        log.get("action") or "",
        log.get("entity_type") or "",
        log.get("user_email") or "",
        " ".join(f"{k} {v}" for k, v in (log.get("details") or {}).items()),
    ]).lower()
    return q in haystack


def _render_activity_log_tab():
    logs = _load_audit_logs()

    search_col, type_col, count_col = st.columns([3, 2, 2])
    with search_col:
        search_q = st.text_input(
            "Search",
            placeholder="Search by name, amount, field changed…",
            label_visibility="collapsed",
        ).strip().lower()
    with type_col:
        entity_options = ["All"] + list(_ENTITY_LABELS.keys())
        selected_entity = st.selectbox(
            "Filter by type",
            options=entity_options,
            format_func=lambda x: "All types" if x == "All" else _ENTITY_LABELS.get(x, x),
            label_visibility="collapsed",
        )

    # Apply type filter then search filter
    filtered = logs if selected_entity == "All" else [l for l in logs if l.get("entity_type") == selected_entity]
    if search_q:
        filtered = [l for l in filtered if _log_matches_search(l, search_q)]

    with count_col:
        st.caption(f"{len(filtered)} entr{'y' if len(filtered) == 1 else 'ies'}")

    if not filtered:
        st.info("No activity logged yet. Actions like saving payroll, approving leave, or editing employees will appear here.")
        return

    for log in filtered:
        # Format timestamp in PH time
        ts_raw = log.get("created_at", "")
        try:
            dt = datetime.fromisoformat(ts_raw.replace("Z", "+00:00")).astimezone(_PH_TZ)
            ts = dt.strftime("%b %d, %Y %I:%M %p")
        except Exception:
            ts = ts_raw[:16]

        actor   = log.get("user_email") or "System"
        action  = log.get("action", "")
        etype   = _ENTITY_LABELS.get(log.get("entity_type", ""), log.get("entity_type", ""))
        elabel  = log.get("entity_label") or ""
        details = log.get("details") or {}

        badge_html = _action_badge(action)
        details_html = ""
        if details:
            parts = []
            for k, v in details.items():
                v_str = str(v)
                if " → " in v_str:
                    old_val, new_val = v_str.split(" → ", 1)
                    val_html = (
                        f'<span style="color:#dc2626">{old_val}</span>'
                        f'<span style="color:#9ca3af"> → </span>'
                        f'<span style="color:#16a34a">{new_val}</span>'
                    )
                else:
                    val_html = f'<span style="color:#374151">{v_str}</span>'
                parts.append(
                    f'<span style="color:#6b7280">{k}:</span> {val_html}'
                )
            items_html = '<span style="color:#d1d5db;margin:0 6px">|</span>'.join(parts)
            details_html = f'<div style="font-size:11px;margin-top:5px;display:flex;flex-wrap:wrap;gap:4px 0">{items_html}</div>'

        st.markdown(
            f'<div style="border:1px solid #e5e7eb;border-radius:8px;padding:10px 14px;margin-bottom:6px">'
            f'<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">'
            f'<span style="color:#9ca3af;font-size:11px;white-space:nowrap">{ts}</span>'
            f'{badge_html}'
            f'<span style="font-size:13px;color:#374151"><strong>{etype}</strong> — {elabel}</span>'
            f'<span style="margin-left:auto;font-size:11px;color:#9ca3af;white-space:nowrap">{actor}</span>'
            f'</div>{details_html}</div>',
            unsafe_allow_html=True,
        )


def render():
    st.title("Company Setup")

    # Show confirmation after save
    if st.session_state.pop("company_saved", False):
        st.success("Company settings saved successfully.")

    company = _load_company()

    if not company:
        st.error("No company found. Please contact your administrator.")
        return

    tab_settings, tab_templates, tab_log = st.tabs([
        "⚙️ Company Settings",
        "🏖 Leave Templates",
        "📋 Activity Log",
    ])

    with tab_settings:
        st.caption("Configure your company details. These appear on payslips and government reports.")

        # ── Main company settings form ──────────────────────────────────────
        with st.form("company_setup_form"):

            # --- Company Information ---
            st.subheader("Company Information")
            col1, col2 = st.columns(2)

            with col1:
                name = st.text_input("Company Name *", value=company.get("name", ""))
            with col2:
                region_index = REGIONS.index(company.get("region", "NCR")) if company.get("region", "NCR") in REGIONS else 0
                region = st.selectbox(
                    "Region *",
                    options=REGIONS,
                    index=region_index,
                    help="Affects minimum wage computation",
                )

            address = st.text_area("Company Address", value=company.get("address", "") or "", height=80)

            freq_index = PAY_FREQUENCIES.index(company.get("pay_frequency", "semi-monthly"))
            pay_frequency = st.selectbox(
                "Pay Frequency",
                options=PAY_FREQUENCIES,
                index=freq_index,
                help="How often employees are paid",
            )

            # --- Government Registration Numbers ---
            st.subheader("Government Registration Numbers")
            st.caption("These are used in government remittance reports.")

            col1, col2 = st.columns(2)
            with col1:
                bir_tin = st.text_input("BIR TIN", value=company.get("bir_tin", "") or "")
                sss_no = st.text_input("SSS Employer No.", value=company.get("sss_employer_no", "") or "")
            with col2:
                philhealth_no = st.text_input("PhilHealth Employer No.", value=company.get("philhealth_employer_no", "") or "")
                pagibig_no = st.text_input("Pag-IBIG Employer No.", value=company.get("pagibig_employer_no", "") or "")

            # --- Leave Policy ---
            st.subheader("Leave Policy")
            st.caption(
                "Set when leave balances reset. "
                "To configure how many VL/SL/CL days each group of employees gets, "
                "use the **Leave Templates** tab."
            )

            replenishment_opts = {
                "annual":      "Annual — resets every January 1",
                "anniversary": "Anniversary — resets on each employee's hire date",
            }
            current_rep = company.get("leave_replenishment", "annual")
            rep_idx = list(replenishment_opts.keys()).index(current_rep) if current_rep in replenishment_opts else 0
            leave_replenishment = st.selectbox(
                "Leave Balance Replenishment Policy",
                options=list(replenishment_opts.keys()),
                format_func=lambda k: replenishment_opts[k],
                index=rep_idx,
                help=(
                    "Annual: all employees' leave balances reset to full on 1 January each year.\n"
                    "Anniversary: each employee's leave resets on their own hire anniversary."
                ),
            )

            # --- Submit ---
            submitted = st.form_submit_button("Save Company Settings", type="primary", use_container_width=True)

            if submitted:
                if not name.strip():
                    st.error("Company name is required.")
                else:
                    try:
                        _update_company({
                            "name": name.strip(),
                            "address": address.strip(),
                            "region": region,
                            "pay_frequency": pay_frequency,
                            "bir_tin": bir_tin.strip(),
                            "sss_employer_no": sss_no.strip(),
                            "philhealth_employer_no": philhealth_no.strip(),
                            "pagibig_employer_no": pagibig_no.strip(),
                            "leave_replenishment": leave_replenishment,
                        })
                        log_action("updated", "company", get_company_id(), name.strip())
                        st.session_state.company_saved = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error saving: {e}")

    with tab_templates:
        _render_template_section()

    with tab_log:
        _render_activity_log_tab()
