"""
Company Setup — Streamlit page.

One-time onboarding and settings:
- Company name, address, region
- BIR TIN, SSS/PhilHealth/Pag-IBIG employer numbers
- Pay frequency + leave replenishment policy
- Leave Entitlement Templates (named tiers, assignable per employee)
- Holiday Calendar (national PH holidays + company-specific custom entries)
"""

import streamlit as st
from datetime import date, datetime, timezone, timedelta
from app.db_helper import get_db, get_company_id, log_action
from app.styles import inject_css


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
# Database operations — Holidays
# ============================================================

_HOLIDAY_TYPE_LABELS = {
    "regular":             "Regular Holiday",
    "special_non_working": "Special Non-Working",
    "special_working":     "Special Working",
}

_HOLIDAY_TYPE_COLORS = {
    "regular":             ("#991b1b", "#fee2e2"),   # red
    "special_non_working": ("#92400e", "#fef3c7"),   # amber
    "special_working":     ("#065f46", "#d1fae5"),   # green
}


def _load_holidays(year: int) -> list[dict]:
    """Load national (company_id IS NULL) + company-specific holidays for a year."""
    db  = get_db()
    cid = get_company_id()
    result = (
        db.table("holidays")
        .select("*")
        .eq("year", year)
        .or_(f"company_id.is.null,company_id.eq.{cid}")
        .order("holiday_date")
        .execute()
    )
    return result.data or []


def _add_custom_holiday(data: dict) -> dict:
    db = get_db()
    data["company_id"] = get_company_id()
    result = db.table("holidays").insert(data).execute()
    return result.data[0]


def _delete_custom_holiday(holiday_id: str):
    db = get_db()
    db.table("holidays").delete().eq("id", holiday_id).execute()


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

        # ── Year-End Policy ───────────────────────────────────────────────────
        st.markdown("**Year-End Policy**")
        st.caption(
            "What happens to unused leave days at year-end. "
            "Carry-over and cash conversion are applied when HR runs the year-end processing action (Phase 5). "
            "DOLE note: Service Incentive Leave (SIL) unused days are legally convertible to cash."
        )
        p1, p2, p3 = st.columns(3)
        with p1:
            carry_over_cap = st.number_input(
                "Carry-Over Cap (days)",
                min_value=0, max_value=60,
                value=int(d.get("carry_over_cap", 0)),
                step=1,
                help=(
                    "Maximum unused days (per leave type) that roll over to next year. "
                    "0 = no carry-over. Applies to VL, SL, and CL."
                ),
            )
        with p2:
            convertible_to_cash = st.checkbox(
                "Convert unused to cash",
                value=bool(d.get("convertible_to_cash", False)),
                help=(
                    "Unused days beyond the carry-over cap are paid out as salary. "
                    "Applies at year-end processing."
                ),
            )
        with p3:
            conversion_rate = st.number_input(
                "Conversion Rate (× daily rate)",
                min_value=0.10, max_value=2.00,
                value=float(d.get("conversion_rate", 1.00)),
                step=0.10,
                format="%.2f",
                help=(
                    "1.00 = 1 unused day = 1 day's basic pay. "
                    "Ignored when 'Convert unused to cash' is off."
                ),
            )

        submitted = st.form_submit_button(submit_label, type="primary", width='stretch')

    if submitted:
        if not name.strip():
            st.error("Template name is required.")
            return None
        if max_mo != 0 and max_mo < min_mo:
            st.error("Max. service must be ≥ Min. service (or 0 for no upper limit).")
            return None
        return {
            "name":                name.strip(),
            "min_service_months":  int(min_mo),
            "max_service_months":  None if max_mo == 0 else int(max_mo),
            "vl_days":             int(vl),
            "sl_days":             int(sl),
            "cl_days":             int(cl),
            "carry_over_cap":      int(carry_over_cap),
            "convertible_to_cash": bool(convertible_to_cash),
            "conversion_rate":     float(conversion_rate),
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
    hdr = st.columns([2.5, 2, 1, 1, 1, 2.5, 1.8])
    for col, lbl in zip(hdr, ["Name", "Service Range", "VL", "SL", "CL", "Year-End Policy", "Actions"]):
        col.markdown(f"**{lbl}**")

    for tmpl in templates:
        row = st.columns([2.5, 2, 1, 1, 1, 2.5, 1.8])
        row[0].text(tmpl["name"])
        row[1].text(_service_range_label(tmpl["min_service_months"], tmpl["max_service_months"]))
        row[2].text(str(tmpl["vl_days"]))
        row[3].text(str(tmpl["sl_days"]))
        row[4].text(str(tmpl["cl_days"]))

        # Policy summary
        co_cap = int(tmpl.get("carry_over_cap", 0) or 0)
        convertible = bool(tmpl.get("convertible_to_cash", False))
        rate = float(tmpl.get("conversion_rate", 1.00) or 1.00)
        policy_parts = []
        if co_cap > 0:
            policy_parts.append(f"↪ {co_cap}d carry-over")
        if convertible:
            policy_parts.append(f"💵 cash ×{rate:.2f}")
        if not policy_parts:
            policy_parts.append("Forfeit unused")
        row[5].caption(" · ".join(policy_parts))

        act1, act2 = row[6].columns(2)
        with act1:
            if st.button("Edit", key=f"tmpl_edit_{tmpl['id']}", width='stretch'):
                # Toggle: if already editing this one, close it
                if st.session_state.get("editing_template_id") == tmpl["id"]:
                    st.session_state.editing_template_id = None
                else:
                    st.session_state.editing_template_id = tmpl["id"]
                    st.session_state.show_add_template = False
                st.rerun()
        with act2:
            if st.button("Del", key=f"tmpl_del_{tmpl['id']}", width='stretch',
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
    "holiday":          "Holiday",
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


def _holiday_type_badge(htype: str) -> str:
    fg, bg = _HOLIDAY_TYPE_COLORS.get(htype, ("#6b7280", "#f3f4f6"))
    label  = _HOLIDAY_TYPE_LABELS.get(htype, htype)
    return (
        f'<span style="background:{bg};color:{fg};padding:2px 9px;border-radius:12px;'
        f'font-size:11px;font-weight:700;letter-spacing:.3px;white-space:nowrap">'
        f'{label}</span>'
    )


def _render_holidays_tab():
    st.subheader("Holiday Calendar")
    st.caption(
        "Philippine national holidays are pre-loaded and updated annually. "
        "Add company-specific holidays below — local government holidays, company anniversary days, etc."
    )

    # ── Holiday pay multiplier reference ─────────────────────────────────────
    with st.expander("📊 DOLE Holiday Pay Multiplier Reference"):
        st.markdown(
            """
| Holiday Type | Not Worked | Worked (Basic) | Worked + OT |
|---|---|---|---|
| **Regular Holiday** | 100% of daily rate | **200%** of daily rate | **260%** (200% × 1.30) |
| **Special Non-Working** | No pay (no work, no pay) | **130%** of daily rate | **169%** (130% × 1.30) |
| **Special Working** | No premium | **130%** of daily rate | **169%** (130% × 1.30) |
| **Regular Holiday + Rest Day** | 100% | **260%** (200% × 1.30) | **338%** (260% × 1.30) |
| **Special Non-Working + Rest Day** | No pay | **150%** of daily rate | **195%** (150% × 1.30) |

*Source: DOLE Labor Advisory & Article 94, Labor Code of the Philippines.*
            """,
            unsafe_allow_html=False,
        )

    st.divider()

    # ── Year selector ─────────────────────────────────────────────────────────
    current_year = date.today().year
    year_col, _ = st.columns([1, 3])
    with year_col:
        year = st.selectbox(
            "Year",
            options=[current_year - 1, current_year, current_year + 1],
            index=1,
            label_visibility="collapsed",
            format_func=lambda y: f"📅  {y}",
        )

    holidays = _load_holidays(year)
    national = [h for h in holidays if not h.get("company_id")]
    custom   = [h for h in holidays if h.get("company_id")]

    # ── Add custom holiday ────────────────────────────────────────────────────
    add_col, _ = st.columns([1, 3])
    with add_col:
        if st.button("+ Add Company Holiday", key="hol_add_btn"):
            st.session_state.show_add_holiday = True

    if st.session_state.get("show_add_holiday"):
        st.markdown("**New Company Holiday**")
        with st.form("add_holiday_form", clear_on_submit=True):
            fc1, fc2, fc3 = st.columns([2, 2, 2])
            with fc1:
                hol_date = st.date_input(
                    "Date *",
                    value=date(year, 1, 1),
                    min_value=date(year, 1, 1),
                    max_value=date(year, 12, 31),
                )
            with fc2:
                hol_name = st.text_input("Holiday Name *", placeholder="e.g. City Fiesta, Founding Anniversary")
            with fc3:
                hol_type = st.selectbox(
                    "Type *",
                    options=list(_HOLIDAY_TYPE_LABELS.keys()),
                    format_func=lambda k: _HOLIDAY_TYPE_LABELS[k],
                )
            sub_col, cancel_col, _ = st.columns([1, 1, 3])
            with sub_col:
                submitted = st.form_submit_button("Add Holiday", type="primary", width='stretch')
            with cancel_col:
                cancelled = st.form_submit_button("Cancel", width='stretch')

        if cancelled:
            st.session_state.show_add_holiday = False
            st.rerun()

        if submitted:
            if not hol_name.strip():
                st.error("Holiday name is required.")
            else:
                try:
                    result = _add_custom_holiday({
                        "holiday_date": hol_date.isoformat(),
                        "name":         hol_name.strip(),
                        "type":         hol_type,
                        "year":         year,
                    })
                    log_action("created", "holiday", result["id"], hol_name.strip())
                    st.session_state.show_add_holiday = False
                    st.success(f"**{hol_name.strip()}** added for {year}.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding holiday: {e}")

    st.divider()

    # ── Company-specific holidays ─────────────────────────────────────────────
    if custom:
        st.markdown(f"**Company Holidays — {year}** *(editable)*")
        hdr = st.columns([1.5, 3, 2.5, 1])
        for col, lbl in zip(hdr, ["Date", "Name", "Type", ""]):
            col.markdown(f"<span style='font-size:12px;color:#6b7280;font-weight:600'>{lbl}</span>",
                         unsafe_allow_html=True)

        for h in custom:
            row = st.columns([1.5, 3, 2.5, 1])
            try:
                d = datetime.strptime(h["holiday_date"], "%Y-%m-%d").date()
                row[0].markdown(
                    f"<span style='font-size:13px'>{d.strftime('%b %d')}</span>",
                    unsafe_allow_html=True,
                )
            except Exception:
                row[0].text(h["holiday_date"])
            row[1].text(h["name"])
            row[2].markdown(_holiday_type_badge(h["type"]), unsafe_allow_html=True)
            with row[3]:
                if st.button("🗑", key=f"hol_del_{h['id']}", help="Delete this holiday"):
                    st.session_state[f"hol_del_confirm_{h['id']}"] = True
                    st.rerun()

            if st.session_state.get(f"hol_del_confirm_{h['id']}"):
                st.warning(f"Delete **{h['name']}**?")
                dc1, dc2, _ = st.columns([1, 1, 4])
                with dc1:
                    if st.button("Confirm", key=f"hol_del_yes_{h['id']}", type="primary"):
                        try:
                            _delete_custom_holiday(h["id"])
                            log_action("deleted", "holiday", h["id"], h["name"])
                            st.session_state.pop(f"hol_del_confirm_{h['id']}", None)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                with dc2:
                    if st.button("Cancel", key=f"hol_del_no_{h['id']}"):
                        st.session_state.pop(f"hol_del_confirm_{h['id']}", None)
                        st.rerun()
        st.divider()
    else:
        st.caption(f"No company-specific holidays added for {year}. Click **+ Add Company Holiday** to add one.")

    # ── National holidays (read-only) ─────────────────────────────────────────
    st.markdown(f"**National Holidays — {year}** *(read-only, PH Proclamation)*")
    if not national:
        st.info(f"No national holidays loaded for {year}. Run migration 004 to seed PH holidays.")
        return

    hdr2 = st.columns([1.5, 4, 2.5])
    for col, lbl in zip(hdr2, ["Date", "Name", "Type"]):
        col.markdown(f"<span style='font-size:12px;color:#6b7280;font-weight:600'>{lbl}</span>",
                     unsafe_allow_html=True)

    for h in national:
        row = st.columns([1.5, 4, 2.5])
        try:
            d = datetime.strptime(h["holiday_date"], "%Y-%m-%d").date()
            row[0].markdown(
                f"<span style='font-size:13px'>{d.strftime('%b %d')}</span>",
                unsafe_allow_html=True,
            )
        except Exception:
            row[0].text(h["holiday_date"])
        row[1].text(h["name"])
        row[2].markdown(_holiday_type_badge(h["type"]), unsafe_allow_html=True)


# ============================================================
# Database operations — Schedules
# ============================================================

_DAYS_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_DAYS_LABEL = {
    "Mon": "Monday", "Tue": "Tuesday", "Wed": "Wednesday",
    "Thu": "Thursday", "Fri": "Friday", "Sat": "Saturday", "Sun": "Sunday",
}


def _load_schedules() -> list[dict]:
    return (
        get_db().table("schedules")
        .select("*")
        .eq("company_id", get_company_id())
        .order("name")
        .execute()
    ).data or []


def _create_schedule(data: dict) -> dict:
    data["company_id"] = get_company_id()
    result = get_db().table("schedules").insert(data).execute()
    return result.data[0]


def _update_schedule(sched_id: str, data: dict) -> dict:
    result = (
        get_db().table("schedules")
        .update(data)
        .eq("id", sched_id)
        .execute()
    )
    return result.data[0]


def _delete_schedule(sched_id: str):
    get_db().table("schedules").delete().eq("id", sched_id).execute()


def _hours_per_day(start: str, end: str, break_min: int, overnight: bool) -> float:
    """Compute net hours worked per day from shift times."""
    from datetime import datetime as _dt
    fmt = "%H:%M"
    try:
        s = _dt.strptime(start, fmt)
        e = _dt.strptime(end, fmt)
        diff = (e - s).total_seconds() / 3600
        if overnight or diff <= 0:
            diff += 24
        return max(0.0, diff - break_min / 60)
    except Exception:
        return 0.0


def _schedule_form(
    form_key: str,
    defaults: dict | None = None,
    submit_label: str = "Save Schedule",
) -> dict | None:
    """Render add/edit form for a shift schedule. Returns data dict on submit."""
    d = defaults or {}

    raw_days = d.get("work_days", ["Mon", "Tue", "Wed", "Thu", "Fri"])
    if isinstance(raw_days, str):
        raw_days = [x.strip().strip('"') for x in raw_days.strip("{}").split(",")]
    existing_days = set(raw_days)

    with st.form(form_key, clear_on_submit=(defaults is None)):
        n1, _ = st.columns([3, 1])
        with n1:
            name = st.text_input(
                "Schedule Name *",
                value=d.get("name", ""),
                placeholder="e.g. Regular 8–5, Night Shift, Field Work",
            )

        st.markdown("**Shift Hours**")
        t1, t2, t3 = st.columns(3)
        with t1:
            raw_start = d.get("start_time", "08:00")
            if isinstance(raw_start, str):
                raw_start = raw_start[:5]
            from datetime import time as _time
            try:
                sh, sm = map(int, raw_start.split(":"))
            except Exception:
                sh, sm = 8, 0
            start_time = st.time_input("Start Time", value=_time(sh, sm), step=1800)
        with t2:
            raw_end = d.get("end_time", "17:00")
            if isinstance(raw_end, str):
                raw_end = raw_end[:5]
            try:
                eh, em = map(int, raw_end.split(":"))
            except Exception:
                eh, em = 17, 0
            end_time = st.time_input("End Time", value=_time(eh, em), step=1800)
        with t3:
            break_minutes = st.number_input(
                "Break (minutes)",
                min_value=0, max_value=240,
                value=int(d.get("break_minutes", 60)),
                step=15,
                help="Unpaid break deducted from hours worked.",
            )

        is_overnight = st.checkbox(
            "Overnight shift (crosses midnight — e.g. 10 PM → 6 AM)",
            value=bool(d.get("is_overnight", False)),
            help="Check this if end time is on the next calendar day.",
        )

        st.markdown("**Working Days**")
        day_cols = st.columns(7)
        selected_days = []
        for col, day in zip(day_cols, _DAYS_ORDER):
            if col.checkbox(day, value=(day in existing_days), key=f"{form_key}_day_{day}"):
                selected_days.append(day)

        submitted = st.form_submit_button(submit_label, type="primary", width="stretch")

    if submitted:
        if not name.strip():
            st.error("Schedule name is required.")
            return None
        if not selected_days:
            st.error("Select at least one working day.")
            return None
        net_hrs = _hours_per_day(
            start_time.strftime("%H:%M"),
            end_time.strftime("%H:%M"),
            int(break_minutes),
            bool(is_overnight),
        )
        if net_hrs <= 0:
            st.error("Net hours must be > 0. Check start/end times and break.")
            return None
        return {
            "name":          name.strip(),
            "start_time":    start_time.strftime("%H:%M"),
            "end_time":      end_time.strftime("%H:%M"),
            "break_minutes": int(break_minutes),
            "is_overnight":  bool(is_overnight),
            "work_days":     selected_days,
        }
    return None


def _render_schedules_tab():
    st.subheader("Shift Schedule Profiles")
    st.caption(
        "Define your company's shift schedules (e.g. Regular 8–5, Night Shift). "
        "Assign one to each employee so the DTR engine knows their expected working hours. "
        "Employees without an assigned schedule will be treated as unscheduled."
    )

    add_col, _ = st.columns([1, 3])
    with add_col:
        if st.button("+ Add Schedule", key="sched_add_btn"):
            st.session_state.show_add_schedule = True

    if st.session_state.get("show_add_schedule"):
        st.markdown("**New Schedule**")
        new_data = _schedule_form("add_schedule_form", submit_label="Add Schedule")
        if new_data is not None:
            try:
                result = _create_schedule(new_data)
                log_action("created", "schedule", result["id"], new_data["name"])
                st.session_state.show_add_schedule = False
                st.success(f"Schedule **{new_data['name']}** added.")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
        cancel_col, _ = st.columns([1, 4])
        with cancel_col:
            if st.button("Cancel", key="sched_add_cancel"):
                st.session_state.show_add_schedule = False
                st.rerun()

    schedules = _load_schedules()

    if not schedules:
        st.info("No schedules defined yet. Click **+ Add Schedule** to create your first shift profile.")
        return

    hdr = st.columns([2.5, 1.5, 1.5, 1, 2.5, 1.8])
    for col, lbl in zip(hdr, ["Name", "Net Hrs/Day", "Times", "Break", "Working Days", "Actions"]):
        col.markdown(f"**{lbl}**")

    for sched in schedules:
        row = st.columns([2.5, 1.5, 1.5, 1, 2.5, 1.8])
        net_hrs = _hours_per_day(
            sched.get("start_time", "")[:5],
            sched.get("end_time", "")[:5],
            int(sched.get("break_minutes", 60)),
            bool(sched.get("is_overnight", False)),
        )
        overnight_tag = " 🌙" if sched.get("is_overnight") else ""
        raw_days = sched.get("work_days", [])
        if isinstance(raw_days, str):
            raw_days = [x.strip().strip('"') for x in raw_days.strip("{}").split(",")]
        days_str = " · ".join(raw_days) if raw_days else "—"

        row[0].text(sched["name"] + overnight_tag)
        row[1].text(f"{net_hrs:.1f} hrs")
        row[2].text(f"{sched.get('start_time','')[:5]} – {sched.get('end_time','')[:5]}")
        row[3].text(f"{sched.get('break_minutes', 60)} min")
        row[4].caption(days_str)

        act1, act2 = row[5].columns(2)
        with act1:
            if st.button("Edit", key=f"sched_edit_{sched['id']}", width="stretch"):
                if st.session_state.get("editing_schedule_id") == sched["id"]:
                    st.session_state.editing_schedule_id = None
                else:
                    st.session_state.editing_schedule_id = sched["id"]
                    st.session_state.show_add_schedule = False
                st.rerun()
        with act2:
            if st.button("Del", key=f"sched_del_{sched['id']}", width="stretch",
                         help="Employees assigned to this schedule will become unscheduled."):
                st.session_state[f"sched_del_confirm_{sched['id']}"] = True
                st.rerun()

        if st.session_state.get(f"sched_del_confirm_{sched['id']}"):
            st.warning(f"Delete **{sched['name']}**? Assigned employees will become unscheduled.")
            dc1, dc2, _ = st.columns([1, 1, 3])
            with dc1:
                if st.button("Confirm Delete", key=f"sched_del_yes_{sched['id']}", type="primary"):
                    try:
                        _delete_schedule(sched["id"])
                        log_action("deleted", "schedule", sched["id"], sched["name"])
                        st.session_state.pop(f"sched_del_confirm_{sched['id']}", None)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
            with dc2:
                if st.button("Cancel", key=f"sched_del_no_{sched['id']}"):
                    st.session_state.pop(f"sched_del_confirm_{sched['id']}", None)
                    st.rerun()

        if st.session_state.get("editing_schedule_id") == sched["id"]:
            st.markdown(f"**Editing: {sched['name']}**")
            updated = _schedule_form(
                f"edit_schedule_{sched['id']}",
                defaults=sched,
                submit_label="Save Changes",
            )
            if updated is not None:
                try:
                    _update_schedule(sched["id"], updated)
                    log_action("updated", "schedule", sched["id"], updated["name"])
                    st.session_state.editing_schedule_id = None
                    st.success(f"Schedule **{updated['name']}** updated.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            cancel2, _ = st.columns([1, 4])
            with cancel2:
                if st.button("Cancel Edit", key=f"sched_edit_cancel_{sched['id']}"):
                    st.session_state.editing_schedule_id = None
                    st.rerun()

        st.divider()


# ============================================================
# Main Page Render
# ============================================================


def render():
    inject_css()
    st.title("Company Setup")

    # Show confirmation after save
    if st.session_state.pop("company_saved", False):
        st.success("Company settings saved successfully.")

    company = _load_company()

    if not company:
        st.error("No company found. Please contact your administrator.")
        return

    tab_settings, tab_templates, tab_holidays, tab_schedules, tab_log = st.tabs([
        "⚙️ Company Settings",
        "🏖 Leave Templates",
        "📅 Holidays",
        "🕐 Schedules",
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
            submitted = st.form_submit_button("Save Company Settings", type="primary", width='stretch')

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

    with tab_holidays:
        _render_holidays_tab()

    with tab_schedules:
        _render_schedules_tab()

    with tab_log:
        _render_activity_log_tab()
