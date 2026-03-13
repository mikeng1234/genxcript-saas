"""
Payroll Run — Streamlit page.

The main working screen:
1. Create or select a pay period
2. Input additional earnings per employee (OT, holiday, allowances, etc.)
3. Auto-compute government contributions + withholding tax
4. Review breakdown and finalize
"""

import streamlit as st
from datetime import date, timedelta
import calendar
from backend.payroll import compute_payroll
from app.db_helper import get_db, get_company_id
import plotly.graph_objects as go
import pandas as pd


# ============================================================
# Helpers
# ============================================================

def _centavos_to_pesos(centavos: int) -> float:
    return centavos / 100


def _compute_period_end(start: date, pay_frequency: str) -> date:
    """
    Given a period start date and the company's pay frequency,
    return the estimated period end date.

    - semi-monthly : start on 1–15 → end on the 15th;
                     start on 16–31 → end on last day of the month
    - monthly      : last day of the start date's month
    - weekly       : start + 6 days (Mon–Sun)
    """
    if pay_frequency == "semi-monthly":
        if start.day <= 15:
            return start.replace(day=15)
        else:
            last_day = calendar.monthrange(start.year, start.month)[1]
            return start.replace(day=last_day)

    elif pay_frequency == "monthly":
        last_day = calendar.monthrange(start.year, start.month)[1]
        return start.replace(day=last_day)

    elif pay_frequency == "weekly":
        return start + timedelta(days=6)

    # Fallback — treat as semi-monthly
    if start.day <= 15:
        return start.replace(day=15)
    last_day = calendar.monthrange(start.year, start.month)[1]
    return start.replace(day=last_day)


def _pesos_to_centavos(pesos: float) -> int:
    return int(round(pesos * 100))


def _fmt(centavos: int) -> str:
    """Format centavos as peso string: ₱12,345.67"""
    return f"₱{_centavos_to_pesos(centavos):,.2f}"


# ============================================================
# Database operations
# ============================================================

def _load_company() -> dict:
    """Load the current company record (for pay_frequency etc.)."""
    db = get_db()
    result = (
        db.table("companies")
        .select("*")
        .eq("id", get_company_id())
        .single()
        .execute()
    )
    return result.data or {}


def _load_employees() -> list[dict]:
    """Load active employees from Supabase."""
    db = get_db()
    result = (
        db.table("employees")
        .select("*")
        .eq("company_id", get_company_id())
        .eq("is_active", True)
        .order("last_name")
        .execute()
    )
    return result.data


def _load_pay_periods() -> list[dict]:
    """Load all pay periods from Supabase."""
    db = get_db()
    result = (
        db.table("pay_periods")
        .select("*")
        .eq("company_id", get_company_id())
        .order("period_start", desc=True)
        .execute()
    )
    return result.data


def _create_pay_period(data: dict) -> dict:
    """Insert a new pay period."""
    db = get_db()
    data["company_id"] = get_company_id()
    result = db.table("pay_periods").insert(data).execute()
    return result.data[0]


def _update_pay_period(period_id: str, data: dict) -> dict:
    """Update a pay period (e.g. status change)."""
    db = get_db()
    result = db.table("pay_periods").update(data).eq("id", period_id).execute()
    return result.data[0]


def _load_payroll_entries(pay_period_id: str) -> dict:
    """Load all payroll entries for a pay period, keyed by employee_id."""
    db = get_db()
    result = (
        db.table("payroll_entries")
        .select("*")
        .eq("pay_period_id", pay_period_id)
        .execute()
    )
    return {row["employee_id"]: row for row in result.data}


def _upsert_payroll_entry(pay_period_id: str, employee_id: str, data: dict) -> dict:
    """Insert or update a payroll entry for an employee in a pay period."""
    db = get_db()
    data["pay_period_id"] = pay_period_id
    data["employee_id"] = employee_id

    # Check if entry exists
    existing = (
        db.table("payroll_entries")
        .select("id")
        .eq("pay_period_id", pay_period_id)
        .eq("employee_id", employee_id)
        .execute()
    )

    if existing.data:
        # Update existing
        result = (
            db.table("payroll_entries")
            .update(data)
            .eq("id", existing.data[0]["id"])
            .execute()
        )
    else:
        # Insert new
        result = db.table("payroll_entries").insert(data).execute()

    return result.data[0]


# ============================================================
# Pay Period Management
# ============================================================

def _load_all_period_history() -> list[dict]:
    """Load aggregate totals for all finalized/paid periods — used for the trend chart."""
    db = get_db()
    periods_result = (
        db.table("pay_periods")
        .select("*")
        .eq("company_id", get_company_id())
        .in_("status", ["finalized", "paid"])
        .order("period_start", desc=False)
        .execute()
    )
    rows = []
    for p in periods_result.data:
        entries_result = (
            db.table("payroll_entries")
            .select("*")
            .eq("pay_period_id", p["id"])
            .execute()
        )
        entries = entries_result.data
        if not entries:
            continue
        rows.append({
            "period": p["period_start"],
            "gross_pay":       sum(e["gross_pay"]         for e in entries) / 100,
            "total_deductions":sum(e["total_deductions"]  for e in entries) / 100,
            "net_pay":         sum(e["net_pay"]           for e in entries) / 100,
            "employer_cost":   sum(
                e["sss_employer"] + e["philhealth_employer"] + e["pagibig_employer"]
                for e in entries
            ) / 100,
        })
    return rows


def _render_pay_period_selector() -> dict | None:
    """Render pay period creation and selection. Returns selected period or None."""
    periods = _load_pay_periods()

    col_select, col_new = st.columns([3, 1])

    with col_new:
        st.write("")  # spacer
        st.write("")
        if st.button("+ New Pay Period", type="primary", width="stretch"):
            st.session_state.show_new_period = True
            # Clear stale date state so defaults are recomputed fresh
            for k in ("np_start", "np_end", "np_pay", "np_start_prev"):
                st.session_state.pop(k, None)

    with col_select:
        if not periods:
            st.info("No pay periods yet. Create one to start.")
            selected_period = None
        else:
            period_labels = {
                p["id"]: f"{p['period_start']} to {p['period_end']}  [{p['status'].upper()}]"
                for p in periods
            }
            selected_id = st.selectbox(
                "Select Pay Period",
                options=[p["id"] for p in periods],
                format_func=lambda x: period_labels[x],
                index=0,  # latest first (sorted desc)
            )
            selected_period = next(p for p in periods if p["id"] == selected_id)

    # ── New period creation ──────────────────────────────────────────────────
    if st.session_state.get("show_new_period"):
        st.subheader("Create Pay Period")

        # Load company pay frequency once
        company = _load_company()
        pay_frequency = company.get("pay_frequency", "semi-monthly")

        # Compute sensible default start date based on frequency
        today = date.today()
        if pay_frequency == "weekly":
            # Start of the current week (Monday)
            default_start = today - timedelta(days=today.weekday())
        elif pay_frequency == "monthly":
            default_start = today.replace(day=1)
        else:  # semi-monthly
            default_start = today.replace(day=1) if today.day <= 15 else today.replace(day=16)

        # ── Seed session state on first render ───────────────────────────────
        if "np_start" not in st.session_state:
            st.session_state.np_start = default_start
            st.session_state.np_end   = _compute_period_end(default_start, pay_frequency)
            st.session_state.np_pay   = st.session_state.np_end + timedelta(days=5)
            st.session_state.np_start_prev = default_start

        # ── Auto-update end/payment dates when start changes ─────────────────
        # Compare current widget value to previous; update end only if start moved.
        current_start = st.session_state.np_start
        if current_start != st.session_state.get("np_start_prev"):
            new_end = _compute_period_end(current_start, pay_frequency)
            st.session_state.np_end  = new_end
            st.session_state.np_pay  = new_end + timedelta(days=5)
            st.session_state.np_start_prev = current_start

        # ── Date inputs (outside form so changes trigger reruns) ─────────────
        col1, col2, col3 = st.columns(3)
        with col1:
            st.date_input(
                "Period Start",
                key="np_start",
                help=f"Pay frequency: {pay_frequency}. Period End auto-fills based on this.",
            )
        with col2:
            st.date_input(
                "Period End",
                key="np_end",
                help="Auto-filled from Period Start. You can adjust if needed.",
            )
        with col3:
            st.date_input(
                "Payment Date",
                key="np_pay",
                help="Default is 5 days after Period End.",
            )

        # ── Submit button ────────────────────────────────────────────────────
        col_cancel, col_create = st.columns([1, 1])
        with col_cancel:
            if st.button("Cancel", width="stretch"):
                st.session_state.show_new_period = False
                for k in ("np_start", "np_end", "np_pay", "np_start_prev"):
                    st.session_state.pop(k, None)
                st.rerun()
        with col_create:
            if st.button("Create Period", type="primary", width="stretch"):
                p_start = st.session_state.np_start
                p_end   = st.session_state.np_end
                p_pay   = st.session_state.np_pay
                if p_end <= p_start:
                    st.error("Period End must be after Period Start.")
                else:
                    try:
                        _create_pay_period({
                            "period_start": p_start.isoformat(),
                            "period_end":   p_end.isoformat(),
                            "payment_date": p_pay.isoformat(),
                            "status": "draft",
                        })
                        st.session_state.show_new_period = False
                        for k in ("np_start", "np_end", "np_pay", "np_start_prev"):
                            st.session_state.pop(k, None)
                        st.success(f"Created pay period: {p_start} to {p_end}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creating pay period: {e}")

        st.divider()

    return selected_period


# ============================================================
# Earnings Input & Computation per Employee
# ============================================================

def _render_employee_payroll(emp: dict, period_id: str, is_finalized: bool, entries: dict):
    """Render earnings input and computation for one employee."""
    saved = entries.get(emp["id"], {})

    name = f"{emp['first_name']} {emp['last_name']}"
    salary_display = _fmt(emp["basic_salary"])

    with st.expander(f"{emp['employee_no']} — {name}  |  Basic: {salary_display}", expanded=False):

        if is_finalized:
            _render_payroll_summary(saved)
            return

        # --- Earnings input form ---
        with st.form(key=f"earnings_{period_id}_{emp['id']}"):

            st.markdown("**Earnings**")
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                basic_pay = st.number_input(
                    "Basic Pay (₱)", min_value=0.0,
                    value=_centavos_to_pesos(saved.get("basic_pay", emp["basic_salary"])),
                    step=100.0, format="%.2f",
                    key=f"basic_{period_id}_{emp['id']}",
                )
            with col2:
                overtime_pay = st.number_input(
                    "Overtime (₱)", min_value=0.0,
                    value=_centavos_to_pesos(saved.get("overtime_pay", 0)),
                    step=100.0, format="%.2f",
                    key=f"ot_{period_id}_{emp['id']}",
                )
            with col3:
                holiday_pay = st.number_input(
                    "Holiday Pay (₱)", min_value=0.0,
                    value=_centavos_to_pesos(saved.get("holiday_pay", 0)),
                    step=100.0, format="%.2f",
                    key=f"hol_{period_id}_{emp['id']}",
                )
            with col4:
                night_diff = st.number_input(
                    "Night Diff (₱)", min_value=0.0,
                    value=_centavos_to_pesos(saved.get("night_differential", 0)),
                    step=100.0, format="%.2f",
                    key=f"nd_{period_id}_{emp['id']}",
                )

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                allowances_nt = st.number_input(
                    "Non-Taxable Allowances (₱)", min_value=0.0,
                    value=_centavos_to_pesos(saved.get("allowances_nontaxable", 0)),
                    step=100.0, format="%.2f",
                    key=f"ant_{period_id}_{emp['id']}",
                    help="Meal, rice, clothing allowances within de minimis limits",
                )
            with col2:
                allowances_t = st.number_input(
                    "Taxable Allowances (₱)", min_value=0.0,
                    value=_centavos_to_pesos(saved.get("allowances_taxable", 0)),
                    step=100.0, format="%.2f",
                    key=f"at_{period_id}_{emp['id']}",
                )
            with col3:
                commission = st.number_input(
                    "Commission (₱)", min_value=0.0,
                    value=_centavos_to_pesos(saved.get("commission", 0)),
                    step=100.0, format="%.2f",
                    key=f"comm_{period_id}_{emp['id']}",
                )
            with col4:
                thirteenth = st.number_input(
                    "13th Month Accrual (₱)", min_value=0.0,
                    value=_centavos_to_pesos(saved.get("thirteenth_month_accrual", 0)),
                    step=100.0, format="%.2f",
                    key=f"13th_{period_id}_{emp['id']}",
                )

            # --- Other deductions ---
            st.markdown("**Other Deductions**")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                sss_loan = st.number_input(
                    "SSS Loan (₱)", min_value=0.0,
                    value=_centavos_to_pesos(saved.get("sss_loan", 0)),
                    step=100.0, format="%.2f",
                    key=f"sssl_{period_id}_{emp['id']}",
                )
            with col2:
                pagibig_loan = st.number_input(
                    "Pag-IBIG Loan (₱)", min_value=0.0,
                    value=_centavos_to_pesos(saved.get("pagibig_loan", 0)),
                    step=100.0, format="%.2f",
                    key=f"pil_{period_id}_{emp['id']}",
                )
            with col3:
                cash_advance = st.number_input(
                    "Cash Advance (₱)", min_value=0.0,
                    value=_centavos_to_pesos(saved.get("cash_advance", 0)),
                    step=100.0, format="%.2f",
                    key=f"ca_{period_id}_{emp['id']}",
                )
            with col4:
                other_ded = st.number_input(
                    "Other Deductions (₱)", min_value=0.0,
                    value=_centavos_to_pesos(saved.get("other_deductions", 0)),
                    step=100.0, format="%.2f",
                    key=f"other_{period_id}_{emp['id']}",
                )

            computed = st.form_submit_button("Compute & Save", type="primary", width="stretch")

        if computed:
            # Convert all inputs to centavos
            basic_c = _pesos_to_centavos(basic_pay)
            ot_c = _pesos_to_centavos(overtime_pay)
            hol_c = _pesos_to_centavos(holiday_pay)
            nd_c = _pesos_to_centavos(night_diff)
            ant_c = _pesos_to_centavos(allowances_nt)
            at_c = _pesos_to_centavos(allowances_t)
            comm_c = _pesos_to_centavos(commission)
            thirteenth_c = _pesos_to_centavos(thirteenth)
            sssl_c = _pesos_to_centavos(sss_loan)
            pil_c = _pesos_to_centavos(pagibig_loan)
            ca_c = _pesos_to_centavos(cash_advance)
            other_c = _pesos_to_centavos(other_ded)

            # Gross pay = sum of all earnings
            gross = basic_c + ot_c + hol_c + nd_c + ant_c + at_c + comm_c + thirteenth_c

            # Run computation engine
            result = compute_payroll(
                gross_pay=gross,
                nontaxable_allowances=ant_c,
            )

            # Total voluntary deductions
            vol_deductions = sssl_c + pil_c + ca_c + other_c

            # Save to database
            entry_data = {
                "basic_pay": basic_c,
                "overtime_pay": ot_c,
                "holiday_pay": hol_c,
                "night_differential": nd_c,
                "allowances_nontaxable": ant_c,
                "allowances_taxable": at_c,
                "commission": comm_c,
                "thirteenth_month_accrual": thirteenth_c,
                "gross_pay": gross,
                "sss_employee": result.sss_employee,
                "philhealth_employee": result.philhealth_employee,
                "pagibig_employee": result.pagibig_employee,
                "sss_employer": result.sss_employer,
                "philhealth_employer": result.philhealth_employer,
                "pagibig_employer": result.pagibig_employer,
                "withholding_tax": result.withholding_tax,
                "sss_loan": sssl_c,
                "pagibig_loan": pil_c,
                "cash_advance": ca_c,
                "other_deductions": other_c,
                "total_deductions": result.total_mandatory_deductions + vol_deductions,
                "net_pay": result.net_pay - vol_deductions,
            }

            try:
                saved_entry = _upsert_payroll_entry(period_id, emp["id"], entry_data)
                entries[emp["id"]] = saved_entry
                st.success(f"Computed: {name} — Net Pay: {_fmt(entry_data['net_pay'])}")
            except Exception as e:
                st.error(f"Error saving: {e}")

        # Show last computed result if available
        if emp["id"] in entries:
            _render_payroll_summary(entries[emp["id"]])


def _render_payroll_summary(entry: dict):
    """Show the computation breakdown for an employee."""
    if not entry:
        st.caption("Not yet computed. Fill in earnings and click 'Compute & Save'.")
        return

    st.markdown("---")
    col_earn, col_ded, col_net = st.columns(3)

    with col_earn:
        st.markdown("**Earnings**")
        st.text(f"Basic Pay:       {_fmt(entry.get('basic_pay', 0))}")
        st.text(f"Overtime:        {_fmt(entry.get('overtime_pay', 0))}")
        st.text(f"Holiday Pay:     {_fmt(entry.get('holiday_pay', 0))}")
        st.text(f"Night Diff:      {_fmt(entry.get('night_differential', 0))}")
        st.text(f"Allow (NT):      {_fmt(entry.get('allowances_nontaxable', 0))}")
        st.text(f"Allow (Tax):     {_fmt(entry.get('allowances_taxable', 0))}")
        st.text(f"Commission:      {_fmt(entry.get('commission', 0))}")
        st.text(f"13th Month:      {_fmt(entry.get('thirteenth_month_accrual', 0))}")
        st.markdown(f"**Gross Pay:     {_fmt(entry.get('gross_pay', 0))}**")

    with col_ded:
        st.markdown("**Deductions**")
        st.text(f"SSS (EE):        {_fmt(entry.get('sss_employee', 0))}")
        st.text(f"PhilHealth (EE): {_fmt(entry.get('philhealth_employee', 0))}")
        st.text(f"Pag-IBIG (EE):   {_fmt(entry.get('pagibig_employee', 0))}")
        st.text(f"Withholding Tax: {_fmt(entry.get('withholding_tax', 0))}")
        st.markdown("*Voluntary:*")
        st.text(f"SSS Loan:        {_fmt(entry.get('sss_loan', 0))}")
        st.text(f"Pag-IBIG Loan:   {_fmt(entry.get('pagibig_loan', 0))}")
        st.text(f"Cash Advance:    {_fmt(entry.get('cash_advance', 0))}")
        st.text(f"Other:           {_fmt(entry.get('other_deductions', 0))}")
        st.markdown(f"**Total Ded:     {_fmt(entry.get('total_deductions', 0))}**")

    with col_net:
        st.markdown("**Summary**")
        er_total = entry.get("sss_employer", 0) + entry.get("philhealth_employer", 0) + entry.get("pagibig_employer", 0)
        st.markdown("")
        st.markdown("*Employer Cost:*")
        st.text(f"SSS (ER):        {_fmt(entry.get('sss_employer', 0))}")
        st.text(f"PhilHealth (ER): {_fmt(entry.get('philhealth_employer', 0))}")
        st.text(f"Pag-IBIG (ER):   {_fmt(entry.get('pagibig_employer', 0))}")
        st.text(f"Total ER Cost:   {_fmt(er_total)}")
        st.markdown("")
        net = entry.get("net_pay", 0)
        st.markdown(f"### Net Pay: {_fmt(net)}")


# ============================================================
# Payroll Summary Totals
# ============================================================

def _render_period_totals(entries: dict, employees: list[dict]):
    """Show totals across all employees for this pay period."""
    computed = [entries[e["id"]] for e in employees if e["id"] in entries]

    if not computed:
        return

    st.divider()
    st.subheader("Pay Period Totals")

    total_gross = sum(e["gross_pay"] for e in computed)
    total_sss_ee = sum(e["sss_employee"] for e in computed)
    total_ph_ee = sum(e["philhealth_employee"] for e in computed)
    total_pi_ee = sum(e["pagibig_employee"] for e in computed)
    total_wht = sum(e["withholding_tax"] for e in computed)
    total_sss_er = sum(e["sss_employer"] for e in computed)
    total_ph_er = sum(e["philhealth_employer"] for e in computed)
    total_pi_er = sum(e["pagibig_employer"] for e in computed)
    total_deductions = sum(e["total_deductions"] for e in computed)
    total_net = sum(e["net_pay"] for e in computed)
    total_er = total_sss_er + total_ph_er + total_pi_er

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Gross Pay", _fmt(total_gross))
    with col2:
        st.metric("Total Deductions", _fmt(total_deductions))
    with col3:
        st.metric("Total Net Pay", _fmt(total_net))
    with col4:
        st.metric("Total Employer Cost", _fmt(total_er))

    st.markdown("**Government Remittances Due:**")
    rem_cols = st.columns(4)
    with rem_cols[0]:
        st.text(f"SSS:       EE {_fmt(total_sss_ee)} + ER {_fmt(total_sss_er)} = {_fmt(total_sss_ee + total_sss_er)}")
    with rem_cols[1]:
        st.text(f"PhilHealth: EE {_fmt(total_ph_ee)} + ER {_fmt(total_ph_er)} = {_fmt(total_ph_ee + total_ph_er)}")
    with rem_cols[2]:
        st.text(f"Pag-IBIG:  EE {_fmt(total_pi_ee)} + ER {_fmt(total_pi_er)} = {_fmt(total_pi_ee + total_pi_er)}")
    with rem_cols[3]:
        st.text(f"BIR WHT:   {_fmt(total_wht)}")

    computed_count = len(computed)
    total_count = len(employees)
    if computed_count < total_count:
        st.warning(f"Only {computed_count} of {total_count} employees computed. Compute all before finalizing.")


# ============================================================
# Main Page Render
# ============================================================

def render():
    st.title("Payroll Run")

    # ---- Payroll History Combination Chart (moved to top) ----
    st.divider()
    st.subheader("📊 Payroll History")

    history = _load_all_period_history()

    if not history:
        st.info("Chart will appear once you have at least one finalized pay period.")
    else:
        df_hist = pd.DataFrame(history)

        fig = go.Figure()

        # Grouped bars: Net Pay, Total Deductions, Employer Cost
        fig.add_trace(go.Bar(
            name="Net Pay",
            x=df_hist["period"],
            y=df_hist["net_pay"],
            marker_color="#2ca02c",
            offsetgroup=0,
        ))
        fig.add_trace(go.Bar(
            name="Total Deductions",
            x=df_hist["period"],
            y=df_hist["total_deductions"],
            marker_color="#d62728",
            offsetgroup=1,
        ))
        fig.add_trace(go.Bar(
            name="Employer Cost",
            x=df_hist["period"],
            y=df_hist["employer_cost"],
            marker_color="#ff7f0e",
            offsetgroup=2,
        ))

        # Line overlay: Total Gross Pay
        fig.add_trace(go.Scatter(
            name="Gross Pay",
            x=df_hist["period"],
            y=df_hist["gross_pay"],
            mode="lines+markers",
            line=dict(color="#1f77b4", width=3),
            marker=dict(size=8),
        ))

        fig.update_layout(
            barmode="group",
            title="Payroll Breakdown by Period",
            xaxis_title="Pay Period Start",
            yaxis_title="Amount (₱)",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=0, r=0, t=56, b=0),
        )

        st.plotly_chart(fig, width="stretch")

    st.divider()

    employees = _load_employees()

    if not employees:
        st.warning("No active employees. Add employees first in the Employee Master File.")
        return

    # --- Pay Period Selection ---
    period = _render_pay_period_selector()

    if period is None:
        return

    is_locked = period["status"] in ("reviewed", "finalized", "paid")

    st.divider()

    # Status badge
    status_colors = {"draft": "blue", "reviewed": "violet", "finalized": "orange", "paid": "green"}
    color = status_colors.get(period["status"], "gray")
    status_line = f"**Period:** {period['period_start']} to {period['period_end']}  &nbsp; | &nbsp;  **Payment Date:** {period['payment_date']}  &nbsp; | &nbsp;  **Status:** :{color}[{period['status'].upper()}]"

    # Show reviewer info if available
    if period.get("reviewed_by"):
        reviewed_at = period["reviewed_at"][:16].replace("T", " ") if period.get("reviewed_at") else ""
        status_line += f"  &nbsp; | &nbsp;  **Reviewed by:** {period['reviewed_by']} ({reviewed_at})"

    st.markdown(status_line)

    if is_locked:
        col_msg, col_btn = st.columns([4, 1])
        with col_msg:
            if period["status"] == "reviewed":
                st.info("This pay period is under review. Earnings are read-only.")
            else:
                st.info("This pay period is finalized. Earnings are read-only.")
        with col_btn:
            st.write("")  # spacer
            if st.button("Reopen for Editing", width="stretch"):
                _update_pay_period(period["id"], {"status": "draft", "reviewed_by": None, "reviewed_at": None})
                st.rerun()

    # --- Load payroll entries for this period ---
    entries = _load_payroll_entries(period["id"])

    # --- Employee payroll entries ---
    st.subheader(f"Employees ({len(employees)})")

    for emp in employees:
        _render_employee_payroll(emp, period["id"], is_locked, entries)

    # --- Period totals ---
    _render_period_totals(entries, employees)

    # --- Workflow buttons ---
    if period["status"] == "draft":
        st.divider()
        all_computed = all(e["id"] in entries for e in employees)

        col1, col2, col3 = st.columns([2, 1, 1])
        with col2:
            if st.button(
                "Submit for Review",
                type="primary",
                disabled=not all_computed,
                width="stretch",
            ):
                _update_pay_period(period["id"], {"status": "reviewed"})
                st.success("Pay period submitted for review.")
                st.rerun()

        if not all_computed:
            st.caption("Compute all employees before submitting for review.")

    elif period["status"] == "reviewed":
        st.divider()
        reviewer_name = st.text_input("Reviewer Name", placeholder="e.g. Juan dela Cruz")
        col1, col2, col3 = st.columns([2, 1, 1])
        with col2:
            if st.button(
                "Approve & Finalize",
                type="primary",
                disabled=not reviewer_name.strip(),
                width="stretch",
            ):
                from datetime import datetime
                _update_pay_period(period["id"], {
                    "status": "finalized",
                    "reviewed_by": reviewer_name.strip(),
                    "reviewed_at": datetime.now().isoformat(),
                })
                st.success(f"Approved by {reviewer_name.strip()}. Pay period finalized!")
                st.rerun()

        if not reviewer_name.strip():
            st.caption("Enter reviewer name to approve and finalize.")

    elif period["status"] == "finalized":
        st.divider()
        col1, col2, col3 = st.columns([2, 1, 1])
        with col3:
            if st.button("Mark as Paid", width="stretch"):
                _update_pay_period(period["id"], {"status": "paid"})
                st.rerun()

