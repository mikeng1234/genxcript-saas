"""
Employee Master File — Streamlit page.

Features:
- View all employees in a table (from Supabase)
- Add a new employee via a form
- Edit an existing employee
- Deactivate / reactivate employees
- Onboarding checklist — flags missing government IDs and bank account
"""

import streamlit as st
import datetime
from datetime import date
from app.db_helper import get_db, get_company_id


# ============================================================
# Constants for dropdown options
# ============================================================

EMPLOYMENT_TYPES = ["regular", "probationary", "contractual"]
SALARY_TYPES = ["monthly", "daily", "hourly"]
TAX_STATUSES = ["S", "ME", "S1", "S2", "S3", "ME1", "ME2", "ME3", "ME4"]

TAX_STATUS_LABELS = {
    "S": "S — Single",
    "ME": "ME — Married",
    "S1": "S1 — Single w/ 1 dependent",
    "S2": "S2 — Single w/ 2 dependents",
    "S3": "S3 — Single w/ 3 dependents",
    "ME1": "ME1 — Married w/ 1 dependent",
    "ME2": "ME2 — Married w/ 2 dependents",
    "ME3": "ME3 — Married w/ 3 dependents",
    "ME4": "ME4 — Married w/ 4 dependents",
}

# Government ID fields to check for onboarding completeness
ONBOARDING_FIELDS = [
    ("sss_no",          "SSS No."),
    ("philhealth_no",   "PhilHealth No."),
    ("pagibig_no",      "Pag-IBIG No."),
    ("bir_tin",         "BIR TIN"),
    ("bank_account",    "Bank Account"),
]


# ============================================================
# Onboarding Checklist Helper
# ============================================================

def _onboarding_status(emp: dict) -> tuple[int, list[str]]:
    """
    Check how complete an employee's onboarding profile is.

    Returns:
        (completed_count, list_of_missing_field_labels)
    """
    missing = [label for field, label in ONBOARDING_FIELDS if not emp.get(field)]
    completed = len(ONBOARDING_FIELDS) - len(missing)
    return completed, missing


def _onboarding_badge(completed: int, total: int) -> str:
    """Return a colored markdown badge for the onboarding score."""
    if completed == total:
        return f":green[{completed}/{total} ✓]"
    elif completed >= total - 1:
        return f":orange[{completed}/{total}]"
    else:
        return f":red[{completed}/{total}]"


# ============================================================
# Database operations
# ============================================================

def _load_employees(show_inactive: bool = False) -> list[dict]:
    """Load employees from Supabase."""
    db = get_db()
    company_id = get_company_id()
    query = db.table("employees").select("*").eq("company_id", company_id)
    if not show_inactive:
        query = query.eq("is_active", True)
    result = query.order("last_name").execute()
    return result.data


def _create_employee(data: dict) -> dict:
    """Insert a new employee into Supabase."""
    db = get_db()
    data["company_id"] = get_company_id()
    result = db.table("employees").insert(data).execute()
    return result.data[0]


def _update_employee(employee_id: str, data: dict) -> dict:
    """Update an employee in Supabase."""
    db = get_db()
    result = db.table("employees").update(data).eq("id", employee_id).execute()
    return result.data[0]


def _centavos_to_pesos(centavos: int) -> float:
    return centavos / 100


def _pesos_to_centavos(pesos: float) -> int:
    return int(round(pesos * 100))


def _load_leave_templates() -> list[dict]:
    """Load leave entitlement templates for the current company."""
    db = get_db()
    result = (
        db.table("leave_entitlement_templates")
        .select("id, name, min_service_months, max_service_months, vl_days, sl_days, cl_days")
        .eq("company_id", get_company_id())
        .order("min_service_months")
        .execute()
    )
    return result.data or []


def _template_label(tmpl: dict) -> str:
    """Return a display label for a leave template."""
    def _mo(m: int) -> str:
        if m % 12 == 0 and m > 0:
            y = m // 12
            return f"{y} yr{'s' if y != 1 else ''}"
        return f"{m} mo"

    min_mo = tmpl["min_service_months"]
    max_mo = tmpl.get("max_service_months")
    lo = _mo(min_mo) if min_mo > 0 else "Start"
    if max_mo is None:
        svc = f"{lo}+"
    else:
        svc = f"{lo} – {_mo(max_mo + 1)}"
    return (
        f"{tmpl['name']}  ({svc}) "
        f"· {tmpl['vl_days']} VL / {tmpl['sl_days']} SL / {tmpl['cl_days']} CL"
    )


# ============================================================
# Employee Form (shared by Add and Edit)
# ============================================================

def _employee_form(existing: dict | None = None, form_key: str = "add") -> dict | None:
    """
    Render an employee form. Returns the form data dict if submitted, else None.
    If `existing` is provided, fields are pre-filled for editing.
    """
    is_edit = existing is not None
    defaults = existing or {}

    # Load leave templates outside the form context (safe to call any time)
    leave_templates = _load_leave_templates()

    with st.form(key=f"employee_form_{form_key}", clear_on_submit=not is_edit):
        st.subheader("Employee Information" if not is_edit else f"Edit: {defaults.get('first_name', '')} {defaults.get('last_name', '')}")

        # --- Row 1: Name and employee number ---
        col1, col2, col3 = st.columns(3)
        with col1:
            first_name = st.text_input("First Name *", value=defaults.get("first_name", ""))
        with col2:
            last_name = st.text_input("Last Name *", value=defaults.get("last_name", ""))
        with col3:
            employee_no = st.text_input("Employee No. *", value=defaults.get("employee_no", ""))

        # --- Row 2: Position, type, date hired ---
        col1, col2, col3 = st.columns(3)
        with col1:
            position = st.text_input("Position", value=defaults.get("position", ""))
        with col2:
            emp_type_index = EMPLOYMENT_TYPES.index(defaults.get("employment_type", "regular"))
            employment_type = st.selectbox("Employment Type", EMPLOYMENT_TYPES, index=emp_type_index)
        with col3:
            default_date = defaults.get("date_hired", date.today().isoformat())
            if isinstance(default_date, str):
                default_date = date.fromisoformat(default_date)
            date_hired = st.date_input("Date Hired", value=default_date)

        # --- Row 3: Leave Entitlement Template ---
        if leave_templates:
            # Build option list: None = company default, then each template
            tmpl_ids   = [None] + [t["id"] for t in leave_templates]
            tmpl_labels = ["— No template (use company default: 15 VL / 15 SL / 5 CL) —"] + [
                _template_label(t) for t in leave_templates
            ]
            current_tid = defaults.get("leave_template_id")
            try:
                tmpl_idx = tmpl_ids.index(current_tid)
            except ValueError:
                tmpl_idx = 0

            selected_tmpl_label = st.selectbox(
                "Leave Entitlement Template",
                options=tmpl_labels,
                index=tmpl_idx,
                help=(
                    "Assign a leave tier to this employee. "
                    "This controls how many VL/SL/CL days they receive per year. "
                    "Create templates in Company Setup → Leave Entitlement Templates."
                ),
            )
            selected_tmpl_id = tmpl_ids[tmpl_labels.index(selected_tmpl_label)]
        else:
            st.info(
                "No leave templates configured yet. "
                "Go to **Company Setup → Leave Entitlement Templates** to create leave tiers.",
                icon="ℹ️",
            )
            selected_tmpl_id = defaults.get("leave_template_id")

        # --- Row 4: Salary ---
        col1, col2, col3 = st.columns(3)
        with col1:
            default_salary = _centavos_to_pesos(defaults.get("basic_salary", 0))
            basic_salary = st.number_input(
                "Basic Salary (₱) *",
                min_value=0.0,
                value=default_salary,
                step=500.0,
                format="%.2f",
            )
        with col2:
            sal_type_index = SALARY_TYPES.index(defaults.get("salary_type", "monthly"))
            salary_type = st.selectbox("Salary Type", SALARY_TYPES, index=sal_type_index)
        with col3:
            tax_index = TAX_STATUSES.index(defaults.get("tax_status", "S"))
            tax_status = st.selectbox(
                "Tax Status",
                options=TAX_STATUSES,
                index=tax_index,
                format_func=lambda x: TAX_STATUS_LABELS[x],
            )

        # --- Row 5: Government numbers ---
        st.markdown("**Government IDs**")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            sss_no = st.text_input("SSS No.", value=defaults.get("sss_no", "") or "")
        with col2:
            philhealth_no = st.text_input("PhilHealth No.", value=defaults.get("philhealth_no", "") or "")
        with col3:
            pagibig_no = st.text_input("Pag-IBIG No.", value=defaults.get("pagibig_no", "") or "")
        with col4:
            bir_tin = st.text_input("BIR TIN", value=defaults.get("bir_tin", "") or "")

        # --- Row 6: Bank account + email ---
        col1, col2 = st.columns(2)
        with col1:
            bank_account = st.text_input("Bank Account No.", value=defaults.get("bank_account", "") or "")
        with col2:
            email = st.text_input(
                "Employee Email (for self-service portal)",
                value=defaults.get("email", "") or "",
                placeholder="e.g. juan.delacruz@gmail.com",
                help="Used to send the employee a portal invite.",
            )

        # --- Submit ---
        submitted = st.form_submit_button(
            "Update Employee" if is_edit else "Add Employee",
            type="primary",
            width="stretch",
        )

        if submitted:
            if not first_name.strip():
                st.error("First name is required.")
                return None
            if not last_name.strip():
                st.error("Last name is required.")
                return None
            if not employee_no.strip():
                st.error("Employee number is required.")
                return None
            if basic_salary <= 0:
                st.error("Basic salary must be greater than zero.")
                return None

            return {
                "employee_no":       employee_no.strip(),
                "first_name":        first_name.strip(),
                "last_name":         last_name.strip(),
                "position":          position.strip(),
                "employment_type":   employment_type,
                "date_hired":        date_hired.isoformat(),
                "basic_salary":      _pesos_to_centavos(basic_salary),
                "salary_type":       salary_type,
                "tax_status":        tax_status,
                "sss_no":            sss_no.strip(),
                "philhealth_no":     philhealth_no.strip(),
                "pagibig_no":        pagibig_no.strip(),
                "bir_tin":           bir_tin.strip(),
                "bank_account":      bank_account.strip(),
                "email":             email.strip() or None,
                "leave_template_id": selected_tmpl_id,
            }

    return None


# ============================================================
# Leave / OT Approval — DB helpers
# ============================================================

def _count_pending_admin() -> tuple[int, int]:
    """Return (pending_leave_count, pending_ot_count) for this company."""
    db = get_db()
    cid = get_company_id()
    lr  = db.table("leave_requests").select("id", count="exact").eq("company_id", cid).eq("status", "pending").execute()
    otr = db.table("overtime_requests").select("id", count="exact").eq("company_id", cid).eq("status", "pending").execute()
    return (lr.count or 0), (otr.count or 0)


def _load_leave_requests_admin() -> list[dict]:
    db = get_db()
    return (
        db.table("leave_requests")
        .select("*, employees(first_name, last_name, employee_no)")
        .eq("company_id", get_company_id())
        .order("created_at", desc=True)
        .execute()
    ).data or []


def _load_ot_requests_admin() -> list[dict]:
    db = get_db()
    return (
        db.table("overtime_requests")
        .select("*, employees(first_name, last_name, employee_no)")
        .eq("company_id", get_company_id())
        .order("created_at", desc=True)
        .execute()
    ).data or []


def _review_leave_request(req_id: str, status: str, note: str):
    get_db().table("leave_requests").update({
        "status":      status,
        "admin_notes": note.strip() or None,
        "reviewed_by": st.session_state.get("user_id"),
        "reviewed_at": datetime.datetime.utcnow().isoformat() + "Z",
    }).eq("id", req_id).execute()


def _review_ot_request(req_id: str, status: str, note: str):
    get_db().table("overtime_requests").update({
        "status":      status,
        "admin_notes": note.strip() or None,
        "reviewed_by": st.session_state.get("user_id"),
        "reviewed_at": datetime.datetime.utcnow().isoformat() + "Z",
    }).eq("id", req_id).execute()


# ============================================================
# Leave / OT Approval — UI helpers
# ============================================================

_LEAVE_TYPE_LABELS   = {"VL": "Vacation Leave", "SL": "Sick Leave", "CL": "Casual / Emergency Leave"}
_APPR_STATUS_COLORS  = {"pending": "#f59e0b", "approved": "#16a34a", "rejected": "#dc2626"}


def _appr_badge(status: str) -> str:
    c = _APPR_STATUS_COLORS.get(status, "#94a3b8")
    return (
        f'<span style="background:{c};color:#fff;padding:2px 8px;border-radius:4px;'
        f'font-size:11px;font-weight:700;letter-spacing:.3px">{status.upper()}</span>'
    )


def _render_leave_request_row(req: dict):
    emp     = req.get("employees") or {}
    name    = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip() or "Unknown"
    emp_no  = emp.get("employee_no", "—")
    status  = req.get("status", "pending")
    lt      = req.get("leave_type", "—")
    lt_lbl  = _LEAVE_TYPE_LABELS.get(lt, lt)
    days    = float(req.get("days") or 0)
    start   = req.get("start_date", "—")
    end     = req.get("end_date",   "—")
    reason  = req.get("reason") or ""
    a_note  = req.get("admin_notes") or ""
    is_pend = status == "pending"

    border = "#f59e0b" if is_pend else ("#16a34a" if status == "approved" else "#dc2626")
    bg     = "#fffbeb" if is_pend else "#f9fafb"
    badge  = _appr_badge(status)

    note_html   = f'<br><span style="color:#6b7280;font-size:12px">Reason: {reason}</span>'     if reason  else ""
    review_html = f'<br><span style="color:#6b7280;font-size:12px">HR note: {a_note}</span>'   if a_note  else ""

    st.markdown(
        f'<div style="border:1px solid #e5e7eb;border-left:4px solid {border};'
        f'border-radius:8px;padding:12px 16px;margin-bottom:6px;background:{bg}">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">'
        f'<div><strong style="font-size:14px">{name}</strong>'
        f'<span style="font-size:12px;color:#6b7280;margin-left:8px">{emp_no}</span></div>'
        f'<div>{badge}</div></div>'
        f'<div style="font-size:13px;color:#374151">'
        f'<strong>{lt}</strong> — {lt_lbl}'
        f'&nbsp;·&nbsp; {start} – {end}'
        f'&nbsp;·&nbsp; <strong>{days:.1g} day{"s" if days != 1 else ""}</strong>'
        f'{note_html}{review_html}</div></div>',
        unsafe_allow_html=True,
    )

    if is_pend:
        nc, ac, rc = st.columns([3.5, 1, 1])
        note_key = f"note_lr_{req['id']}"
        with nc:
            st.text_input("Note", key=note_key, placeholder="Admin note (optional)", label_visibility="collapsed")
        with ac:
            if st.button("✓ Approve", key=f"ap_lr_{req['id']}", type="primary", use_container_width=True):
                _review_leave_request(req["id"], "approved", st.session_state.get(note_key, ""))
                st.session_state["_review_toast"] = ("success", f"Leave request for **{name}** approved.")
                st.rerun()
        with rc:
            if st.button("✗ Reject", key=f"rej_lr_{req['id']}", use_container_width=True):
                _review_leave_request(req["id"], "rejected", st.session_state.get(note_key, ""))
                st.session_state["_review_toast"] = ("error", f"Leave request for **{name}** rejected.")
                st.rerun()


def _render_ot_request_row(req: dict):
    emp     = req.get("employees") or {}
    name    = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip() or "Unknown"
    emp_no  = emp.get("employee_no", "—")
    status  = req.get("status", "pending")
    hours   = float(req.get("hours") or 0)
    ot_date = req.get("ot_date", "—")
    start_t = req.get("start_time", "—")
    end_t   = req.get("end_time",   "—")
    reason  = req.get("reason") or ""
    a_note  = req.get("admin_notes") or ""
    is_pend = status == "pending"

    border = "#f59e0b" if is_pend else ("#16a34a" if status == "approved" else "#dc2626")
    bg     = "#fffbeb" if is_pend else "#f9fafb"
    badge  = _appr_badge(status)

    note_html   = f'<br><span style="color:#6b7280;font-size:12px">Reason: {reason}</span>'   if reason else ""
    review_html = f'<br><span style="color:#6b7280;font-size:12px">HR note: {a_note}</span>' if a_note else ""

    st.markdown(
        f'<div style="border:1px solid #e5e7eb;border-left:4px solid {border};'
        f'border-radius:8px;padding:12px 16px;margin-bottom:6px;background:{bg}">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">'
        f'<div><strong style="font-size:14px">{name}</strong>'
        f'<span style="font-size:12px;color:#6b7280;margin-left:8px">{emp_no}</span></div>'
        f'<div>{badge}</div></div>'
        f'<div style="font-size:13px;color:#374151">'
        f'Overtime &nbsp;·&nbsp; {ot_date} &nbsp;·&nbsp; {start_t}–{end_t}'
        f'&nbsp;·&nbsp; <strong>{hours:.1g} hr{"s" if hours != 1 else ""}</strong>'
        f'{note_html}{review_html}</div></div>',
        unsafe_allow_html=True,
    )

    if is_pend:
        nc, ac, rc = st.columns([3.5, 1, 1])
        note_key = f"note_ot_{req['id']}"
        with nc:
            st.text_input("Note", key=note_key, placeholder="Admin note (optional)", label_visibility="collapsed")
        with ac:
            if st.button("✓ Approve", key=f"ap_ot_{req['id']}", type="primary", use_container_width=True):
                _review_ot_request(req["id"], "approved", st.session_state.get(note_key, ""))
                st.session_state["_review_toast"] = ("success", f"OT request for **{name}** approved.")
                st.rerun()
        with rc:
            if st.button("✗ Reject", key=f"rej_ot_{req['id']}", use_container_width=True):
                _review_ot_request(req["id"], "rejected", st.session_state.get(note_key, ""))
                st.session_state["_review_toast"] = ("error", f"OT request for **{name}** rejected.")
                st.rerun()


# ============================================================
# Leave / OT Approval — Tab renderer
# ============================================================

def _render_approvals_tab():
    # Pending counts (already fetched for tab label, but we need full lists here)
    all_lr  = _load_leave_requests_admin()
    all_ot  = _load_ot_requests_admin()

    pending_lr   = [r for r in all_lr  if r["status"] == "pending"]
    resolved_lr  = [r for r in all_lr  if r["status"] != "pending"]
    pending_ot   = [r for r in all_ot  if r["status"] == "pending"]
    resolved_ot  = [r for r in all_ot  if r["status"] != "pending"]

    total_pending = len(pending_lr) + len(pending_ot)

    if total_pending == 0:
        st.success("All caught up — no pending leave or OT requests.", icon="✅")
    else:
        st.info(
            f"**{total_pending} pending request{'s' if total_pending != 1 else ''}** — "
            f"{len(pending_lr)} leave · {len(pending_ot)} overtime",
            icon="📋",
        )

    lr_label = f"🏖 Leave Requests ({len(pending_lr)} pending)" if pending_lr else "🏖 Leave Requests"
    ot_label = f"⏰ OT Requests ({len(pending_ot)} pending)"    if pending_ot else "⏰ OT Requests"

    lr_tab, ot_tab = st.tabs([lr_label, ot_label])

    with lr_tab:
        if not all_lr:
            st.caption("No leave requests have been filed yet.")
        else:
            if pending_lr:
                st.markdown("**Pending — action required**")
                for req in pending_lr:
                    _render_leave_request_row(req)
                if resolved_lr:
                    st.divider()
            if resolved_lr:
                with st.expander(f"History ({len(resolved_lr)} resolved)", expanded=False):
                    for req in resolved_lr[:50]:
                        _render_leave_request_row(req)
            if not pending_lr:
                st.caption("No pending leave requests.")

    with ot_tab:
        if not all_ot:
            st.caption("No overtime requests have been filed yet.")
        else:
            if pending_ot:
                st.markdown("**Pending — action required**")
                for req in pending_ot:
                    _render_ot_request_row(req)
                if resolved_ot:
                    st.divider()
            if resolved_ot:
                with st.expander(f"History ({len(resolved_ot)} resolved)", expanded=False):
                    for req in resolved_ot[:50]:
                        _render_ot_request_row(req)
            if not pending_ot:
                st.caption("No pending OT requests.")


# ============================================================
# Main Page Render
# ============================================================

def _render_employees_tab():
    # --- Top action bar ---
    col_search, col_filter, col_incomplete, col_add = st.columns([3, 1.5, 1.5, 1])

    with col_search:
        search = st.text_input("Search employees", placeholder="Type a name or employee number...")

    with col_filter:
        show_inactive = st.checkbox("Show inactive")

    with col_incomplete:
        show_incomplete_only = st.checkbox("Incomplete IDs only")

    with col_add:
        st.write("")
        st.write("")
        add_clicked = st.button("+ Add Employee", type="primary", width="stretch")

    # --- Add Employee Form ---
    if add_clicked:
        st.session_state.show_add_form = True

    if st.session_state.get("show_add_form"):
        st.divider()
        new_data = _employee_form(form_key="add_new")
        if new_data is not None:
            try:
                _create_employee(new_data)
                st.session_state.show_add_form = False
                st.success(f"Added {new_data['first_name']} {new_data['last_name']}")
                st.rerun()
            except Exception as e:
                error_msg = str(e)
                if "duplicate" in error_msg.lower() or "unique" in error_msg.lower():
                    st.error(f"Employee number {new_data['employee_no']} already exists.")
                else:
                    st.error(f"Error adding employee: {error_msg}")

    # --- Load employees ---
    employees = _load_employees(show_inactive=show_inactive)

    # --- Onboarding summary banner ---
    if employees:
        incomplete = [e for e in employees if _onboarding_status(e)[0] < len(ONBOARDING_FIELDS)]
        if incomplete:
            names = ", ".join(
                f"{e['first_name']} {e['last_name']}" for e in incomplete[:3]
            )
            more = f" and {len(incomplete) - 3} more" if len(incomplete) > 3 else ""
            st.warning(
                f"**{len(incomplete)} employee{'s' if len(incomplete) > 1 else ''} have incomplete government IDs:** "
                f"{names}{more}. Edit their profiles to add the missing details.",
                icon="⚠️",
            )

    # --- Search filter ---
    filtered = employees
    if search:
        search_lower = search.lower()
        filtered = [
            e for e in filtered
            if search_lower in e["first_name"].lower()
            or search_lower in e["last_name"].lower()
            or search_lower in e["employee_no"].lower()
        ]

    # --- Incomplete only filter ---
    if show_incomplete_only:
        filtered = [e for e in filtered if _onboarding_status(e)[0] < len(ONBOARDING_FIELDS)]

    # --- Employee Table ---
    st.divider()

    if not filtered:
        if show_incomplete_only:
            st.success("All employees have complete government ID profiles.")
        else:
            st.info("No employees found. Click '+ Add Employee' to get started.")
        return

    total = len(ONBOARDING_FIELDS)
    st.caption(f"Showing {len(filtered)} employee{'s' if len(filtered) != 1 else ''}")

    # Table header
    cols = st.columns([1, 2, 2, 2, 1.5, 1, 1, 2])
    for col, header in zip(cols, ["No.", "Name", "Position", "Salary", "Type", "IDs", "Status", "Actions"]):
        col.markdown(f"**{header}**")

    # Table rows
    for emp in filtered:
        completed, missing = _onboarding_status(emp)
        cols = st.columns([1, 2, 2, 2, 1.5, 1, 1, 2])

        with cols[0]:
            st.text(emp["employee_no"])
        with cols[1]:
            name_display = f"{emp['last_name']}, {emp['first_name']}"
            portal_status = " 🔗" if emp.get("user_id") else ""
            st.text(name_display + portal_status)
        with cols[2]:
            st.text(emp.get("position", "—") or "—")
        with cols[3]:
            salary_display = f"₱{_centavos_to_pesos(emp['basic_salary']):,.2f}/{emp['salary_type'][:2]}"
            st.text(salary_display)
        with cols[4]:
            st.text(emp["employment_type"].title())
        with cols[5]:
            badge = _onboarding_badge(completed, total)
            if missing:
                st.markdown(badge, help=f"Missing: {', '.join(missing)}")
            else:
                st.markdown(badge)
        with cols[6]:
            if emp.get("is_active", True):
                st.markdown(":green[Active]")
            else:
                st.markdown(":red[Inactive]")
        with cols[7]:
            btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
            with btn_col1:
                if st.button("Edit", key=f"edit_{emp['id']}", width="stretch"):
                    st.session_state.editing_id = emp["id"]
            with btn_col2:
                # Invite button logic:
                #   No email set      → show dash (can't invite)
                #   Email set, no uid → show "Invite" (first-time invite)
                #   Email set, uid    → show "Re-send" (re-link / resend flow)
                if not emp.get("email"):
                    st.markdown("—", help="Add email to enable invite")
                elif not emp.get("user_id"):
                    if st.button("Invite", key=f"invite_{emp['id']}", width="stretch",
                                 help=f"Send portal invite to {emp['email']}"):
                        st.session_state[f"invite_confirm_{emp['id']}"] = True
                else:
                    if st.button("Re-send", key=f"invite_{emp['id']}", width="stretch",
                                 help=f"Re-send or re-link portal access for {emp['email']}"):
                        st.session_state[f"invite_confirm_{emp['id']}"] = True
            with btn_col3:
                # Reset password — only if employee has a linked account
                if emp.get("email") and emp.get("user_id"):
                    if st.button("Pwd ↺", key=f"resetpwd_{emp['id']}", width="stretch",
                                 help=f"Send password reset email to {emp['email']}"):
                        from app.auth import send_password_reset
                        ok, err = send_password_reset(emp["email"])
                        if ok:
                            st.session_state["_invite_toast"] = (
                                "success",
                                f"Password reset email sent to **{emp['email']}**.",
                            )
                        else:
                            st.session_state["_invite_toast"] = ("error", err)
                        st.rerun()
                else:
                    st.markdown("—", help="Link portal account first")
            with btn_col4:
                if emp.get("is_active", True):
                    if st.button("Off", key=f"deact_{emp['id']}", width="stretch"):
                        _update_employee(emp["id"], {"is_active": False})
                        st.rerun()
                else:
                    if st.button("On", key=f"react_{emp['id']}", width="stretch"):
                        _update_employee(emp["id"], {"is_active": True})
                        st.rerun()

        # Invite / Re-send confirmation
        if st.session_state.get(f"invite_confirm_{emp['id']}"):
            already_linked = bool(emp.get("user_id"))
            action_label   = "Re-send / Re-link portal access" if already_linked else "Send portal invite"
            st.info(f"{action_label} for **{emp['email']}**?")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Yes, Confirm", key=f"inv_yes_{emp['id']}", type="primary"):
                    from app.auth import invite_employee
                    from app.db_helper import get_db, get_company_id
                    ok, result = invite_employee(emp["email"])
                    if ok:
                        # result may be "user_id|SMTP_FAILED|temp_pass|err_msg"
                        # when SMTP is not configured — parse it out
                        smtp_failed   = False
                        temp_password = None
                        smtp_err      = ""
                        if "|SMTP_FAILED|" in result:
                            parts         = result.split("|SMTP_FAILED|", 1)
                            auth_user_id  = parts[0]
                            rest          = parts[1].split("|", 1)
                            temp_password = rest[0]
                            smtp_err      = rest[1] if len(rest) > 1 else ""
                            smtp_failed   = True
                        else:
                            auth_user_id = result

                        db = get_db()
                        # Update employee record with auth user ID
                        db.table("employees").update({"user_id": auth_user_id}).eq("id", emp["id"]).execute()
                        # Upsert user_company_access — handles both new and existing rows
                        try:
                            db.table("user_company_access").upsert({
                                "user_id":    auth_user_id,
                                "company_id": get_company_id(),
                                "role":       "employee",
                            }, on_conflict="user_id,company_id").execute()
                        except Exception:
                            try:
                                db.table("user_company_access").insert({
                                    "user_id":    auth_user_id,
                                    "company_id": get_company_id(),
                                    "role":       "employee",
                                }).execute()
                            except Exception:
                                pass

                        if smtp_failed:
                            # SMTP not configured — show the temp password to admin
                            toast_msg = (
                                f"✅ Account created for **{emp['email']}**.\n\n"
                                f"⚠️ Email could not be sent ({smtp_err}).\n\n"
                                f"**Share this temporary password manually:**\n\n"
                                f"```\n{temp_password}\n```\n\n"
                                "Tell the employee to log in and use **Forgot Password** to change it."
                            )
                            st.session_state["_invite_toast"] = ("warning", toast_msg)
                        else:
                            action = "re-linked" if already_linked else "created"
                            toast_msg = (
                                f"✅ Portal access {action} for **{emp['email']}**. "
                                "A temporary password was emailed — they should check their inbox and log in."
                            )
                            st.session_state["_invite_toast"] = ("success", toast_msg)
                    else:
                        st.session_state["_invite_toast"] = ("error", result)
                    st.session_state[f"invite_confirm_{emp['id']}"] = False
                    st.rerun()
            with c2:
                if st.button("Cancel", key=f"inv_no_{emp['id']}"):
                    st.session_state[f"invite_confirm_{emp['id']}"] = False
                    st.rerun()

        # --- Edit form ---
        if st.session_state.get("editing_id") == emp["id"]:
            updated = _employee_form(existing=emp, form_key=f"edit_{emp['id']}")
            if updated is not None:
                try:
                    _update_employee(emp["id"], updated)
                    st.session_state.editing_id = None
                    st.success(f"Updated {updated['first_name']} {updated['last_name']}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error updating employee: {e}")

            if st.button("Cancel Edit", key=f"cancel_{emp['id']}"):
                st.session_state.editing_id = None
                st.rerun()

            st.divider()


# ============================================================
# Page entry point
# ============================================================

def render():
    st.title("Employee Master File")

    # ── Page-level toasts (shown above tabs so they're always visible) ─────────
    for toast_key in ("_invite_toast", "_review_toast"):
        if toast_key in st.session_state:
            kind, msg = st.session_state.pop(toast_key)
            if kind == "success":
                st.success(msg)
            elif kind == "warning":
                st.warning(msg)
            else:
                st.error(msg)

    # ── Pending count for tab label badge ─────────────────────────────────────
    pending_lr, pending_ot = _count_pending_admin()
    pending_total = pending_lr + pending_ot
    approvals_label = (
        f"📋 Leave & OT Approvals  · {pending_total} pending"
        if pending_total else "📋 Leave & OT Approvals"
    )

    tab_emp, tab_approvals = st.tabs(["👥 Employees", approvals_label])

    with tab_emp:
        _render_employees_tab()

    with tab_approvals:
        _render_approvals_tab()
