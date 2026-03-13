"""
Dashboard — Streamlit page.

The landing page showing a snapshot of the company's payroll status:
- Key metrics (headcount, payroll cost, net pay)
- Current/latest pay period status
- Government remittance summary
- Upcoming deadlines
- Recent payroll history
"""

import streamlit as st
from datetime import date
from app.db_helper import get_db, get_company_id
from backend.deadlines import get_remittance_deadlines, load_holiday_set
import plotly.express as px
import pandas as pd


# ============================================================
# Helpers
# ============================================================

def _fmt(centavos: int) -> str:
    return f"₱{centavos / 100:,.2f}"


def _load_company() -> dict:
    db = get_db()
    result = db.table("companies").select("*").eq("id", get_company_id()).execute()
    return result.data[0] if result.data else {}


def _load_active_employee_count() -> int:
    db = get_db()
    result = (
        db.table("employees")
        .select("id", count="exact")
        .eq("company_id", get_company_id())
        .eq("is_active", True)
        .execute()
    )
    return result.count or 0


def _load_all_employee_count() -> int:
    db = get_db()
    result = (
        db.table("employees")
        .select("id", count="exact")
        .eq("company_id", get_company_id())
        .execute()
    )
    return result.count or 0


def _load_pay_periods() -> list[dict]:
    db = get_db()
    result = (
        db.table("pay_periods")
        .select("*")
        .eq("company_id", get_company_id())
        .order("period_start", desc=True)
        .limit(10)
        .execute()
    )
    return result.data


def _load_payroll_entries(pay_period_id: str) -> list[dict]:
    db = get_db()
    result = (
        db.table("payroll_entries")
        .select("*")
        .eq("pay_period_id", pay_period_id)
        .execute()
    )
    return result.data


def _load_payroll_history() -> list[dict]:
    """Load all finalized/paid periods with aggregate totals for charts."""
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
        entries = _load_payroll_entries(p["id"])
        if not entries:
            continue
        rows.append({
            "period": p["period_start"],
            "gross_pay": sum(e["gross_pay"] for e in entries) / 100,
            "net_pay":   sum(e["net_pay"]   for e in entries) / 100,
            "headcount": len(entries),
            "sss":       sum(e["sss_employee"]       + e["sss_employer"]       for e in entries) / 100,
            "philhealth":sum(e["philhealth_employee"] + e["philhealth_employer"] for e in entries) / 100,
            "pagibig":   sum(e["pagibig_employee"]   + e["pagibig_employer"]   for e in entries) / 100,
            "bir":       sum(e["withholding_tax"]    for e in entries) / 100,
        })
    return rows


# ============================================================
# Government Remittance Deadlines
# ============================================================

def _get_accurate_deadlines() -> list[dict]:
    """
    Load holidays from the database and compute deadlines adjusted
    for weekends and Philippine holidays.
    """
    db = get_db()
    today = date.today()
    holidays = load_holiday_set(db, year=today.year)
    return get_remittance_deadlines(today, holidays)


# ============================================================
# Main Page Render
# ============================================================

def render():
    company = _load_company()
    company_name = company.get("name", "Your Company")

    st.title(f"{company_name} — Dashboard")

    # ---- Charts (moved to top, above KPI block) ----
    st.divider()
    st.subheader("📊 Payroll Trends")

    history = _load_payroll_history()

    if len(history) < 2:
        st.info("Charts will appear once you have 2 or more finalized pay periods.")
    else:
        df = pd.DataFrame(history)

        # Row 1: Trend line (wide) + Deductions pie (narrow)
        col_trend, col_pie = st.columns([3, 2])

        with col_trend:
            fig_trend = px.line(
                df,
                x="period",
                y=["gross_pay", "net_pay"],
                labels={"value": "Amount (₱)", "period": "Period", "variable": ""},
                color_discrete_map={"gross_pay": "#1f77b4", "net_pay": "#2ca02c"},
                markers=True,
            )
            fig_trend.for_each_trace(
                lambda t: t.update(
                    name={"gross_pay": "Gross Pay", "net_pay": "Net Pay"}[t.name]
                )
            )
            fig_trend.update_layout(
                title="Payroll Cost Trend",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=0, r=0, t=48, b=0),
                hovermode="x unified",
            )
            st.plotly_chart(fig_trend, width="stretch")

        with col_pie:
            latest = history[-1]
            pie_labels = ["SSS", "PhilHealth", "Pag-IBIG", "BIR Withholding"]
            pie_values = [
                latest["sss"],
                latest["philhealth"],
                latest["pagibig"],
                latest["bir"],
            ]
            fig_pie = px.pie(
                names=pie_labels,
                values=pie_values,
                title=f"Deductions Breakdown ({latest['period'][:7]})",
                color_discrete_sequence=px.colors.qualitative.Set2,
                hole=0.35,
            )
            fig_pie.update_traces(textposition="inside", textinfo="percent+label")
            fig_pie.update_layout(
                showlegend=False,
                margin=dict(l=0, r=0, t=48, b=0),
            )
            st.plotly_chart(fig_pie, width="stretch")

        # Row 2: Headcount bar (full width)
        fig_hc = px.bar(
            df,
            x="period",
            y="headcount",
            labels={"headcount": "Employees Paid", "period": "Period"},
            title="Headcount per Pay Period",
            color_discrete_sequence=["#ff7f0e"],
            text="headcount",
        )
        fig_hc.update_traces(textposition="outside")
        fig_hc.update_layout(
            margin=dict(l=0, r=0, t=48, b=0),
            yaxis=dict(rangemode="tozero"),
        )
        st.plotly_chart(fig_hc, width="stretch")

    st.divider()

    # ---- Top KPI Metrics ----
    active_count = _load_active_employee_count()
    total_count = _load_all_employee_count()
    inactive_count = total_count - active_count
    periods = _load_pay_periods()

    # Find latest finalized/paid period for payroll totals
    latest_period = None
    latest_entries = []
    for p in periods:
        if p["status"] in ("finalized", "paid"):
            latest_period = p
            latest_entries = _load_payroll_entries(p["id"])
            break

    # Calculate totals from latest period
    total_gross = sum(e["gross_pay"] for e in latest_entries) if latest_entries else 0
    total_net = sum(e["net_pay"] for e in latest_entries) if latest_entries else 0
    total_er = sum(
        e["sss_employer"] + e["philhealth_employer"] + e["pagibig_employer"]
        for e in latest_entries
    ) if latest_entries else 0
    total_cost = total_gross + total_er  # total employer cost

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Active Employees", active_count, delta=f"{inactive_count} inactive" if inactive_count else None, delta_color="off")
    with col2:
        st.metric("Total Gross Pay", _fmt(total_gross))
    with col3:
        st.metric("Total Net Pay", _fmt(total_net))
    with col4:
        st.metric("Total Employer Cost", _fmt(total_cost), help="Gross pay + employer SSS, PhilHealth, Pag-IBIG")

    if latest_period:
        st.caption(f"Based on latest finalized period: {latest_period['period_start']} to {latest_period['period_end']}")
    else:
        st.caption("No finalized pay periods yet. Totals will appear after your first payroll run.")

    st.divider()

    # ---- Two-column layout: Pay Periods + Deadlines ----
    col_left, col_right = st.columns([3, 2])

    # ---- Left: Recent Pay Periods ----
    with col_left:
        st.subheader("Recent Pay Periods")

        if not periods:
            st.info("No pay periods yet. Go to Payroll Run to create one.")
        else:
            for p in periods[:5]:
                status = p["status"]
                color = {"draft": "blue", "finalized": "orange", "paid": "green"}.get(status, "gray")

                # Load entry count for this period
                entry_count = len(_load_payroll_entries(p["id"]))

                col_period, col_status, col_count = st.columns([3, 1, 1])
                with col_period:
                    st.text(f"{p['period_start']} to {p['period_end']}")
                with col_status:
                    st.markdown(f":{color}[{status.upper()}]")
                with col_count:
                    st.text(f"{entry_count} entries")

    # ---- Right: Government Remittance Deadlines ----
    with col_right:
        st.subheader("Remittance Deadlines")

        deadlines = _get_accurate_deadlines()

        for d in deadlines:
            days_until = d["days_until"]
            if days_until < 0:
                icon = "🔴"
                status = "OVERDUE"
            elif days_until <= 3:
                icon = "🟡"
                status = f"in {days_until} days"
            else:
                icon = "🟢"
                status = f"in {days_until} days"

            deadline_str = d["deadline"].strftime("%b %d")
            if d["deadline"] != d["raw_deadline"]:
                deadline_str += " (adjusted)"

            st.markdown(f"{icon} **{d['agency']}** ({d['form']}) — {deadline_str}  \n{d['description']} · *{status}*")

    st.divider()

    # ---- Government Remittance Summary (from latest period) ----
    if latest_entries:
        st.subheader("Government Remittance Summary")
        st.caption(f"Period: {latest_period['period_start']} to {latest_period['period_end']}")

        total_sss_ee = sum(e["sss_employee"] for e in latest_entries)
        total_sss_er = sum(e["sss_employer"] for e in latest_entries)
        total_ph_ee = sum(e["philhealth_employee"] for e in latest_entries)
        total_ph_er = sum(e["philhealth_employer"] for e in latest_entries)
        total_pi_ee = sum(e["pagibig_employee"] for e in latest_entries)
        total_pi_er = sum(e["pagibig_employer"] for e in latest_entries)
        total_wht = sum(e["withholding_tax"] for e in latest_entries)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown("**SSS**")
            st.text(f"Employee:  {_fmt(total_sss_ee)}")
            st.text(f"Employer:  {_fmt(total_sss_er)}")
            st.markdown(f"**Total:   {_fmt(total_sss_ee + total_sss_er)}**")

        with col2:
            st.markdown("**PhilHealth**")
            st.text(f"Employee:  {_fmt(total_ph_ee)}")
            st.text(f"Employer:  {_fmt(total_ph_er)}")
            st.markdown(f"**Total:   {_fmt(total_ph_ee + total_ph_er)}**")

        with col3:
            st.markdown("**Pag-IBIG**")
            st.text(f"Employee:  {_fmt(total_pi_ee)}")
            st.text(f"Employer:  {_fmt(total_pi_er)}")
            st.markdown(f"**Total:   {_fmt(total_pi_ee + total_pi_er)}**")

        with col4:
            st.markdown("**BIR Withholding Tax**")
            st.text(f"Total:     {_fmt(total_wht)}")
            st.markdown("")
            all_gov = (total_sss_ee + total_sss_er + total_ph_ee + total_ph_er
                       + total_pi_ee + total_pi_er + total_wht)
            st.markdown(f"**All Gov:  {_fmt(all_gov)}**")

