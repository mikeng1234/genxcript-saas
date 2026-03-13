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

        # --- Row 3: Salary ---
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

        # --- Row 4: Government numbers ---
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

        # --- Row 5: Bank account ---
        bank_account = st.text_input("Bank Account No.", value=defaults.get("bank_account", "") or "")

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
                "employee_no": employee_no.strip(),
                "first_name": first_name.strip(),
                "last_name": last_name.strip(),
                "position": position.strip(),
                "employment_type": employment_type,
                "date_hired": date_hired.isoformat(),
                "basic_salary": _pesos_to_centavos(basic_salary),
                "salary_type": salary_type,
                "tax_status": tax_status,
                "sss_no": sss_no.strip(),
                "philhealth_no": philhealth_no.strip(),
                "pagibig_no": pagibig_no.strip(),
                "bir_tin": bir_tin.strip(),
                "bank_account": bank_account.strip(),
            }

    return None


# ============================================================
# Main Page Render
# ============================================================

def render():
    st.title("Employee Master File")

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
    cols = st.columns([1, 2, 2, 2, 1.5, 1, 1, 1])
    for col, header in zip(cols, ["No.", "Name", "Position", "Salary", "Type", "IDs", "Status", "Actions"]):
        col.markdown(f"**{header}**")

    # Table rows
    for emp in filtered:
        completed, missing = _onboarding_status(emp)
        cols = st.columns([1, 2, 2, 2, 1.5, 1, 1, 1])

        with cols[0]:
            st.text(emp["employee_no"])
        with cols[1]:
            st.text(f"{emp['last_name']}, {emp['first_name']}")
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
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("Edit", key=f"edit_{emp['id']}", width="stretch"):
                    st.session_state.editing_id = emp["id"]
            with btn_col2:
                if emp.get("is_active", True):
                    if st.button("Off", key=f"deact_{emp['id']}", width="stretch"):
                        _update_employee(emp["id"], {"is_active": False})
                        st.rerun()
                else:
                    if st.button("On", key=f"react_{emp['id']}", width="stretch"):
                        _update_employee(emp["id"], {"is_active": True})
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
