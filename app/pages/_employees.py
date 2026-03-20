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
from app.db_helper import get_db, get_company_id, log_action
from app.styles import inject_css


# ============================================================
# Constants for dropdown options
# ============================================================

EMPLOYMENT_TYPES = ["regular", "probationary", "contractual"]
SALARY_TYPES = ["monthly", "daily"]
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

# ── Personal profile helpers (shared with Edit Employee dialog) ──────────────

CIVIL_STATUSES = ["Single", "Married", "Widowed", "Separated", "Divorced"]
SEXES          = ["Male", "Female", "Prefer not to say"]

PROVINCES = [
    "Metro Manila", "Abra", "Agusan del Norte", "Agusan del Sur", "Aklan",
    "Albay", "Antique", "Apayao", "Aurora", "Basilan", "Bataan", "Batanes",
    "Batangas", "Benguet", "Biliran", "Bohol", "Bukidnon", "Bulacan",
    "Cagayan", "Camarines Norte", "Camarines Sur", "Camiguin", "Capiz",
    "Catanduanes", "Cavite", "Cebu", "Compostela Valley", "Cotabato",
    "Davao del Norte", "Davao del Sur", "Davao Occidental", "Davao Oriental",
    "Dinagat Islands", "Eastern Samar", "Guimaras", "Ifugao", "Ilocos Norte",
    "Ilocos Sur", "Iloilo", "Isabela", "Kalinga", "La Union", "Laguna",
    "Lanao del Norte", "Lanao del Sur", "Leyte", "Maguindanao", "Marinduque",
    "Masbate", "Misamis Occidental", "Misamis Oriental", "Mountain Province",
    "Negros Occidental", "Negros Oriental", "Northern Samar", "Nueva Ecija",
    "Nueva Vizcaya", "Occidental Mindoro", "Oriental Mindoro", "Palawan",
    "Pampanga", "Pangasinan", "Quezon", "Quirino", "Rizal", "Romblon",
    "Samar", "Sarangani", "Shariff Kabunsuan", "Siquijor", "Sorsogon",
    "South Cotabato", "Southern Leyte", "Sultan Kudarat", "Sulu", "Surigao del Norte",
    "Surigao del Sur", "Tarlac", "Tawi-Tawi", "Zambales", "Zamboanga del Norte",
    "Zamboanga del Sur", "Zamboanga Sibugay",
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
        return f":green[{completed}/{total}]"
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


def _employee_diff(old: dict, new: dict, new_dept: str) -> dict:
    """Return {field_label: 'old → new'} for fields that changed."""
    TAX_LABELS = {"S": "Single", "ME": "Married", "ME1": "ME+1", "ME2": "ME+2", "ME3": "ME+3", "ME4": "ME+4"}
    changes = {}

    simple_fields = {
        "first_name":      "First Name",
        "last_name":       "Last Name",
        "position":        "Position",
        "employment_type": "Employment Type",
        "salary_type":     "Salary Type",
        "employee_no":     "Employee No.",
    }
    for field, label in simple_fields.items():
        o = str(old.get(field, "") or "").strip()
        n = str(new.get(field, "") or "").strip()
        if o.upper() != n.upper():
            changes[label] = f"{o or '—'} → {n or '—'}"

    # Tax status — show human label
    o_tax = old.get("tax_status", "") or ""
    n_tax = new.get("tax_status", "") or ""
    if o_tax != n_tax:
        changes["Tax Status"] = f"{TAX_LABELS.get(o_tax, o_tax) or '—'} → {TAX_LABELS.get(n_tax, n_tax) or '—'}"

    # Salary — centavos to pesos
    o_sal = old.get("basic_salary", 0) or 0
    n_sal = new.get("basic_salary", 0) or 0
    if o_sal != n_sal:
        changes["Salary"] = f"₱{o_sal/100:,.2f} → ₱{n_sal/100:,.2f}"

    # Department (stored separately, already .upper()'d)
    o_dept = (old.get("department", "") or "").strip().upper()
    n_dept = (new_dept or "").strip().upper()
    if o_dept != n_dept:
        changes["Department"] = f"{o_dept or '—'} → {n_dept or '—'}"

    # Dates — regularization and separation
    for field, label in (("regularization_date", "Regularization Date"), ("resignation_date", "Separation Date")):
        o = str(old.get(field) or "")
        n = str(new.get(field) or "")
        if o != n:
            changes[label] = f"{o or '—'} → {n or '—'}"

    return changes


def _upsert_employee_department(employee_id: str, department: str) -> None:
    """Upsert the department field in employee_profiles."""
    get_db().table("employee_profiles").upsert(
        {
            "employee_id": employee_id,
            "company_id":  get_company_id(),
            "department":  department.strip(),
        },
        on_conflict="employee_id",
    ).execute()


def _upsert_employee_profile_fields(employee_id: str, data: dict) -> None:
    """Upsert arbitrary extra fields into employee_profiles (Phase 3B+)."""
    payload = {
        "employee_id": employee_id,
        "company_id":  get_company_id(),
    }
    payload.update(data)
    get_db().table("employee_profiles").upsert(payload, on_conflict="employee_id").execute()


def _load_employee_profile(employee_id: str) -> dict:
    """Load the profile row for a single employee (returns {} if not found)."""
    result = (
        get_db().table("employee_profiles")
        .select("*")
        .eq("employee_id", employee_id)
        .execute()
    )
    return result.data[0] if result.data else {}


def _load_single_employee(emp_id: str) -> dict:
    """Load a single employee row by ID."""
    result = get_db().table("employees").select("*").eq("id", emp_id).single().execute()
    return result.data or {}


def _clear_dialog_state(emp_id: str) -> None:
    """Remove all edit-dialog session state keys for a given employee ID."""
    prefix_keys = [
        k for k in list(st.session_state.keys())
        if (k.startswith("d_") or k.startswith("_dp_")) and k.endswith(f"_{emp_id}")
    ]
    for k in prefix_keys:
        st.session_state.pop(k, None)


def _load_all_departments() -> dict:
    """Return {employee_id: department_str} for all employees in this company."""
    try:
        db  = get_db()
        cid = get_company_id()
        # Get employee_ids that belong to this company first
        emp_ids_res = (
            db.table("employees")
            .select("id")
            .eq("company_id", cid)
            .execute()
        )
        ids = [r["id"] for r in (emp_ids_res.data or [])]
        if not ids:
            return {}
        profiles = (
            db.table("employee_profiles")
            .select("employee_id, department")
            .in_("employee_id", ids)
            .execute()
        )
        return {
            p["employee_id"]: (p.get("department") or "")
            for p in (profiles.data or [])
        }
    except Exception:
        return {}


def _centavos_to_pesos(centavos: int) -> float:
    return centavos / 100


def _pesos_to_centavos(pesos: float) -> int:
    return int(round(pesos * 100))


def _load_all_employee_nos() -> list[str]:
    """Load all employee numbers (active + inactive) to avoid collisions."""
    db = get_db()
    result = (
        db.table("employees")
        .select("employee_no")
        .eq("company_id", get_company_id())
        .execute()
    )
    return [r["employee_no"] for r in result.data]


def _next_employee_no(existing_nos: list[str]) -> str:
    """Suggest next employee number by incrementing the highest numeric suffix found."""
    if not existing_nos:
        return "EMP-001"
    best_num = 0
    best_prefix = ""
    best_width = 3
    for no in existing_nos:
        stripped = no.rstrip("0123456789")
        digits = no[len(stripped):]
        if digits:
            try:
                n = int(digits)
                if n > best_num:
                    best_num = n
                    best_prefix = stripped
                    best_width = max(3, len(digits))
            except ValueError:
                pass
    if best_num > 0:
        return f"{best_prefix}{best_num + 1:0{best_width}d}"
    return "EMP-001"


def _load_distinct_positions() -> list[str]:
    """Load sorted unique non-empty positions from this company's employees."""
    db = get_db()
    result = (
        db.table("employees")
        .select("position")
        .eq("company_id", get_company_id())
        .execute()
    )
    seen: set[str] = set()
    positions: list[str] = []
    for r in result.data:
        p = (r.get("position") or "").strip().upper()
        if p and p not in seen:
            seen.add(p)
            positions.append(p)
    return sorted(positions)


def _load_department_names() -> list[str]:
    """Load department names from the departments table for filter use."""
    try:
        db = get_db()
        result = (
            db.table("departments")
            .select("name")
            .eq("company_id", get_company_id())
            .eq("is_active", True)
            .order("name")
            .execute()
        )
        names = [r["name"] for r in (result.data or [])]
        return names
    except Exception:
        return []


def _load_distinct_departments() -> list[str]:
    """Load sorted unique non-empty departments from employee_profiles for this company."""
    db = get_db()
    cid = get_company_id()
    emp_ids = [
        r["id"] for r in
        db.table("employees").select("id").eq("company_id", cid).execute().data
    ]
    if not emp_ids:
        return []
    result = db.table("employee_profiles").select("department").in_("employee_id", emp_ids).execute()
    seen: set[str] = set()
    departments: list[str] = []
    for r in result.data:
        d = (r.get("department") or "").strip().upper()
        if d and d not in seen:
            seen.add(d)
            departments.append(d)
    return sorted(departments)


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


def _load_schedules_for_form() -> list[dict]:
    """Load shift schedules for the schedule dropdown in the employee form."""
    return (
        get_db().table("schedules")
        .select("id, name, start_time, end_time, break_minutes, is_overnight")
        .eq("company_id", get_company_id())
        .order("name")
        .execute()
    ).data or []


def _schedule_label(sched: dict) -> str:
    """Return a display label for a shift schedule."""
    start = (sched.get("start_time") or "")[:5]
    end   = (sched.get("end_time")   or "")[:5]
    brk   = int(sched.get("break_minutes", 60))
    night = " (Overnight)" if sched.get("is_overnight") else ""
    return f"{sched['name']}  ({start} – {end}, {brk}min break){night}"


# ============================================================
# Employee Form (shared by Add and Edit)
# ============================================================

_NEW_POSITION_SENTINEL   = "— Add new position —"
_NEW_DEPT_SENTINEL       = "— Add new department —"


def _employee_form(existing: dict | None = None, form_key: str = "add") -> dict | None:
    """
    Render an employee form. Returns the form data dict if submitted, else None.
    If `existing` is provided, fields are pre-filled for editing.
    """
    is_edit = existing is not None
    defaults = existing or {}

    # Load helpers outside form (DB calls are fine here)
    leave_templates      = _load_leave_templates()
    schedules            = _load_schedules_for_form()
    distinct_positions   = _load_distinct_positions()
    distinct_departments = _load_distinct_departments()

    # Auto-suggest employee number only for new employees
    if not is_edit:
        all_nos = _load_all_employee_nos()
        suggested_no = _next_employee_no(all_nos)
    else:
        suggested_no = defaults.get("employee_no", "")

    # Resolve initial position selection
    current_position_raw = (defaults.get("position") or "").strip().upper()
    if current_position_raw in distinct_positions:
        pos_dropdown_idx = distinct_positions.index(current_position_raw)
        pos_new_default  = ""
    else:
        pos_dropdown_idx = len(distinct_positions)  # sentinel
        pos_new_default  = defaults.get("position", "") or ""

    position_options = distinct_positions + [_NEW_POSITION_SENTINEL]

    # Resolve initial department selection
    current_dept_raw = (defaults.get("department") or "").strip().upper()
    if current_dept_raw in distinct_departments:
        dept_dropdown_idx = distinct_departments.index(current_dept_raw)
        dept_new_default  = ""
    else:
        dept_dropdown_idx = len(distinct_departments)  # sentinel
        dept_new_default  = defaults.get("department", "") or ""

    dept_options = distinct_departments + [_NEW_DEPT_SENTINEL]

    # Session state keys — outside form for immediate reactivity
    pos_select_key  = f"_pos_select_{form_key}"
    pos_new_key     = f"_pos_new_{form_key}"
    dept_select_key = f"_dept_select_{form_key}"
    dept_new_key    = f"_dept_new_{form_key}"

    if pos_select_key not in st.session_state:
        st.session_state[pos_select_key]  = position_options[pos_dropdown_idx]
    if pos_new_key not in st.session_state:
        st.session_state[pos_new_key]     = pos_new_default
    if dept_select_key not in st.session_state:
        st.session_state[dept_select_key] = dept_options[dept_dropdown_idx]
    if dept_new_key not in st.session_state:
        st.session_state[dept_new_key]    = dept_new_default

    st.subheader("Employee Information" if not is_edit else f"Edit: {defaults.get('first_name', '')} {defaults.get('last_name', '')}")

    st.markdown(
        """<style>
        input[aria-label="New Position"],
        input[aria-label="New Department"],
        input[aria-label="Department"] { text-transform: uppercase; }
        </style>""",
        unsafe_allow_html=True,
    )

    # --- Position + Department selectors OUTSIDE the form (immediate reactivity) ---
    _pc1, _pc2, _pc3, _pc4 = st.columns(4)
    with _pc1:
        st.selectbox(
            "Position",
            options=position_options,
            key=pos_select_key,
            help="Select an existing job title or choose '— Add new position —' to type a new one.",
        )
        if st.session_state.get(pos_select_key) == _NEW_POSITION_SENTINEL:
            st.text_input(
                "New Position",
                key=pos_new_key,
                placeholder="e.g. ACCOUNTING STAFF",
                label_visibility="collapsed",
            )
    with _pc2:
        st.selectbox(
            "Department",
            options=dept_options,
            key=dept_select_key,
            help="Select an existing department or choose '— Add new department —' to type a new one.",
        )
        if st.session_state.get(dept_select_key) == _NEW_DEPT_SENTINEL:
            st.text_input(
                "New Department",
                key=dept_new_key,
                placeholder="e.g. FINANCE",
                label_visibility="collapsed",
            )

    with st.form(key=f"employee_form_{form_key}", clear_on_submit=not is_edit):
        # --- Row 1: Name and employee number ---
        col1, col2, col3 = st.columns(3)
        with col1:
            first_name = st.text_input("First Name *", value=defaults.get("first_name", ""))
        with col2:
            last_name = st.text_input("Last Name *", value=defaults.get("last_name", ""))
        with col3:
            employee_no = st.text_input(
                "Employee No. *",
                value=suggested_no,
                help="Auto-suggested based on existing numbers. You can change it." if not is_edit else None,
            )

        # --- Row 2: Employment Type, Date Hired ---
        col3, col4 = st.columns(2)
        with col3:
            emp_type_index = EMPLOYMENT_TYPES.index(defaults.get("employment_type", "regular"))
            employment_type = st.selectbox(
                "Employment Type",
                EMPLOYMENT_TYPES,
                index=emp_type_index,
                format_func=str.upper,
            )
        with col4:
            default_date = defaults.get("date_hired", date.today().isoformat())
            if isinstance(default_date, str):
                default_date = date.fromisoformat(default_date)
            date_hired = st.date_input("Date Hired", value=default_date)

        # --- Row 2b: Regularization Date | Separation Date ---
        _rr1, _rr2 = st.columns(2)
        with _rr1:
            _reg_raw = defaults.get("regularization_date")
            _reg_val = date.fromisoformat(_reg_raw) if isinstance(_reg_raw, str) and _reg_raw else None
            regularization_date = st.date_input(
                "Regularization Date",
                value=_reg_val,
                help="Date employee was regularized. Leave blank if not yet applicable.",
            )
        with _rr2:
            _res_raw = defaults.get("resignation_date")
            _res_val = date.fromisoformat(_res_raw) if isinstance(_res_raw, str) and _res_raw else None
            resignation_date = st.date_input(
                "Separation Date",
                value=_res_val,
                help="Date employee resigned, was terminated, or otherwise separated from service. Leave blank if still employed.",
            )

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

        # --- Row 3b: Shift Schedule ---
        if schedules:
            sched_ids    = [None] + [s["id"] for s in schedules]
            sched_labels = ["— No schedule assigned —"] + [_schedule_label(s) for s in schedules]
            current_sid  = defaults.get("schedule_id")
            try:
                sched_idx = sched_ids.index(current_sid)
            except ValueError:
                sched_idx = 0
            selected_sched_label = st.selectbox(
                "Shift Schedule",
                options=sched_labels,
                index=sched_idx,
                help=(
                    "Assign the employee's default working shift. "
                    "Used by the DTR engine to compute late, undertime, and absent. "
                    "Create schedules in Company Setup → Schedules."
                ),
            )
            selected_sched_id = sched_ids[sched_labels.index(selected_sched_label)]
        else:
            st.info(
                "No shift schedules configured yet. "
                "Go to **Company Setup → Schedules** to define shift profiles.",
                icon="ℹ️",
            )
            selected_sched_id = defaults.get("schedule_id")

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
            salary_type = st.selectbox("Salary Type", SALARY_TYPES, index=sal_type_index, format_func=str.upper)
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
            bank_account = st.text_input(
                "Disbursement Account No.",
                value=defaults.get("bank_account", "") or "",
                placeholder="Bank, GCash, Maya, or other account number",
            )
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

            # Resolve position from session state (widgets live outside the form)
            _pos_sel = st.session_state.get(pos_select_key, "")
            if _pos_sel == _NEW_POSITION_SENTINEL:
                resolved_position = st.session_state.get(pos_new_key, "").strip().upper()
            else:
                resolved_position = _pos_sel

            # Resolve department from session state
            _dept_sel = st.session_state.get(dept_select_key, "")
            if _dept_sel == _NEW_DEPT_SENTINEL:
                resolved_department = st.session_state.get(dept_new_key, "").strip().upper()
            else:
                resolved_department = _dept_sel

            # Clear outside-form session state for add mode so next open starts fresh
            if not is_edit:
                st.session_state.pop(pos_select_key,  None)
                st.session_state.pop(pos_new_key,     None)
                st.session_state.pop(dept_select_key, None)
                st.session_state.pop(dept_new_key,    None)

            return {
                "employee_no":        employee_no.strip(),
                "first_name":         first_name.strip(),
                "last_name":          last_name.strip(),
                "position":           resolved_position,
                "department":         resolved_department,
                "employment_type":    employment_type,
                "date_hired":         date_hired.isoformat(),
                # Phase 3B — stored in employees table
                "resignation_date":   resignation_date.isoformat() if resignation_date else None,
                # Phase 3B — stored in employee_profiles
                "regularization_date": regularization_date.isoformat() if regularization_date else None,
                "basic_salary":       _pesos_to_centavos(basic_salary),
                "salary_type":        salary_type,
                "tax_status":         tax_status,
                "sss_no":             sss_no.strip(),
                "philhealth_no":      philhealth_no.strip(),
                "pagibig_no":         pagibig_no.strip(),
                "bir_tin":            bir_tin.strip(),
                "bank_account":       bank_account.strip(),
                "email":              email.strip() or None,
                "leave_template_id":  selected_tmpl_id,
                "schedule_id":        selected_sched_id,
            }

    return None


# ============================================================
# Leave Balances Admin View — DB helpers
# ============================================================

def _load_company_leave_settings() -> dict:
    """Load leave entitlement defaults + replenishment policy from companies table."""
    result = (
        get_db().table("companies")
        .select("leave_vl_days, leave_sl_days, leave_cl_days, leave_replenishment")
        .eq("id", get_company_id())
        .single()
        .execute()
    )
    return result.data or {}


def _load_leave_templates_map() -> dict:
    """Return {template_id: {name, vl_days, sl_days, cl_days}} for all company templates."""
    result = (
        get_db().table("leave_entitlement_templates")
        .select("id, name, vl_days, sl_days, cl_days")
        .eq("company_id", get_company_id())
        .execute()
    )
    return {r["id"]: r for r in (result.data or [])}


def _load_employees_for_balance() -> list[dict]:
    """Active employees with leave template assignment and department."""
    employees = (
        get_db().table("employees")
        .select("id, first_name, last_name, employee_no, position, date_hired, leave_template_id")
        .eq("company_id", get_company_id())
        .eq("is_active", True)
        .order("last_name")
        .execute()
    ).data or []
    # Department lives in employee_profiles — merge it in
    dept_map = _load_all_departments()
    for emp in employees:
        emp["department"] = dept_map.get(emp["id"], "")
    return employees


def _load_leave_balance_overrides(year: int) -> dict:
    """
    Load leave_balance rows for the given year.
    Returns {(employee_id, leave_type): opening_balance}.
    When a row exists it REPLACES the template/default entitlement for that year
    (the stored value already includes template days + any carried-over days).
    """
    result = (
        get_db().table("leave_balance")
        .select("employee_id, leave_type, opening_balance")
        .eq("company_id", get_company_id())
        .eq("year", year)
        .execute()
    )
    return {
        (r["employee_id"], r["leave_type"]): float(r["opening_balance"])
        for r in (result.data or [])
    }


def _load_approved_leave_year(year: int) -> dict:
    """
    Load all approved leave_requests for the given calendar year.
    Returns {employee_id: {"VL": days, "SL": days, "CL": days}}.
    """
    start = date(year, 1, 1).isoformat()
    end   = date(year, 12, 31).isoformat()
    result = (
        get_db().table("leave_requests")
        .select("employee_id, leave_type, days")
        .eq("company_id", get_company_id())
        .eq("status", "approved")
        .gte("start_date", start)
        .lte("start_date", end)
        .execute()
    )
    usage: dict = {}
    for r in (result.data or []):
        eid = r["employee_id"]
        lt  = r.get("leave_type", "")
        if eid not in usage:
            usage[eid] = {"VL": 0.0, "SL": 0.0, "CL": 0.0}
        if lt in ("VL", "SL", "CL"):
            usage[eid][lt] += float(r.get("days") or 0)
    return usage


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
# Special Leave Admin — DB helpers
# ============================================================

def _load_special_leave_requests_admin() -> list[dict]:
    return (
        get_db().table("special_leave_requests")
        .select("*, employees(first_name, last_name, employee_no)")
        .eq("company_id", get_company_id())
        .order("created_at", desc=True)
        .execute()
    ).data or []


def _count_pending_special() -> int:
    r = (
        get_db().table("special_leave_requests")
        .select("id", count="exact")
        .eq("company_id", get_company_id())
        .eq("status", "pending")
        .execute()
    )
    return r.count or 0


def _review_special_leave(req_id: str, status: str, note: str):
    get_db().table("special_leave_requests").update({
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

# Special leave type metadata
_SL_TYPE_META = {
    "ML":  ("Maternity Leave",   "RA 11210", "#be185d", "#fdf2f8"),
    "PL":  ("Paternity Leave",   "RA 8187",  "#1d4ed8", "#eff6ff"),
    "SPL": ("Solo Parent Leave", "RA 8972",  "#7c3aed", "#f5f3ff"),
}
_SL_DELIVERY_LABELS = {
    "normal":                "Normal / Vaginal delivery (105 days)",
    "caesarean":             "Caesarean section (105 days)",
    "miscarriage":           "Miscarriage / Stillbirth (60 days)",
    "emergency_termination": "Emergency termination of pregnancy (60 days)",
}


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
            if st.button("Approve", key=f"ap_lr_{req['id']}", type="primary", width='stretch'):
                _review_leave_request(req["id"], "approved", st.session_state.get(note_key, ""))
                log_action("approved", "leave_request", req["id"], f"{name} - {lt_lbl}", {"dates": f"{start} to {end}"})
                st.session_state["_review_toast"] = ("success", f"Leave request for **{name}** approved.")
                st.rerun()
        with rc:
            if st.button("Reject", key=f"rej_lr_{req['id']}", width='stretch'):
                _review_leave_request(req["id"], "rejected", st.session_state.get(note_key, ""))
                log_action("rejected", "leave_request", req["id"], f"{name} - {lt_lbl}", {"dates": f"{start} to {end}"})
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
            if st.button("Approve", key=f"ap_ot_{req['id']}", type="primary", width='stretch'):
                _review_ot_request(req["id"], "approved", st.session_state.get(note_key, ""))
                log_action("approved", "overtime_request", req["id"], f"{name} - {ot_date}", {"hours": hours})
                st.session_state["_review_toast"] = ("success", f"OT request for **{name}** approved.")
                st.rerun()
        with rc:
            if st.button("Reject", key=f"rej_ot_{req['id']}", width='stretch'):
                _review_ot_request(req["id"], "rejected", st.session_state.get(note_key, ""))
                log_action("rejected", "overtime_request", req["id"], f"{name} - {ot_date}", {"hours": hours})
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
        st.success("All caught up — no pending leave or OT requests.", icon=":material/check_circle:")
    else:
        st.info(
            f"**{total_pending} pending request{'s' if total_pending != 1 else ''}** — "
            f"{len(pending_lr)} leave · {len(pending_ot)} overtime",
            icon=":material/assignment:",
        )

    lr_col, ot_col = st.columns(2)

    with lr_col:
        lr_badge = f" ({len(pending_lr)} pending)" if pending_lr else ""
        st.markdown(f"#### Leave Requests{lr_badge}")
        st.divider()
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

    with ot_col:
        ot_badge = f" ({len(pending_ot)} pending)" if pending_ot else ""
        st.markdown(f"#### OT Requests{ot_badge}")
        st.divider()
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
# Leave Balances Admin View — Render
# ============================================================

def _render_leave_balances_tab():
    import pandas as pd

    today    = date.today()
    cur_year = today.year

    yr_col, _ = st.columns([1, 5])
    with yr_col:
        year = st.selectbox(
            "Year",
            [cur_year - 1, cur_year, cur_year + 1],
            index=1,
            format_func=str,
            key="lb_year",
        )

    company   = _load_company_leave_settings()
    templates = _load_leave_templates_map()
    employees = _load_employees_for_balance()
    usage     = _load_approved_leave_year(year)
    overrides = _load_leave_balance_overrides(year)  # carry-over rows from year-end processing

    if not employees:
        st.info("No active employees found.")
        return

    # Company-wide defaults (fallback when no template is assigned)
    defaults = {
        "VL": int(company.get("leave_vl_days") or 15),
        "SL": int(company.get("leave_sl_days") or 15),
        "CL": int(company.get("leave_cl_days") or 5),
    }

    # ── Summary metrics ───────────────────────────────────────────────────────
    total_vl_used = sum(u.get("VL", 0) for u in usage.values())
    total_sl_used = sum(u.get("SL", 0) for u in usage.values())
    total_cl_used = sum(u.get("CL", 0) for u in usage.values())

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Active Employees", len(employees))
    m2.metric(f"VL Used ({year})", f"{total_vl_used:.1f} days")
    m3.metric(f"SL Used ({year})", f"{total_sl_used:.1f} days")
    m4.metric(f"CL Used ({year})", f"{total_cl_used:.1f} days")

    st.divider()

    # ── Filter controls ────────────────────────────────────────────────────────
    all_positions = sorted({(emp.get("position") or "").strip() for emp in employees} - {""})
    all_depts     = sorted({emp.get("department") or "" for emp in employees} - {""})
    # Load dept names from structured departments table (fall back to employee data)
    _dept_names_structured = _load_department_names()
    if _dept_names_structured:
        all_depts = _dept_names_structured

    lb_s, lb_p, lb_d = st.columns([2, 1.5, 1.5])
    with lb_s:
        lb_search = st.text_input("Search", placeholder="Name or employee no…",
                                  label_visibility="collapsed", key="lb_search")
    with lb_p:
        lb_sel_pos  = st.multiselect("Position",   all_positions, key="lb_f_pos",  placeholder="All positions")
    with lb_d:
        lb_sel_dept = st.multiselect("Department", all_depts,     key="lb_f_dept", placeholder="All departments")

    # ── Build rows ─────────────────────────────────────────────────────────────
    rows = []
    for emp in employees:
        eid     = emp["id"]
        tmpl_id = emp.get("leave_template_id")
        tmpl    = templates.get(tmpl_id) if tmpl_id else None
        dept    = emp.get("department") or "—"

        # Apply filters
        emp_name = f"{emp['last_name']}, {emp['first_name']}"
        if lb_search:
            q = lb_search.lower()
            if q not in emp_name.lower() and q not in (emp.get("employee_no") or "").lower():
                continue
        if lb_sel_pos  and (emp.get("position") or "") not in lb_sel_pos:
            continue
        if lb_sel_dept and dept not in lb_sel_dept:
            continue

        # Base entitlement from template or company defaults
        ent = {
            "VL": int(tmpl["vl_days"]) if tmpl else defaults["VL"],
            "SL": int(tmpl["sl_days"]) if tmpl else defaults["SL"],
            "CL": int(tmpl["cl_days"]) if tmpl else defaults["CL"],
        }
        # Override with leave_balance row if present (includes carry-over from prior year)
        has_override = False
        for lt in ("VL", "SL", "CL"):
            ob = overrides.get((eid, lt))
            if ob is not None:
                ent[lt] = ob
                has_override = True

        u = usage.get(eid, {"VL": 0.0, "SL": 0.0, "CL": 0.0})

        def _pct(used, total):
            return min(100.0, round(used / total * 100, 1)) if total > 0 else 0.0

        # Template label — suffix with ↪ if carry-over opening balance is active
        tmpl_label = (tmpl["name"] if tmpl else "Default") + (" ↪" if has_override else "")

        rows.append({
            "No.":      emp.get("employee_no", ""),
            "Employee": emp_name,
            "Position": emp.get("position") or "—",
            "Dept":     dept,
            "Template": tmpl_label,
            "VL Left":   max(0.0, ent["VL"] - u["VL"]),
            "VL Total":  ent["VL"],
            "VL Used":   round(float(u.get("VL", 0)), 1),
            "SL Left":   max(0.0, ent["SL"] - u["SL"]),
            "SL Total":  ent["SL"],
            "SL Used":   round(float(u.get("SL", 0)), 1),
            "CL Left":   max(0.0, ent["CL"] - u["CL"]),
            "CL Total":  ent["CL"],
            "CL Used":   round(float(u.get("CL", 0)), 1),
        })

    if not rows:
        st.info("No employees match the selected filter.")
        return

    df = pd.DataFrame(rows)

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "No.":      st.column_config.TextColumn("No.",      width="small"),
            "Employee": st.column_config.TextColumn("Employee", width="medium"),
            "Position": st.column_config.TextColumn("Position", width="small"),
            "Dept":     st.column_config.TextColumn("Dept",     width="small"),
            "Template": st.column_config.TextColumn("Template", width="small"),
            "VL Left":  st.column_config.NumberColumn("VL Rem",  format="%.0f", width="small"),
            "VL Total": st.column_config.NumberColumn("VL Total",format="%.0f", width="small"),
            "VL Used":  st.column_config.NumberColumn("VL Used", format="%.1f", width="small"),
            "SL Left":  st.column_config.NumberColumn("SL Rem",  format="%.0f", width="small"),
            "SL Total": st.column_config.NumberColumn("SL Total",format="%.0f", width="small"),
            "SL Used":  st.column_config.NumberColumn("SL Used", format="%.1f", width="small"),
            "CL Left":  st.column_config.NumberColumn("CL Rem",  format="%.0f", width="small"),
            "CL Total": st.column_config.NumberColumn("CL Total",format="%.0f", width="small"),
            "CL Used":  st.column_config.NumberColumn("CL Used", format="%.1f", width="small"),
        },
    )

    replenishment = company.get("leave_replenishment", "annual")
    policy_note = (
        "Annual policy — balances shown as approved leave taken Jan 1 – Dec 31."
        if replenishment == "annual"
        else "Anniversary policy — balances reflect the calendar year window above. "
             "Individual reset dates may vary by hire date."
    )
    st.caption(
        f"{policy_note} Entitlement is per assigned template or company defaults. "
        "↪ = opening balance includes carried-over days from the prior year."
    )


# ============================================================
# Special Leaves Admin — UI & Tab renderer
# ============================================================

def _sl_type_badge(lt: str) -> str:
    label, _, color, _ = _SL_TYPE_META.get(lt, (lt, "", "#6b7280", "#f3f4f6"))
    return (
        f'<span style="background:{color};color:#fff;padding:2px 8px;'
        f'border-radius:4px;font-size:11px;font-weight:700;">{lt}</span>'
    )


def _render_special_leave_row(req: dict):
    emp      = req.get("employees") or {}
    name     = f"{emp.get('first_name','')} {emp.get('last_name','')}".strip() or "Unknown"
    emp_no   = emp.get("employee_no", "—")
    status   = req.get("status", "pending")
    lt       = req.get("leave_type", "—")
    lt_label, ra_ref, _, _ = _SL_TYPE_META.get(lt, (lt, "", "#6b7280", "#f3f4f6"))
    days     = float(req.get("days") or 0)
    start    = req.get("start_date", "—")
    end      = req.get("end_date",   "—")
    reason   = req.get("reason")    or ""
    a_note   = req.get("admin_notes") or ""
    is_pend  = status == "pending"

    border = "#f59e0b" if is_pend else ("#16a34a" if status == "approved" else "#dc2626")
    bg     = "#fffbeb" if is_pend else "#f9fafb"
    badge  = _appr_badge(status)
    lt_bdg = _sl_type_badge(lt)

    # Build supporting detail line
    details = []
    if lt == "ML" and req.get("delivery_type"):
        details.append(_SL_DELIVERY_LABELS.get(req["delivery_type"], req["delivery_type"]))
    if lt == "PL" and req.get("partner_name"):
        details.append(f"Partner: {req['partner_name']}")
    if lt == "SPL" and req.get("solo_parent_id"):
        details.append(f"Solo Parent ID: {req['solo_parent_id']}")
    if req.get("delivery_date"):
        details.append(f"Delivery date: {req['delivery_date']}")
    if req.get("supporting_docs_note"):
        details.append(f"Docs: {req['supporting_docs_note']}")

    detail_html  = f'<br><span style="font-size:12px;color:#6b7280;">{" · ".join(details)}</span>' if details else ""
    reason_html  = f'<br><span style="font-size:12px;color:#6b7280;">Reason: {reason}</span>'   if reason  else ""
    anote_html   = f'<br><span style="font-size:12px;color:#6b7280;">HR note: {a_note}</span>'  if a_note  else ""

    st.markdown(
        f'<div style="border:1px solid #e5e7eb;border-left:4px solid {border};'
        f'border-radius:8px;padding:12px 16px;margin-bottom:6px;background:{bg}">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">'
        f'<div><strong style="font-size:14px">{name}</strong>'
        f'<span style="font-size:12px;color:#6b7280;margin-left:8px">{emp_no}</span></div>'
        f'<div style="display:flex;gap:6px;align-items:center">{lt_bdg}&nbsp;{badge}</div></div>'
        f'<div style="font-size:13px;color:#374151;">'
        f'<strong>{lt}</strong> — {lt_label} <span style="color:#9ca3af;font-size:11px">{ra_ref}</span>'
        f'&nbsp;·&nbsp; {start} – {end}'
        f'&nbsp;·&nbsp; <strong>{days:.0f} day{"s" if days != 1 else ""}</strong>'
        f'{detail_html}{reason_html}{anote_html}</div></div>',
        unsafe_allow_html=True,
    )

    if is_pend:
        nc, ac, rc = st.columns([3.5, 1, 1])
        note_key = f"note_slr_{req['id']}"
        with nc:
            st.text_input("Note", key=note_key, placeholder="Admin note (optional)",
                          label_visibility="collapsed")
        with ac:
            if st.button("Approve", key=f"ap_slr_{req['id']}", type="primary", width="stretch"):
                _review_special_leave(req["id"], "approved", st.session_state.get(note_key, ""))
                log_action("approved", "special_leave_request", req["id"],
                           f"{name} — {lt_label}", {"dates": f"{start} to {end}"})
                st.session_state["_review_toast"] = ("success", f"Special leave for **{name}** approved.")
                st.rerun()
        with rc:
            if st.button("Reject", key=f"rej_slr_{req['id']}", width="stretch"):
                _review_special_leave(req["id"], "rejected", st.session_state.get(note_key, ""))
                log_action("rejected", "special_leave_request", req["id"],
                           f"{name} — {lt_label}", {"dates": f"{start} to {end}"})
                st.session_state["_review_toast"] = ("error", f"Special leave for **{name}** rejected.")
                st.rerun()


def _render_special_leaves_tab():
    all_slr = _load_special_leave_requests_admin()

    # ── Summary metrics ───────────────────────────────────────────────────────
    pending_n = sum(1 for r in all_slr if r["status"] == "pending")
    ml_n      = sum(1 for r in all_slr if r["leave_type"] == "ML")
    pl_n      = sum(1 for r in all_slr if r["leave_type"] == "PL")
    spl_n     = sum(1 for r in all_slr if r["leave_type"] == "SPL")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Pending Review",    pending_n)
    m2.metric("Maternity (ML)",    ml_n)
    m3.metric("Paternity (PL)",    pl_n)
    m4.metric("Solo Parent (SPL)", spl_n)

    # ── PH law reference banner ───────────────────────────────────────────────
    st.info(
        "**ML** (RA 11210) — 105 days paid for normal/caesarean · 60 days for miscarriage &nbsp;|&nbsp; "
        "**PL** (RA 8187) — 7 days paid (first 4 deliveries of spouse) &nbsp;|&nbsp; "
        "**SPL** (RA 8972) — 7 days paid per year · requires DSWD Solo Parent ID",
        icon="⚖️",
    )

    st.divider()

    if not all_slr:
        st.info("No special leave requests have been filed yet.", icon=":material/info:")
        return

    # ── Filter row ────────────────────────────────────────────────────────────
    f1, f2, f3 = st.columns([2.5, 1.5, 1.5])
    with f1:
        slr_q  = st.text_input("Search", placeholder="Employee name or number…",
                               label_visibility="collapsed", key="slr_search")
    with f2:
        slr_lt = st.multiselect("Type",   ["ML", "PL", "SPL"],
                                key="slr_type_f", placeholder="All types")
    with f3:
        slr_st = st.multiselect("Status", ["pending", "approved", "rejected"],
                                key="slr_status_f", placeholder="All statuses")

    # Apply filters
    filtered = all_slr
    if slr_q:
        q = slr_q.lower()
        filtered = [
            r for r in filtered
            if q in (r.get("employees") or {}).get("first_name", "").lower()
            or q in (r.get("employees") or {}).get("last_name",  "").lower()
            or q in (r.get("employees") or {}).get("employee_no","").lower()
        ]
    if slr_lt:
        filtered = [r for r in filtered if r.get("leave_type") in slr_lt]
    if slr_st:
        filtered = [r for r in filtered if r.get("status")     in slr_st]

    f_pending  = [r for r in filtered if r["status"] == "pending"]
    f_resolved = [r for r in filtered if r["status"] != "pending"]

    if not filtered:
        st.info("No records match the selected filters.")
        return

    if f_pending:
        st.markdown(f"**Pending — {len(f_pending)} request{'s' if len(f_pending) != 1 else ''} awaiting review**")
        for req in f_pending:
            _render_special_leave_row(req)
        if f_resolved:
            st.divider()

    if f_resolved:
        with st.expander(f"History — {len(f_resolved)} resolved", expanded=(not f_pending)):
            for req in f_resolved[:80]:
                _render_special_leave_row(req)

    if not f_pending:
        st.success("All special leave requests are resolved.", icon=":material/check_circle:")


# ============================================================
# Edit Employee Dialog (popup — combines admin + portal fields)
# ============================================================

@st.dialog("Edit Employee", width="large")
def _edit_employee_dialog(emp_id: str):
    """
    Full-featured popup editor. Combines employment details (admin fields)
    and personal profile (portal fields) in one tabbed dialog.
    Saves both the `employees` table and `employee_profiles` in one submit.
    """
    # ── Load data ─────────────────────────────────────────────────────────────
    emp     = _load_single_employee(emp_id)
    profile = _load_employee_profile(emp_id)
    p       = profile or {}

    # Inject department from employee_profiles
    dept_lookup = _load_all_departments()
    emp["department"] = dept_lookup.get(emp_id, "")

    # ── Dropdown data ──────────────────────────────────────────────────────────
    distinct_positions   = _load_distinct_positions()
    distinct_departments = _load_distinct_departments()
    leave_templates      = _load_leave_templates()
    schedules            = _load_schedules_for_form()

    position_options = distinct_positions + [_NEW_POSITION_SENTINEL]
    dept_options     = distinct_departments + [_NEW_DEPT_SENTINEL]

    # Session-state keys for the outside-form position/dept widgets
    pos_key  = f"_dp_pos_{emp_id}"
    posn_key = f"_dp_posn_{emp_id}"
    dep_key  = f"_dp_dep_{emp_id}"
    depn_key = f"_dp_depn_{emp_id}"

    current_position_raw = (emp.get("position") or "").strip().upper()
    current_dept_raw     = (emp.get("department") or "").strip().upper()

    if pos_key not in st.session_state:
        if current_position_raw in distinct_positions:
            st.session_state[pos_key] = current_position_raw
        else:
            st.session_state[pos_key]  = _NEW_POSITION_SENTINEL
            st.session_state[posn_key] = emp.get("position", "")
    if dep_key not in st.session_state:
        if current_dept_raw in distinct_departments:
            st.session_state[dep_key] = current_dept_raw
        else:
            st.session_state[dep_key]  = _NEW_DEPT_SENTINEL
            st.session_state[depn_key] = emp.get("department", "")

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_emp, tab_profile_tab = st.tabs(["📋 Employment Details", "👤 Personal Profile"])

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 1 — Employment Details
    # ─────────────────────────────────────────────────────────────────────────
    with tab_emp:
        st.markdown("**Name & Employee Number**")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.text_input("First Name *", value=emp.get("first_name", ""), key=f"d_fn_{emp_id}")
        with c2:
            st.text_input("Last Name *",  value=emp.get("last_name", ""),  key=f"d_ln_{emp_id}")
        with c3:
            st.text_input("Employee No. *", value=emp.get("employee_no", ""), key=f"d_en_{emp_id}")

        st.markdown("**Employment**")
        c1, c2 = st.columns(2)
        with c1:
            et_idx = EMPLOYMENT_TYPES.index(emp.get("employment_type", "regular"))
            st.selectbox("Employment Type", EMPLOYMENT_TYPES, index=et_idx,
                         format_func=str.upper, key=f"d_et_{emp_id}")
        with c2:
            dh_raw = emp.get("date_hired", date.today().isoformat())
            if isinstance(dh_raw, str):
                dh_raw = date.fromisoformat(dh_raw)
            st.date_input("Date Hired", value=dh_raw, key=f"d_dh_{emp_id}")

        c1, c2 = st.columns(2)
        with c1:
            _reg_raw = p.get("regularization_date")
            _reg_val = date.fromisoformat(_reg_raw) if isinstance(_reg_raw, str) and _reg_raw else None
            st.date_input("Regularization Date", value=_reg_val, key=f"d_rd_{emp_id}",
                          help="Date employee was regularized. Leave blank if not yet applicable.")
        with c2:
            _res_raw = emp.get("resignation_date")
            _res_val = date.fromisoformat(_res_raw) if isinstance(_res_raw, str) and _res_raw else None
            st.date_input("Separation Date", value=_res_val, key=f"d_sd_{emp_id}",
                          help="Date resigned, terminated, or otherwise separated. Leave blank if still employed.")

        st.markdown("**Position & Department**")
        pc1, pc2 = st.columns(2)
        with pc1:
            st.selectbox("Position", options=position_options, key=pos_key)
            if st.session_state.get(pos_key) == _NEW_POSITION_SENTINEL:
                st.text_input("New Position", key=posn_key,
                              placeholder="e.g. ACCOUNTING STAFF",
                              label_visibility="collapsed")
        with pc2:
            st.selectbox("Department", options=dept_options, key=dep_key)
            if st.session_state.get(dep_key) == _NEW_DEPT_SENTINEL:
                st.text_input("New Department", key=depn_key,
                              placeholder="e.g. FINANCE",
                              label_visibility="collapsed")

        # Leave template
        if leave_templates:
            tmpl_ids    = [None] + [t["id"] for t in leave_templates]
            tmpl_labels = ["— No template (use company default) —"] + [_template_label(t) for t in leave_templates]
            current_tid = emp.get("leave_template_id")
            tmpl_idx    = tmpl_ids.index(current_tid) if current_tid in tmpl_ids else 0
            st.selectbox("Leave Entitlement Template", tmpl_labels, index=tmpl_idx, key=f"d_lt_{emp_id}")
        else:
            tmpl_ids    = [None]
            tmpl_labels = ["—"]
            st.info("No leave templates configured. Go to **Company Setup → Leave Entitlement Templates**.", icon="ℹ️")

        # Shift schedule
        if schedules:
            sched_ids    = [None] + [s["id"] for s in schedules]
            sched_labels = ["— No schedule assigned —"] + [_schedule_label(s) for s in schedules]
            current_sid  = emp.get("schedule_id")
            sched_idx    = sched_ids.index(current_sid) if current_sid in sched_ids else 0
            st.selectbox("Shift Schedule", sched_labels, index=sched_idx, key=f"d_sc_{emp_id}")
        else:
            sched_ids    = [None]
            sched_labels = ["—"]
            st.info("No schedules configured. Go to **Company Setup → Schedules**.", icon="ℹ️")

        st.markdown("**Compensation**")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.number_input("Basic Salary (₱) *",
                            min_value=0.0,
                            value=_centavos_to_pesos(emp.get("basic_salary", 0) or 0),
                            step=500.0, format="%.2f", key=f"d_bs_{emp_id}")
        with c2:
            sal_idx = SALARY_TYPES.index(emp.get("salary_type", "monthly"))
            st.selectbox("Salary Type", SALARY_TYPES, index=sal_idx,
                         format_func=str.upper, key=f"d_st_{emp_id}")
        with c3:
            tax_idx = TAX_STATUSES.index(emp.get("tax_status", "S"))
            st.selectbox("Tax Status", TAX_STATUSES, index=tax_idx,
                         format_func=lambda x: TAX_STATUS_LABELS[x], key=f"d_ts_{emp_id}")

        st.markdown("**Government IDs**")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.text_input("SSS No.",        value=emp.get("sss_no", "") or "",        key=f"d_sss_{emp_id}")
        with c2:
            st.text_input("PhilHealth No.", value=emp.get("philhealth_no", "") or "", key=f"d_ph_{emp_id}")
        with c3:
            st.text_input("Pag-IBIG No.",  value=emp.get("pagibig_no", "") or "",    key=f"d_pig_{emp_id}")
        with c4:
            st.text_input("BIR TIN",        value=emp.get("bir_tin", "") or "",       key=f"d_tin_{emp_id}")

        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Disbursement Account No.",
                          value=emp.get("bank_account", "") or "",
                          placeholder="Bank, GCash, Maya, or other account number",
                          key=f"d_ba_{emp_id}")
        with c2:
            st.text_input("Employee Email",
                          value=emp.get("email", "") or "",
                          placeholder="e.g. juan.delacruz@gmail.com",
                          key=f"d_em_{emp_id}",
                          help="Used to send the employee a portal invite.")

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 2 — Personal Profile
    # ─────────────────────────────────────────────────────────────────────────
    with tab_profile_tab:
        st.markdown("#### Personal Information")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.text_input("First Name",  value=emp.get("first_name", ""), disabled=True, key=f"d_pfn_{emp_id}")
        with c2:
            st.text_input("Middle Name", value=p.get("middle_name", "") or "", key=f"d_mn_{emp_id}")
        with c3:
            st.text_input("Last Name",   value=emp.get("last_name", ""),  disabled=True, key=f"d_pln_{emp_id}")

        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Suffix (Jr., Sr., III…)", value=p.get("suffix", "") or "", key=f"d_sx_{emp_id}")
        with c2:
            st.text_input("Mobile Number", value=p.get("mobile_no", "") or "",
                          placeholder="09XX-XXX-XXXX", key=f"d_mob_{emp_id}")

        c1, c2, c3 = st.columns(3)
        with c1:
            dob_val = p.get("date_of_birth")
            if isinstance(dob_val, str):
                dob_val = date.fromisoformat(dob_val)
            st.date_input("Date of Birth",
                          value=dob_val or date(1990, 1, 1),
                          min_value=date(1940, 1, 1),
                          max_value=date.today(),
                          key=f"d_dob_{emp_id}")
        with c2:
            st.text_input("Place of Birth", value=p.get("place_of_birth", "") or "", key=f"d_pob_{emp_id}")
        with c3:
            st.text_input("Nationality",
                          value=p.get("nationality", "Filipino") or "Filipino",
                          key=f"d_nat_{emp_id}")

        c1, c2, c3 = st.columns(3)
        with c1:
            sex_idx = SEXES.index(p["sex"]) if p.get("sex") in SEXES else 0
            st.selectbox("Sex", SEXES, index=sex_idx, key=f"d_sex_{emp_id}")
        with c2:
            cs_idx = CIVIL_STATUSES.index(p["civil_status"]) if p.get("civil_status") in CIVIL_STATUSES else 0
            st.selectbox("Civil Status", CIVIL_STATUSES, index=cs_idx, key=f"d_cs_{emp_id}")
        with c3:
            st.text_input("Religion", value=p.get("religion", "") or "", key=f"d_rel_{emp_id}")

        st.markdown("#### Additional IDs")
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("PhilSys / National ID No.", value=p.get("philsys_no", "") or "", key=f"d_psys_{emp_id}")
        with c2:
            st.text_input("UMID No.", value=p.get("umid_no", "") or "", key=f"d_umid_{emp_id}")

        st.markdown("#### Payment Details")
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Bank / E-wallet Name",
                          value=p.get("bank_name", "") or "",
                          placeholder="e.g. BDO, BPI, GCash, Maya",
                          key=f"d_bn_{emp_id}")
        with c2:
            st.text_input("Disbursement Account No. (HR)",
                          value=emp.get("bank_account", "") or "",
                          disabled=True, key=f"d_bahr_{emp_id}")

        st.markdown("#### Present Address")
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("House No. / Street / Subdivision",
                          value=p.get("present_address_street", "") or "",
                          key=f"d_pstr_{emp_id}")
        with c2:
            st.text_input("Barangay", value=p.get("present_address_barangay", "") or "", key=f"d_pbrgy_{emp_id}")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.text_input("City / Municipality", value=p.get("present_address_city", "") or "", key=f"d_pcity_{emp_id}")
        with c2:
            pprov_idx = (
                PROVINCES.index(p["present_address_province"])
                if p.get("present_address_province") in PROVINCES else 0
            )
            st.selectbox("Province", PROVINCES, index=pprov_idx, key=f"d_pprov_{emp_id}")
        with c3:
            st.text_input("ZIP Code", value=p.get("present_address_zip", "") or "", key=f"d_pzip_{emp_id}")

        st.markdown("#### Permanent Address")
        perm_same_val = bool(p.get("perm_address_same", True))
        st.checkbox("Same as present address", value=perm_same_val, key=f"d_psame_{emp_id}")
        if not st.session_state.get(f"d_psame_{emp_id}", True):
            c1, c2 = st.columns(2)
            with c1:
                st.text_input("House No. / Street / Subdivision",
                              value=p.get("perm_address_street", "") or "",
                              key=f"d_rmstr_{emp_id}")
            with c2:
                st.text_input("Barangay", value=p.get("perm_address_barangay", "") or "", key=f"d_rmbrgy_{emp_id}")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.text_input("City / Municipality",
                              value=p.get("perm_address_city", "") or "",
                              key=f"d_rmcity_{emp_id}")
            with c2:
                rprov_idx = (
                    PROVINCES.index(p["perm_address_province"])
                    if p.get("perm_address_province") in PROVINCES else 0
                )
                st.selectbox("Province", PROVINCES, index=rprov_idx, key=f"d_rmprov_{emp_id}")
            with c3:
                st.text_input("ZIP Code", value=p.get("perm_address_zip", "") or "", key=f"d_rmzip_{emp_id}")

        st.markdown("#### Emergency Contact")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.text_input("Full Name", value=p.get("emergency_name", "") or "", key=f"d_ecn_{emp_id}")
        with c2:
            st.text_input("Relationship",
                          value=p.get("emergency_relationship", "") or "",
                          placeholder="e.g. Spouse, Parent, Sibling",
                          key=f"d_ecr_{emp_id}")
        with c3:
            st.text_input("Contact Number", value=p.get("emergency_phone", "") or "", key=f"d_ecp_{emp_id}")
        st.text_input("Address", value=p.get("emergency_address", "") or "", key=f"d_eca_{emp_id}")

        # Spouse info — shown only when civil status is Married
        if st.session_state.get(f"d_cs_{emp_id}", p.get("civil_status", "")) == "Married":
            st.markdown("#### Spouse Information")
            c1, c2 = st.columns(2)
            with c1:
                st.text_input("Full Name",    value=p.get("spouse_name", "") or "",       key=f"d_spn_{emp_id}")
                st.text_input("Occupation",   value=p.get("spouse_occupation", "") or "",  key=f"d_spoc_{emp_id}")
            with c2:
                st.text_input("Employer",     value=p.get("spouse_employer", "") or "",    key=f"d_spem_{emp_id}")
                st.text_input("Contact No.",  value=p.get("spouse_contact", "") or "",     key=f"d_spct_{emp_id}")

        st.markdown("#### Additional Contact")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.text_input("Home Phone",    value=p.get("home_phone", "") or "",
                          placeholder="(02) 8123-4567",   key=f"d_hp_{emp_id}")
        with c2:
            st.text_input("Work Phone",    value=p.get("work_phone", "") or "",
                          placeholder="+63 2 1234 5678",  key=f"d_wp_{emp_id}")
        with c3:
            st.text_input("Personal Email", value=p.get("personal_email", "") or "",
                          placeholder="juan@gmail.com",   key=f"d_pe_{emp_id}")

        st.markdown("#### Educational Background")
        c1, c2, c3 = st.columns([3, 3, 1])
        with c1:
            st.text_input("Degree / Course",
                          value=p.get("education_degree", "") or "",
                          placeholder="e.g. BS Computer Science, BSBA",
                          key=f"d_edeg_{emp_id}")
        with c2:
            st.text_input("School / University",
                          value=p.get("education_school", "") or "",
                          placeholder="e.g. University of the Philippines",
                          key=f"d_esch_{emp_id}")
        with c3:
            _yr_raw = p.get("education_year")
            st.number_input("Year Graduated",
                            min_value=1950, max_value=2030,
                            value=int(_yr_raw) if _yr_raw else 2000,
                            step=1, key=f"d_eyr_{emp_id}")

        st.markdown("#### Social Links *(optional)*")
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Facebook", value=p.get("facebook", "") or "",
                          placeholder="Profile URL or username", key=f"d_fb_{emp_id}")
        with c2:
            st.text_input("LinkedIn", value=p.get("linkedin", "") or "",
                          placeholder="Profile URL or username", key=f"d_li_{emp_id}")

    # ── Save / Cancel ─────────────────────────────────────────────────────────
    st.divider()
    bc1, bc2 = st.columns(2)
    with bc1:
        save_clicked = st.button("💾 Save Changes", type="primary", width="stretch", key=f"d_save_{emp_id}")
    with bc2:
        if st.button("Cancel", width="stretch", key=f"d_cancel_{emp_id}"):
            st.session_state.pop("editing_id", None)
            _clear_dialog_state(emp_id)
            st.rerun()

    if save_clicked:
        ss = st.session_state

        # Basic validation
        if not (ss.get(f"d_fn_{emp_id}") or "").strip():
            st.error("First name is required.")
            return
        if not (ss.get(f"d_ln_{emp_id}") or "").strip():
            st.error("Last name is required.")
            return
        if not (ss.get(f"d_en_{emp_id}") or "").strip():
            st.error("Employee number is required.")
            return
        if (ss.get(f"d_bs_{emp_id}") or 0) <= 0:
            st.error("Basic salary must be greater than zero.")
            return

        # Resolve position
        pos_sel = ss.get(pos_key, "")
        resolved_position = (
            (ss.get(posn_key, "") or "").strip().upper()
            if pos_sel == _NEW_POSITION_SENTINEL
            else pos_sel
        )

        # Resolve department
        dep_sel = ss.get(dep_key, "")
        resolved_department = (
            (ss.get(depn_key, "") or "").strip().upper()
            if dep_sel == _NEW_DEPT_SENTINEL
            else dep_sel
        )

        # Resolve leave template
        lt_label = ss.get(f"d_lt_{emp_id}")
        resolved_tmpl_id = (
            tmpl_ids[tmpl_labels.index(lt_label)]
            if lt_label and lt_label in tmpl_labels
            else emp.get("leave_template_id")
        )

        # Resolve schedule
        sc_label = ss.get(f"d_sc_{emp_id}")
        resolved_sched_id = (
            sched_ids[sched_labels.index(sc_label)]
            if sc_label and sc_label in sched_labels
            else emp.get("schedule_id")
        )

        # ── Build employees table payload ──────────────────────────────────────
        sep_date = ss.get(f"d_sd_{emp_id}")
        dh_val   = ss.get(f"d_dh_{emp_id}", date.today())
        emp_data = {
            "employee_no":     (ss.get(f"d_en_{emp_id}") or "").strip(),
            "first_name":      (ss.get(f"d_fn_{emp_id}") or "").strip(),
            "last_name":       (ss.get(f"d_ln_{emp_id}") or "").strip(),
            "position":        resolved_position,
            "employment_type": ss.get(f"d_et_{emp_id}", "regular"),
            "date_hired":      dh_val.isoformat() if hasattr(dh_val, "isoformat") else str(dh_val),
            "resignation_date": sep_date.isoformat() if sep_date else None,
            "basic_salary":    _pesos_to_centavos(ss.get(f"d_bs_{emp_id}") or 0),
            "salary_type":     ss.get(f"d_st_{emp_id}", "monthly"),
            "tax_status":      ss.get(f"d_ts_{emp_id}", "S"),
            "sss_no":          (ss.get(f"d_sss_{emp_id}") or "").strip(),
            "philhealth_no":   (ss.get(f"d_ph_{emp_id}") or "").strip(),
            "pagibig_no":      (ss.get(f"d_pig_{emp_id}") or "").strip(),
            "bir_tin":         (ss.get(f"d_tin_{emp_id}") or "").strip(),
            "bank_account":    (ss.get(f"d_ba_{emp_id}") or "").strip(),
            "email":           (ss.get(f"d_em_{emp_id}") or "").strip() or None,
            "leave_template_id": resolved_tmpl_id,
            "schedule_id":     resolved_sched_id,
        }

        # ── Build employee_profiles table payload ──────────────────────────────
        perm_same       = ss.get(f"d_psame_{emp_id}", True)
        reg_date        = ss.get(f"d_rd_{emp_id}")
        civil_stat_val  = ss.get(f"d_cs_{emp_id}", "Single")
        dob_val2        = ss.get(f"d_dob_{emp_id}", date(1990, 1, 1))
        eyr_val         = ss.get(f"d_eyr_{emp_id}")

        profile_data = {
            "regularization_date":      reg_date.isoformat() if reg_date else None,
            "middle_name":              (ss.get(f"d_mn_{emp_id}") or "").strip() or None,
            "suffix":                   (ss.get(f"d_sx_{emp_id}") or "").strip() or None,
            "date_of_birth":            dob_val2.isoformat() if hasattr(dob_val2, "isoformat") else str(dob_val2),
            "place_of_birth":           (ss.get(f"d_pob_{emp_id}") or "").strip() or None,
            "sex":                      ss.get(f"d_sex_{emp_id}", "Male"),
            "civil_status":             civil_stat_val,
            "nationality":              (ss.get(f"d_nat_{emp_id}") or "Filipino").strip() or "Filipino",
            "religion":                 (ss.get(f"d_rel_{emp_id}") or "").strip() or None,
            "mobile_no":                (ss.get(f"d_mob_{emp_id}") or "").strip() or None,
            "philsys_no":               (ss.get(f"d_psys_{emp_id}") or "").strip() or None,
            "umid_no":                  (ss.get(f"d_umid_{emp_id}") or "").strip() or None,
            "bank_name":                (ss.get(f"d_bn_{emp_id}") or "").strip() or None,
            "present_address_street":   (ss.get(f"d_pstr_{emp_id}") or "").strip() or None,
            "present_address_barangay": (ss.get(f"d_pbrgy_{emp_id}") or "").strip() or None,
            "present_address_city":     (ss.get(f"d_pcity_{emp_id}") or "").strip() or None,
            "present_address_province": ss.get(f"d_pprov_{emp_id}", PROVINCES[0]),
            "present_address_zip":      (ss.get(f"d_pzip_{emp_id}") or "").strip() or None,
            "perm_address_same":        perm_same,
            "perm_address_street":      (ss.get(f"d_rmstr_{emp_id}") or "").strip() or None if not perm_same else None,
            "perm_address_barangay":    (ss.get(f"d_rmbrgy_{emp_id}") or "").strip() or None if not perm_same else None,
            "perm_address_city":        (ss.get(f"d_rmcity_{emp_id}") or "").strip() or None if not perm_same else None,
            "perm_address_province":    ss.get(f"d_rmprov_{emp_id}") if not perm_same else None,
            "perm_address_zip":         (ss.get(f"d_rmzip_{emp_id}") or "").strip() or None if not perm_same else None,
            "emergency_name":           (ss.get(f"d_ecn_{emp_id}") or "").strip() or None,
            "emergency_relationship":   (ss.get(f"d_ecr_{emp_id}") or "").strip() or None,
            "emergency_phone":          (ss.get(f"d_ecp_{emp_id}") or "").strip() or None,
            "emergency_address":        (ss.get(f"d_eca_{emp_id}") or "").strip() or None,
            "spouse_name":              (ss.get(f"d_spn_{emp_id}") or "").strip() or None if civil_stat_val == "Married" else None,
            "spouse_occupation":        (ss.get(f"d_spoc_{emp_id}") or "").strip() or None if civil_stat_val == "Married" else None,
            "spouse_employer":          (ss.get(f"d_spem_{emp_id}") or "").strip() or None if civil_stat_val == "Married" else None,
            "spouse_contact":           (ss.get(f"d_spct_{emp_id}") or "").strip() or None if civil_stat_val == "Married" else None,
            "home_phone":               (ss.get(f"d_hp_{emp_id}") or "").strip() or None,
            "work_phone":               (ss.get(f"d_wp_{emp_id}") or "").strip() or None,
            "personal_email":           (ss.get(f"d_pe_{emp_id}") or "").strip() or None,
            "education_degree":         (ss.get(f"d_edeg_{emp_id}") or "").strip() or None,
            "education_school":         (ss.get(f"d_esch_{emp_id}") or "").strip() or None,
            "education_year":           int(eyr_val) if eyr_val else None,
            "facebook":                 (ss.get(f"d_fb_{emp_id}") or "").strip() or None,
            "linkedin":                 (ss.get(f"d_li_{emp_id}") or "").strip() or None,
        }

        try:
            changes = _employee_diff(
                {**emp, **profile},
                {**emp_data, "regularization_date": profile_data.get("regularization_date")},
                resolved_department,
            )
            _update_employee(emp_id, emp_data)
            _upsert_employee_department(emp_id, resolved_department)
            _upsert_employee_profile_fields(emp_id, profile_data)
            log_action(
                "updated", "employee", emp_id,
                f"{emp_data['first_name']} {emp_data['last_name']}",
                details=changes,
            )
            st.session_state.pop("editing_id", None)
            _clear_dialog_state(emp_id)
            st.session_state["_edit_toast"] = (
                f"{emp_data['first_name']} {emp_data['last_name']} updated successfully."
            )
            st.rerun()
        except Exception as e:
            st.error(f"Error updating employee: {e}")


# ============================================================
# Main Page Render
# ============================================================

def _render_employees_tab(show_salary_toggle: bool = True):
    """Render the employee list table.

    Args:
        show_salary_toggle: If True (full page), salary is hidden by default
            with a reveal toggle. If False (dashboard dialog), salary is
            never shown.
    """
    # Open edit dialog if editing_id is set (dialog stays open until save/cancel clears it)
    if st.session_state.get("editing_id"):
        _edit_employee_dialog(st.session_state["editing_id"])

    # Row 1: add button (right-aligned) + flags
    _, col_add = st.columns([5, 1])
    with col_add:
        add_clicked = st.button("+ Add Employee", type="primary", width="stretch")

    # Row 2: flags
    chk1, chk2, _ = st.columns([1.5, 1.5, 4])
    with chk1:
        show_inactive = st.checkbox("Show inactive", key="emp_show_inactive")
    with chk2:
        show_incomplete_only = st.checkbox("Incomplete IDs only", key="emp_incomplete")

    # --- Add Employee Form ---
    if add_clicked:
        st.session_state.show_add_form = True

    if st.session_state.get("show_add_form"):
        st.divider()
        new_data = _employee_form(form_key="add_new")
        if new_data is not None:
            try:
                dept                = new_data.pop("department", "")
                regularization_date = new_data.pop("regularization_date", None)
                result = _create_employee(new_data)
                if dept:
                    _upsert_employee_department(result["id"], dept)
                if regularization_date:
                    _upsert_employee_profile_fields(result["id"], {
                        "regularization_date": regularization_date,
                    })
                log_action("created", "employee", result["id"], f"{new_data['first_name']} {new_data['last_name']}")
                st.session_state.show_add_form = False
                st.success(f"Added {new_data['first_name']} {new_data['last_name']}")
                st.rerun()
            except Exception as e:
                error_msg = str(e)
                if "duplicate" in error_msg.lower() or "unique" in error_msg.lower():
                    st.error(f"Employee number {new_data['employee_no']} already exists.")
                else:
                    st.error(f"Error adding employee: {error_msg}")

    # --- Load employees + departments ---
    employees   = _load_employees(show_inactive=show_inactive)
    dept_lookup = _load_all_departments()
    for emp in employees:
        emp["department"] = dept_lookup.get(emp["id"], "")

    # Filter controls — must be rendered AFTER employees are loaded so options are dynamic
    all_positions = sorted({(e.get("position") or "").strip() for e in employees} - {""})
    all_depts     = sorted({(e.get("department") or "").strip() for e in employees} - {""})
    # Load dept names from structured departments table (fall back to employee data)
    _dept_names_structured = _load_department_names()
    if _dept_names_structured:
        all_depts = _dept_names_structured
    f1, f2 = st.columns(2)
    with f1:
        sel_pos  = st.multiselect("Position", all_positions,  key="emp_f_pos",  placeholder="All positions")
    with f2:
        sel_dept = st.multiselect("Department", all_depts, key="emp_f_dept", placeholder="All departments")

    # Search bar — below the dropdowns
    search = st.text_input(
        "Search", placeholder="Name or employee number…",
        label_visibility="collapsed", key="emp_search",
    )

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

    # --- Apply all filters ---
    filtered = employees
    if search:
        q = search.lower()
        filtered = [
            e for e in filtered
            if q in e["first_name"].lower()
            or q in e["last_name"].lower()
            or q in e["employee_no"].lower()
        ]
    if sel_pos:
        filtered = [e for e in filtered if (e.get("position") or "") in sel_pos]
    if sel_dept:
        filtered = [e for e in filtered if (e.get("department") or "") in sel_dept]

    # --- Incomplete only filter ---
    if show_incomplete_only:
        filtered = [e for e in filtered if _onboarding_status(e)[0] < len(ONBOARDING_FIELDS)]

    # --- Employee Card Grid ---
    if not filtered:
        if show_incomplete_only:
            st.success("All employees have complete government ID profiles.")
        else:
            st.info("No employees found. Click '+ Add Employee' to get started.")
        return

    # ── Salary toggle ───────────────────────────────────────────────────────
    if show_salary_toggle:
        salary_visible = st.session_state.get("emp_salary_visible", False)
        cap_col, tog_col = st.columns([8, 2])
        cap_col.caption(f"Showing {len(filtered)} employee{'s' if len(filtered) != 1 else ''}")
        with tog_col:
            if st.button(
                "Show Salary" if not salary_visible else "Hide Salary",
                key="toggle_salary",
                icon=":material/visibility:" if not salary_visible else ":material/visibility_off:",
            ):
                st.session_state.emp_salary_visible = not salary_visible
    else:
        salary_visible = False
        st.caption(f"Showing {len(filtered)} employee{'s' if len(filtered) != 1 else ''}")

    # Avatar palette (cycles through 8 colors)
    _AV_PAL = [
        ("#d8e2ff", "#001a41"), ("#ffdea0", "#261a00"),
        ("#ffdad6", "#93000a"), ("#c8fcd3", "#002108"),
        ("#e1e3e4", "#424753"), ("#adc6ff", "#004493"),
        ("#cefbea", "#004d30"), ("#fce4ec", "#880e4f"),
    ]
    _TYPE_STYLE = {
        "regular":      ("#c8fcd3", "#005320"),
        "probationary": ("#ffdea0", "#5c4300"),
        "contractual":  ("#e1e3e4", "#424753"),
        "part-time":    ("#d8e2ff", "#004494"),
    }
    _GOV_FIELDS = [
        ("SSS", "sss_no"), ("PH", "philhealth_no"),
        ("PI",  "pagibig_no"), ("TIN", "tin_no"),
    ]

    # 3-column card grid
    for row_start in range(0, len(filtered), 3):
        row_emps = filtered[row_start:row_start + 3]
        gcols = st.columns(3)
        for col_idx, emp in enumerate(row_emps):
            with gcols[col_idx]:
                idx     = row_start + col_idx
                av_bg, av_fg = _AV_PAL[idx % len(_AV_PAL)]
                initials = (
                    (emp.get("first_name") or "")[:1]
                    + (emp.get("last_name") or "")[:1]
                ).upper() or "?"
                dept     = emp.get("department") or "—"
                name     = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
                position = emp.get("position") or "—"
                emp_type = (emp.get("employment_type") or "regular").lower()
                tb_bg, tb_fg = _TYPE_STYLE.get(emp_type, ("#e1e3e4", "#424753"))
                opacity  = "1" if emp.get("is_active", True) else "0.55"

                if salary_visible:
                    sal_v = _centavos_to_pesos(emp["basic_salary"])
                    sal_t = (emp.get("salary_type") or "monthly")[:2].lower()
                    salary_html = (
                        f"<span style='font-weight:700;color:#191c1d;font-size:13px;'>"
                        f"&#8369;{sal_v:,.0f}/{sal_t}</span>"
                    )
                else:
                    salary_html = (
                        "<span style='color:#b0b8c1;font-size:13px;letter-spacing:2px;'>"
                        "&#8226;&#8226;&#8226;&#8226;&#8226;&#8226;</span>"
                    )

                portal_badge = (
                    "<span style='font-size:9px;font-weight:700;color:#005bc1;"
                    "background:#d8e2ff;padding:2px 6px;border-radius:9999px;"
                    "margin-left:5px;vertical-align:middle;'>PORTAL</span>"
                    if emp.get("user_id") else ""
                )
                inactive_tag = (
                    "<div style='font-size:10px;font-weight:700;color:#ba1a1a;"
                    "text-transform:uppercase;letter-spacing:0.08em;margin-top:2px;'>Inactive</div>"
                    if not emp.get("is_active", True) else ""
                )
                gov_pills = "".join(
                    f"<div style='display:flex;align-items:center;gap:4px;"
                    f"font-size:10px;font-weight:700;color:#727784;"
                    f"background:#f3f4f5;padding:3px 7px;border-radius:5px;'>"
                    f"{lbl}&nbsp;"
                    f"<span style='width:7px;height:7px;border-radius:50%;"
                    f"background:{'#6ddd82' if emp.get(fld) else '#ba1a1a'};"
                    f"display:inline-block;flex-shrink:0;'></span></div>"
                    for lbl, fld in _GOV_FIELDS
                )

                st.markdown(
                    f"<div style='opacity:{opacity};background:#ffffff;border-radius:16px;"
                    f"padding:22px 22px 14px;margin-bottom:4px;"
                    f"box-shadow:0px 20px 40px rgba(45,51,53,0.06);"
                    f"display:flex;flex-direction:column;gap:13px;'>"
                    f"<div style='display:flex;justify-content:space-between;align-items:flex-start;'>"
                    f"<div style='width:52px;height:52px;border-radius:12px;background:{av_bg};"
                    f"display:flex;align-items:center;justify-content:center;"
                    f"font-size:17px;font-weight:800;color:{av_fg};"
                    f"font-family:\"Plus Jakarta Sans\",system-ui,sans-serif;'>{initials}</div>"
                    f"<div style='background:#ebeef0;padding:3px 10px;border-radius:9999px;"
                    f"font-size:10px;font-weight:700;text-transform:uppercase;"
                    f"letter-spacing:0.07em;color:#424753;max-width:120px;"
                    f"overflow:hidden;text-overflow:ellipsis;white-space:nowrap;'>{dept}</div>"
                    f"</div>"
                    f"<div>"
                    f"<div style='font-size:15px;font-weight:700;color:#191c1d;line-height:1.3;'>"
                    f"{name}{portal_badge}</div>"
                    f"{inactive_tag}"
                    f"<div style='font-size:12px;color:#424753;margin-top:2px;'>"
                    f"{emp['employee_no']} &middot; {position}</div>"
                    f"</div>"
                    f"<div style='display:flex;justify-content:space-between;align-items:center;"
                    f"padding-top:10px;border-top:1px solid #f3f4f5;'>"
                    f"{salary_html}"
                    f"<span style='font-size:10px;font-weight:700;padding:3px 8px;border-radius:5px;"
                    f"background:{tb_bg};color:{tb_fg};'>{emp_type.title()}</span>"
                    f"</div>"
                    f"<div style='display:flex;gap:5px;flex-wrap:wrap;'>{gov_pills}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                # ── Action buttons ─────────────────────────────────────────
                b1, b2, b3, b4, b5 = st.columns(5)
                with b1:
                    if st.button("", key=f"edit_{emp['id']}", width="stretch",
                                 type="primary", icon=":material/edit:", help="Edit employee"):
                        st.session_state.editing_id = emp["id"]
                        st.rerun()
                with b2:
                    if not emp.get("email"):
                        st.markdown(
                            "<div style='text-align:center;color:#aaa;padding-top:8px;font-size:12px;'"
                            " title='Add email to enable portal invite'>—</div>",
                            unsafe_allow_html=True,
                        )
                    elif not emp.get("user_id"):
                        if st.button("", key=f"invite_{emp['id']}", width="stretch",
                                     icon=":material/contact_mail:",
                                     help=f"Send portal invite to {emp['email']}"):
                            st.session_state[f"invite_confirm_{emp['id']}"] = True
                    else:
                        if st.button("", key=f"invite_{emp['id']}", width="stretch",
                                     icon=":material/sync:",
                                     help=f"Resend portal access to {emp['email']}"):
                            st.session_state[f"invite_confirm_{emp['id']}"] = True
                with b3:
                    if emp.get("email") and emp.get("user_id"):
                        if st.button("", key=f"resetpwd_{emp['id']}", width="stretch",
                                     icon=":material/lock_reset:",
                                     help=f"Send password reset to {emp['email']}"):
                            from app.auth import send_password_reset
                            ok, err = send_password_reset(emp["email"])
                            st.session_state["_invite_toast"] = (
                                ("success", f"Password reset email sent to **{emp['email']}**.")
                                if ok else ("error", err)
                            )
                            st.rerun()
                    else:
                        st.markdown(
                            "<div style='text-align:center;color:#aaa;padding-top:8px;font-size:12px;'"
                            " title='Link portal first to enable password reset'>—</div>",
                            unsafe_allow_html=True,
                        )
                with b4:
                    if emp.get("is_active", True):
                        st.button("", key=f"deact_{emp['id']}", width="stretch",
                                  icon=":material/radio_button_checked:",
                                  help="Deactivate this employee",
                                  on_click=_update_employee, args=(emp["id"], {"is_active": False}))
                    else:
                        st.button("", key=f"react_{emp['id']}", width="stretch",
                                  icon=":material/radio_button_unchecked:",
                                  help="Reactivate this employee",
                                  on_click=_update_employee, args=(emp["id"], {"is_active": True}))
                with b5:
                    if st.button("", key=f"print201_{emp['id']}", width="stretch",
                                 icon=":material/print:", help="Print Employee 201 File"):
                        st.session_state["print201_id"] = emp["id"]

                # ── Invite confirmation ────────────────────────────────────
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
                                db.table("employees").update({"user_id": auth_user_id}).eq("id", emp["id"]).execute()
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
                                    toast_msg = (
                                        f"Account created for **{emp['email']}**.\n\n"
                                        f"Email could not be sent ({smtp_err}).\n\n"
                                        f"**Share this temporary password manually:**\n\n"
                                        f"```\n{temp_password}\n```\n\n"
                                        "Tell the employee to log in and use **Forgot Password** to change it."
                                    )
                                    st.session_state["_invite_toast"] = ("warning", toast_msg)
                                else:
                                    action = "re-linked" if already_linked else "created"
                                    st.session_state["_invite_toast"] = (
                                        "success",
                                        f"Portal access {action} for **{emp['email']}**. "
                                        "A temporary password was emailed.",
                                    )
                            else:
                                st.session_state["_invite_toast"] = ("error", result)
                            st.session_state[f"invite_confirm_{emp['id']}"] = False
                            st.rerun()
                    with c2:
                        if st.button("Cancel", key=f"inv_no_{emp['id']}"):
                            st.session_state[f"invite_confirm_{emp['id']}"] = False
                            st.rerun()

    # ── Employee 201 Print ────────────────────────────────────────────────────
    if st.session_state.get("print201_id"):
        _print_emp_id = st.session_state.pop("print201_id")   # clear immediately
        _print_emp    = next((e for e in employees if e["id"] == _print_emp_id), None)
        if _print_emp:
            try:
                from reports.emp201_pdf import generate_emp201_pdf
                import base64 as _b64mod
                import streamlit.components.v1 as _cv1
                _dept_lkp  = _load_all_departments()
                _p201      = _load_employee_profile(_print_emp_id)
                _pdf_bytes = generate_emp201_pdf(
                    _print_emp, _p201, _dept_lkp.get(_print_emp_id, "")
                )
                _fname = (
                    f"201_{_print_emp.get('employee_no','EMP')}_"
                    f"{_print_emp.get('last_name','').upper()}.pdf"
                )
                # Open PDF in new tab + auto-trigger print dialog
                _b64_str = _b64mod.b64encode(_pdf_bytes).decode()
                _cv1.html(f"""
<script>
(function(){{
  try {{
    var b64="{_b64_str}";
    var raw=atob(b64);
    var bytes=new Uint8Array(raw.length);
    for(var i=0;i<raw.length;i++){{bytes[i]=raw.charCodeAt(i);}}
    var blob=new Blob([bytes],{{type:'application/pdf'}});
    var url=(window.parent.URL||URL).createObjectURL(blob);
    var win=(window.parent.open||window.open).call(window.parent,url,'_blank');
    if(win){{
      win.addEventListener('load',function(){{
        setTimeout(function(){{win.print();}},400);
      }});
    }}
  }} catch(e){{ console.error('Print 201 error:',e); }}
}})();
</script>
""", height=0, scrolling=False)
                # Download fallback (in case popup blocked)
                st.download_button(
                    label=f"⬇️ Download 201 — {_print_emp['last_name']} (popup blocked?)",
                    data=_pdf_bytes,
                    file_name=_fname,
                    mime="application/pdf",
                    key="dl_201_btn",
                )
            except Exception as _e:
                st.error(f"Could not generate 201 PDF: {_e}")


# ============================================================
# Page entry point
# ============================================================

def render():
    inject_css()
    st.markdown(
        '<p class="gxp-page-label">TEAM</p>'
        '<h2 class="gxp-editorial-heading">Employees</h2>',
        unsafe_allow_html=True,
    )

    # ── Page-level toasts (shown above tabs so they're always visible) ─────────
    if "_edit_toast" in st.session_state:
        st.toast(st.session_state.pop("_edit_toast"), icon="✅")

    for toast_key in ("_invite_toast", "_review_toast"):
        if toast_key in st.session_state:
            kind, msg = st.session_state.pop(toast_key)
            if kind == "success":
                st.success(msg)
            elif kind == "warning":
                st.warning(msg)
            else:
                st.error(msg)

    # ── Pending counts for tab notification badges ────────────────────────────
    pending_lr, pending_ot = _count_pending_admin()
    pending_total   = pending_lr + pending_ot
    pending_special = _count_pending_special()

    _badge_css = ""

    if pending_total > 0:
        _badge_css += f"""
            button[data-baseweb="tab"]:nth-child(2) p {{
                position: relative !important; padding-right: 20px !important;
            }}
            button[data-baseweb="tab"]:nth-child(2) p::after {{
                content: "{pending_total}"; position: absolute; top: -5px; right: 0;
                background: #ef4444; color: white; border-radius: 9999px;
                min-width: 16px; height: 16px; font-size: 10px; font-weight: 800;
                text-align: center; line-height: 16px; padding: 0 3px; box-sizing: border-box;
            }}"""

    if pending_special > 0:
        _badge_css += f"""
            button[data-baseweb="tab"]:nth-child(4) p {{
                position: relative !important; padding-right: 20px !important;
            }}
            button[data-baseweb="tab"]:nth-child(4) p::after {{
                content: "{pending_special}"; position: absolute; top: -5px; right: 0;
                background: #be185d; color: white; border-radius: 9999px;
                min-width: 16px; height: 16px; font-size: 10px; font-weight: 800;
                text-align: center; line-height: 16px; padding: 0 3px; box-sizing: border-box;
            }}"""

    if _badge_css:
        st.markdown(
            f"""<style>
            {_badge_css}
            /* Exclude badges on inner nested tabs */
            div[data-baseweb="tab-panel"] button[data-baseweb="tab"]:nth-child(2) p,
            div[data-baseweb="tab-panel"] button[data-baseweb="tab"]:nth-child(4) p {{
                padding-right: 0 !important;
            }}
            div[data-baseweb="tab-panel"] button[data-baseweb="tab"]:nth-child(2) p::after,
            div[data-baseweb="tab-panel"] button[data-baseweb="tab"]:nth-child(4) p::after {{
                display: none !important;
            }}
            </style>""",
            unsafe_allow_html=True,
        )

    tab_emp, tab_approvals, tab_balances, tab_special = st.tabs([
        "Employees",
        "Leave & OT Approvals",
        "Leave Balances",
        "Special Leaves",
    ])

    with tab_emp:
        _render_employees_tab()

    with tab_approvals:
        _render_approvals_tab()

    with tab_balances:
        _render_leave_balances_tab()

    with tab_special:
        _render_special_leaves_tab()
