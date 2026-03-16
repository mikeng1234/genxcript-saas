"""
OT Heat Maps — Phase 4A Visibility Layer

Visualizes approved overtime patterns across three views:
  1. Calendar Heat Map   — Day of Week × Month grid (all employees combined)
  2. By Employee         — Employee × Month grid (who works OT most)
  3. Day of Week         — Bar chart + optional department breakdown
"""

from __future__ import annotations

import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import date

from app.db_helper import get_db, get_company_id


# ── Constants ────────────────────────────────────────────────────────────────

_DOW_ORDER   = ["Monday", "Tuesday", "Wednesday", "Thursday",
                 "Friday", "Saturday", "Sunday"]
_MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# ── Data helpers ─────────────────────────────────────────────────────────────

def _load_ot_data(year: int) -> list[dict]:
    """Return all approved OT requests for the given year, company-scoped."""
    db = get_db()
    result = (
        db.table("overtime_requests")
        .select("id, employee_id, ot_date, hours, status")
        .eq("company_id", get_company_id())
        .eq("status", "approved")
        .gte("ot_date", f"{year}-01-01")
        .lte("ot_date", f"{year}-12-31")
        .execute()
    )
    return result.data or []


def _load_employee_map() -> dict:
    """
    Returns {employee_id: {"name": "Last, First", "department": ""}}.
    Department is left empty ("") when employee_profiles has no row for the employee.
    """
    db         = get_db()
    company_id = get_company_id()

    emps = (
        db.table("employees")
        .select("id, first_name, last_name")
        .eq("company_id", company_id)
        .execute()
    )
    emp_map: dict = {}
    for e in (emps.data or []):
        emp_map[e["id"]] = {
            "name":       f"{(e.get('last_name') or '').strip()}, {(e.get('first_name') or '').strip()}",
            "department": "",
        }

    # Optional: enrich with department from employee_profiles
    try:
        profiles = (
            db.table("employee_profiles")
            .select("employee_id, department")
            .execute()
        )
        for p in (profiles.data or []):
            eid = p.get("employee_id")
            if eid and eid in emp_map and p.get("department"):
                emp_map[eid]["department"] = p["department"]
    except Exception:
        pass

    return emp_map


# ── Page ─────────────────────────────────────────────────────────────────────

def render() -> None:
    st.title("🔥 OT Heat Maps")
    st.caption("Visualize which days and employees drive overtime spikes.")

    # ── Year selector ─────────────────────────────────────────────────────────
    current_year  = date.today().year
    year_options  = list(range(current_year, current_year - 4, -1))
    selected_year = st.selectbox("Year", year_options, index=0)

    # ── Load data ─────────────────────────────────────────────────────────────
    ot_data  = _load_ot_data(selected_year)
    emp_map  = _load_employee_map()

    if not ot_data:
        st.info(
            f"No approved overtime requests found for **{selected_year}**. "
            "Once employees submit OT requests and they are approved, patterns will appear here."
        )
        return

    # ── Build DataFrame ───────────────────────────────────────────────────────
    df = pd.DataFrame(ot_data)
    df["ot_date"] = pd.to_datetime(df["ot_date"])
    df["hours"]   = pd.to_numeric(df["hours"], errors="coerce").fillna(0)

    df["day_of_week"]    = df["ot_date"].dt.day_name()
    df["month_name"]     = df["ot_date"].dt.strftime("%b")
    df["month_num"]      = df["ot_date"].dt.month
    df["employee_name"]  = df["employee_id"].map(
        lambda eid: emp_map.get(eid, {}).get("name", "Unknown")
    )
    df["department"]     = df["employee_id"].map(
        lambda eid: emp_map.get(eid, {}).get("department", "")
    )

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_cal, tab_emp, tab_dow = st.tabs([
        "📅 Calendar Heat Map",
        "👤 By Employee",
        "📊 Day of Week",
    ])

    # =========================================================================
    # Tab 1 — Calendar Heat Map (Day of Week × Month)
    # =========================================================================
    with tab_cal:
        pivot = (
            df.groupby(["month_name", "day_of_week"])["hours"]
            .sum()
            .reset_index()
            .pivot(index="month_name", columns="day_of_week", values="hours")
            .fillna(0)
        )

        # Enforce calendar ordering
        pivot = pivot.reindex(
            index=[m for m in _MONTH_ORDER if m in pivot.index],
            columns=[d for d in _DOW_ORDER  if d in pivot.columns],
        )

        fig1 = px.imshow(
            pivot,
            labels=dict(x="Day of Week", y="Month", color="OT Hours"),
            color_continuous_scale="YlOrRd",
            title=f"Approved OT Hours — Day × Month  ({selected_year})",
            text_auto=".1f",
            aspect="auto",
        )
        fig1.update_layout(
            height=420,
            margin=dict(l=0, r=0, t=50, b=0),
            coloraxis_colorbar=dict(title="hrs"),
        )
        fig1.update_xaxes(side="bottom")
        st.plotly_chart(fig1, use_container_width=True)

        # Summary metrics
        total_hrs     = df["hours"].sum()
        peak_day      = df.groupby("day_of_week")["hours"].sum().idxmax()
        peak_month_nm = df.groupby("month_num")["hours"].sum().idxmax()
        peak_month    = _MONTH_ORDER[peak_month_nm - 1]
        n_emp_ot      = df["employee_id"].nunique()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total OT Hours",     f"{total_hrs:.1f} hrs")
        c2.metric("Peak Day of Week",   peak_day)
        c3.metric("Peak Month",         peak_month)
        c4.metric("Employees with OT",  n_emp_ot)

    # =========================================================================
    # Tab 2 — By Employee (Employee × Month)
    # =========================================================================
    with tab_emp:
        emp_month = (
            df.groupby(["employee_name", "month_name"])["hours"]
            .sum()
            .reset_index()
            .pivot(index="employee_name", columns="month_name", values="hours")
            .fillna(0)
        )

        # Reorder months Jan→Dec
        emp_month = emp_month.reindex(
            columns=[m for m in _MONTH_ORDER if m in emp_month.columns]
        )

        # Sort employees by total OT descending
        emp_month["_total"] = emp_month.sum(axis=1)
        emp_month = emp_month.sort_values("_total", ascending=False).drop(columns=["_total"])

        chart_height = max(300, len(emp_month) * 35 + 120)

        fig2 = px.imshow(
            emp_month,
            labels=dict(x="Month", y="Employee", color="OT Hours"),
            color_continuous_scale="Blues",
            title=f"OT Hours per Employee  ({selected_year})",
            text_auto=".1f",
            aspect="auto",
        )
        fig2.update_layout(
            height=chart_height,
            margin=dict(l=0, r=0, t=50, b=0),
            coloraxis_colorbar=dict(title="hrs"),
        )
        st.plotly_chart(fig2, use_container_width=True)

        # Top 10 table
        st.subheader("Top OT Contributors")
        top_df = (
            df.groupby("employee_name")["hours"]
            .sum()
            .sort_values(ascending=False)
            .head(10)
            .reset_index()
            .rename(columns={"employee_name": "Employee", "hours": "Total OT Hours"})
        )
        top_df["Total OT Hours"] = top_df["Total OT Hours"].map("{:.1f} hrs".format)
        top_df.index = top_df.index + 1   # 1-based rank
        st.dataframe(top_df, use_container_width=True)

    # =========================================================================
    # Tab 3 — Day of Week bar + optional department heatmap
    # =========================================================================
    with tab_dow:
        dow_df = (
            df.groupby("day_of_week")["hours"]
            .sum()
            .reindex(_DOW_ORDER)
            .fillna(0)
            .reset_index()
        )
        dow_df.columns = ["Day", "Hours"]

        fig3 = px.bar(
            dow_df,
            x="Day", y="Hours",
            color="Hours",
            color_continuous_scale="YlOrRd",
            title=f"Total OT Hours by Day of Week  ({selected_year})",
            labels={"Hours": "Total OT Hours"},
            text_auto=".1f",
        )
        fig3.update_coloraxes(showscale=False)
        fig3.update_layout(
            height=400,
            margin=dict(l=0, r=0, t=50, b=0),
            xaxis_title=None,
        )
        st.plotly_chart(fig3, use_container_width=True)

        # Department breakdown — only if at least one employee has a department set
        has_dept = df["department"].ne("").any()
        if has_dept:
            st.subheader("By Department")
            dept_df = df[df["department"] != ""]
            dept_pivot = (
                dept_df.groupby(["department", "day_of_week"])["hours"]
                .sum()
                .reset_index()
                .pivot(index="department", columns="day_of_week", values="hours")
                .fillna(0)
            )
            dept_pivot = dept_pivot.reindex(
                columns=[d for d in _DOW_ORDER if d in dept_pivot.columns]
            )

            fig4 = px.imshow(
                dept_pivot,
                labels=dict(x="Day of Week", y="Department", color="OT Hours"),
                color_continuous_scale="Purples",
                title="OT Hours by Department × Day of Week",
                text_auto=".1f",
                aspect="auto",
            )
            fig4.update_layout(
                height=max(250, len(dept_pivot) * 50 + 120),
                margin=dict(l=0, r=0, t=50, b=0),
                coloraxis_colorbar=dict(title="hrs"),
            )
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.caption(
                "💡 Set employee departments in **Company Setup → Employees** "
                "to enable the department breakdown chart."
            )
