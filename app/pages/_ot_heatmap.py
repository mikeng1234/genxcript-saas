"""
Workforce Analytics — attendance, overtime, late, and undertime analytics.

Tabs:
  1. 📊 OT Analytics    — Heatmaps + Top Contributors (with dept + shift)
  2. ⏰ Late Monitoring  — Top late employees + per-employee 3-month calendar grid
  3. ⏱ Undertime        — Top undertime employees + per-employee 3-month calendar grid
  4. ☕ Break Monitoring — Scheduled vs actual break analysis
"""

from __future__ import annotations

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import date, timedelta
from calendar import monthrange

from app.db_helper import get_db, get_company_id
from app.styles import inject_css


# ── Constants ────────────────────────────────────────────────────────────────

_DOW_ORDER   = ["Monday", "Tuesday", "Wednesday", "Thursday",
                 "Friday", "Saturday", "Sunday"]
_MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# ── Data helpers ─────────────────────────────────────────────────────────────

def _load_ot_data(year: int) -> list[dict]:
    """Return all approved OT requests for the given year, company-scoped."""
    result = (
        get_db().table("overtime_requests")
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
    Returns {employee_id: {name, department, shift_name}}.
    """
    db         = get_db()
    company_id = get_company_id()

    emps = (
        db.table("employees")
        .select("id, first_name, last_name, schedule_id")
        .eq("company_id", company_id)
        .execute()
    )

    # Load schedule names
    sched_map: dict[str, str] = {}
    try:
        scheds = db.table("schedules").select("id, name").eq("company_id", company_id).execute()
        sched_map = {s["id"]: s["name"] for s in (scheds.data or [])}
    except Exception:
        pass

    emp_map: dict = {}
    for e in (emps.data or []):
        sid = e.get("schedule_id")
        emp_map[e["id"]] = {
            "name":       f"{(e.get('last_name') or '').strip()}, {(e.get('first_name') or '').strip()}",
            "department": "",
            "shift":      sched_map.get(sid, "—") if sid else "—",
        }

    # Enrich with department
    try:
        profiles = db.table("employee_profiles").select("employee_id, department").execute()
        for p in (profiles.data or []):
            eid = p.get("employee_id")
            if eid and eid in emp_map and p.get("department"):
                emp_map[eid]["department"] = p["department"]
    except Exception:
        pass

    return emp_map


def _load_time_logs(start_date: date, end_date: date) -> list[dict]:
    """Return time_logs rows for the given date range, company-scoped."""
    result = (
        get_db().table("time_logs")
        .select(
            "employee_id, work_date, late_minutes, undertime_minutes, "
            "gross_hours, expected_hours, status, time_in, time_out, "
            "break_out, break_in, actual_break_minutes, overbreak_minutes"
        )
        .eq("company_id", get_company_id())
        .gte("work_date", str(start_date))
        .lte("work_date", str(end_date))
        .execute()
    )
    return result.data or []


# ── Page ─────────────────────────────────────────────────────────────────────

def render() -> None:
    inject_css()
    st.title("Workforce Analytics")
    st.caption("Overtime, attendance, late, and undertime patterns at a glance.")

    today        = date.today()
    current_year = today.year
    year_options = list(range(current_year, current_year - 4, -1))

    col_year, _ = st.columns([1, 4])
    with col_year:
        selected_year = st.selectbox("Year", year_options, index=0, key="wa_year")

    # ── Top-level tabs ────────────────────────────────────────────────────────
    tab_ot, tab_late, tab_ut, tab_brk = st.tabs([
        "📊 OT Analytics",
        "⏰ Late Monitoring",
        "⏱ Undertime",
        "☕ Break Monitoring",
    ])

    # =========================================================================
    # TAB 1 — OT Analytics (existing heatmaps + improved Top Contributors)
    # =========================================================================
    with tab_ot:
        ot_data = _load_ot_data(selected_year)
        emp_map = _load_employee_map()

        if not ot_data:
            st.info(
                f"No approved overtime requests found for **{selected_year}**. "
                "Patterns will appear here once OT requests are approved.",
                icon="ℹ️"
            )
        else:
            df = pd.DataFrame(ot_data)
            df["ot_date"]      = pd.to_datetime(df["ot_date"])
            df["hours"]        = pd.to_numeric(df["hours"], errors="coerce").fillna(0)
            df["day_of_week"]  = df["ot_date"].dt.day_name()
            df["month_name"]   = df["ot_date"].dt.strftime("%b")
            df["month_num"]    = df["ot_date"].dt.month
            df["employee_name"] = df["employee_id"].map(
                lambda eid: emp_map.get(eid, {}).get("name", "Unknown")
            )
            df["department"]   = df["employee_id"].map(
                lambda eid: emp_map.get(eid, {}).get("department", "")
            )
            df["shift"]        = df["employee_id"].map(
                lambda eid: emp_map.get(eid, {}).get("shift", "—")
            )

            ot_sub1, ot_sub2, ot_sub3 = st.tabs([
                "Calendar Heat Map", "By Employee", "Day of Week"
            ])

            # ── OT sub-tab 1: Calendar Heat Map ──────────────────────────────
            with ot_sub1:
                pivot = (
                    df.groupby(["month_name", "day_of_week"])["hours"]
                    .sum().reset_index()
                    .pivot(index="month_name", columns="day_of_week", values="hours")
                    .fillna(0)
                )
                pivot = pivot.reindex(
                    index=[m for m in _MONTH_ORDER if m in pivot.index],
                    columns=[d for d in _DOW_ORDER  if d in pivot.columns],
                )
                fig1 = px.imshow(
                    pivot,
                    labels=dict(x="Day of Week", y="Month", color="OT Hours"),
                    color_continuous_scale="YlOrRd",
                    title=f"Approved OT Hours — Day × Month  ({selected_year})",
                    text_auto=".1f", aspect="auto",
                )
                fig1.update_layout(height=420, margin=dict(l=0, r=0, t=50, b=0),
                                   coloraxis_colorbar=dict(title="hrs"))
                fig1.update_xaxes(side="bottom")
                st.plotly_chart(fig1, use_container_width=True)

                total_hrs     = df["hours"].sum()
                peak_day      = df.groupby("day_of_week")["hours"].sum().idxmax()
                peak_month_nm = df.groupby("month_num")["hours"].sum().idxmax()
                peak_month    = _MONTH_ORDER[peak_month_nm - 1]
                n_emp_ot      = df["employee_id"].nunique()
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total OT Hours",    f"{total_hrs:.1f} hrs")
                c2.metric("Peak Day of Week",  peak_day)
                c3.metric("Peak Month",        peak_month)
                c4.metric("Employees with OT", n_emp_ot)

            # ── OT sub-tab 2: By Employee + Top Contributors ──────────────────
            with ot_sub2:
                emp_month = (
                    df.groupby(["employee_name", "month_name"])["hours"]
                    .sum().reset_index()
                    .pivot(index="employee_name", columns="month_name", values="hours")
                    .fillna(0)
                )
                emp_month = emp_month.reindex(
                    columns=[m for m in _MONTH_ORDER if m in emp_month.columns]
                )
                emp_month["_total"] = emp_month.sum(axis=1)
                emp_month = emp_month.sort_values("_total", ascending=False).drop(columns=["_total"])

                fig2 = px.imshow(
                    emp_month,
                    labels=dict(x="Month", y="Employee", color="OT Hours"),
                    color_continuous_scale="Blues",
                    title=f"OT Hours per Employee  ({selected_year})",
                    text_auto=".1f", aspect="auto",
                )
                fig2.update_layout(
                    height=max(300, len(emp_month) * 35 + 120),
                    margin=dict(l=0, r=0, t=50, b=0),
                    coloraxis_colorbar=dict(title="hrs"),
                )
                st.plotly_chart(fig2, use_container_width=True)

                # Top Contributors with Dept + Shift
                st.subheader("Top OT Contributors")
                top_agg = (
                    df.groupby(["employee_id", "employee_name", "department", "shift"])["hours"]
                    .sum().reset_index()
                    .sort_values("hours", ascending=False)
                    .head(15)
                    .reset_index(drop=True)
                )
                top_agg.index += 1
                top_agg = top_agg.rename(columns={
                    "employee_name": "Employee",
                    "department":    "Department",
                    "shift":         "Shift",
                    "hours":         "Total OT Hours",
                })
                top_agg["Total OT Hours"] = top_agg["Total OT Hours"].map("{:.1f} hrs".format)
                top_agg = top_agg.drop(columns=["employee_id"])
                st.dataframe(top_agg, use_container_width=True)

            # ── OT sub-tab 3: Day of Week + Department breakdown ──────────────
            with ot_sub3:
                dow_df = (
                    df.groupby("day_of_week")["hours"].sum()
                    .reindex(_DOW_ORDER).fillna(0).reset_index()
                )
                dow_df.columns = ["Day", "Hours"]
                fig3 = px.bar(
                    dow_df, x="Day", y="Hours", color="Hours",
                    color_continuous_scale="YlOrRd",
                    title=f"Total OT Hours by Day of Week  ({selected_year})",
                    labels={"Hours": "Total OT Hours"}, text_auto=".1f",
                )
                fig3.update_coloraxes(showscale=False)
                fig3.update_layout(height=400, margin=dict(l=0, r=0, t=50, b=0),
                                   xaxis_title=None)
                st.plotly_chart(fig3, use_container_width=True)

                has_dept = df["department"].ne("").any()
                if has_dept:
                    st.subheader("By Department")
                    dept_pivot = (
                        df[df["department"] != ""]
                        .groupby(["department", "day_of_week"])["hours"]
                        .sum().reset_index()
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
                        text_auto=".1f", aspect="auto",
                    )
                    fig4.update_layout(
                        height=max(250, len(dept_pivot) * 50 + 120),
                        margin=dict(l=0, r=0, t=50, b=0),
                    )
                    st.plotly_chart(fig4, use_container_width=True)

    # =========================================================================
    # TAB 2 — Late Monitoring
    # =========================================================================
    with tab_late:
        # Date range: current year Jan 1 to today
        range_start = date(selected_year, 1, 1)
        range_end   = min(date(selected_year, 12, 31), today)
        logs_raw    = _load_time_logs(range_start, range_end)
        emp_map2    = _load_employee_map()

        late_rows = [r for r in logs_raw if (r.get("late_minutes") or 0) > 0]

        if not late_rows:
            st.info(f"No late records found for **{selected_year}**.", icon="ℹ️")
        else:
            df_late = pd.DataFrame(late_rows)
            df_late["late_minutes"] = pd.to_numeric(df_late["late_minutes"], errors="coerce").fillna(0)
            df_late["employee_name"] = df_late["employee_id"].map(
                lambda eid: emp_map2.get(eid, {}).get("name", "Unknown")
            )
            df_late["department"] = df_late["employee_id"].map(
                lambda eid: emp_map2.get(eid, {}).get("department", "")
            )

            # ── Summary metrics ───────────────────────────────────────────────
            total_late_days = len(df_late)
            total_late_mins = int(df_late["late_minutes"].sum())
            n_late_emps     = df_late["employee_id"].nunique()
            avg_late        = round(df_late["late_minutes"].mean(), 1)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Late Incidents", total_late_days)
            c2.metric("Total Late Minutes",   f"{total_late_mins:,} min")
            c3.metric("Employees Affected",   n_late_emps)
            c4.metric("Avg Late (per incident)", f"{avg_late} min")

            st.divider()

            # ── Top late employees table with expandable 3-month calendar ─────
            st.subheader("Top Late Employees")
            agg = (
                df_late.groupby(["employee_id", "employee_name", "department"])
                .agg(count=("late_minutes", "count"), total_mins=("late_minutes", "sum"))
                .reset_index()
                .sort_values("total_mins", ascending=False)
            )
            agg["avg_mins"] = (agg["total_mins"] / agg["count"]).round(1)

            for _, row in agg.iterrows():
                eid   = row["employee_id"]
                ename = row["employee_name"]
                dept  = row["department"] or "—"
                col_info, col_btn = st.columns([8, 1])
                with col_info:
                    st.markdown(
                        f"**{ename}** &nbsp;·&nbsp; {dept} &nbsp;·&nbsp; "
                        f"🔴 **{int(row['count'])}× late** &nbsp;·&nbsp; "
                        f"⏱ **{int(row['total_mins'])} min total** &nbsp;·&nbsp; "
                        f"avg {row['avg_mins']} min/incident"
                    )
                with col_btn:
                    if st.button(
                        "", key=f"late_cal_{eid}", icon="📅",
                        help="Show 3-month late calendar",
                    ):
                        toggle_key = f"show_late_cal_{eid}"
                        st.session_state[toggle_key] = not st.session_state.get(toggle_key, False)

                # 3-month heatmap calendar
                if st.session_state.get(f"show_late_cal_{eid}", False):
                    # Last 3 full months + current month
                    cal_end   = today
                    cal_start = (today.replace(day=1) - timedelta(days=60)).replace(day=1)
                    emp_logs  = df_late[(df_late["employee_id"] == eid) &
                                        (df_late["work_date"] >= str(cal_start)) &
                                        (df_late["work_date"] <= str(cal_end))]
                    if not emp_logs.empty:
                        cal_df = emp_logs.copy()
                        cal_df["work_date"] = pd.to_datetime(cal_df["work_date"])
                        cal_df["week"]      = cal_df["work_date"].dt.isocalendar().week.astype(str)
                        cal_df["dow"]       = cal_df["work_date"].dt.day_name()
                        cal_df["label"]     = cal_df["work_date"].dt.strftime("%b %d")

                        fig_cal = px.scatter(
                            cal_df,
                            x="label",
                            y="dow",
                            size="late_minutes",
                            color="late_minutes",
                            color_continuous_scale="Reds",
                            text="late_minutes",
                            title=f"Late Minutes — {ename} (last 3 months)",
                            labels={"label": "Date", "dow": "Day", "late_minutes": "Late (min)"},
                            size_max=40,
                        )
                        fig_cal.update_traces(textposition="middle center",
                                              textfont=dict(color="white", size=10))
                        fig_cal.update_layout(
                            height=320,
                            margin=dict(l=0, r=0, t=50, b=0),
                            yaxis=dict(categoryorder="array",
                                       categoryarray=list(reversed(_DOW_ORDER))),
                        )
                        st.plotly_chart(fig_cal, use_container_width=True,
                                        key=f"late_plot_{eid}")
                    else:
                        st.caption("No late records in the last 3 months.")

    # =========================================================================
    # TAB 3 — Undertime Monitoring
    # =========================================================================
    with tab_ut:
        range_start3 = date(selected_year, 1, 1)
        range_end3   = min(date(selected_year, 12, 31), today)
        logs_raw3    = _load_time_logs(range_start3, range_end3)
        emp_map3     = _load_employee_map()

        ut_rows = [r for r in logs_raw3 if (r.get("undertime_minutes") or 0) > 0]

        if not ut_rows:
            st.info(f"No undertime records found for **{selected_year}**.", icon="ℹ️")
        else:
            df_ut = pd.DataFrame(ut_rows)
            df_ut["undertime_minutes"] = pd.to_numeric(df_ut["undertime_minutes"], errors="coerce").fillna(0)
            df_ut["employee_name"] = df_ut["employee_id"].map(
                lambda eid: emp_map3.get(eid, {}).get("name", "Unknown")
            )
            df_ut["department"] = df_ut["employee_id"].map(
                lambda eid: emp_map3.get(eid, {}).get("department", "")
            )

            total_ut_days = len(df_ut)
            total_ut_mins = int(df_ut["undertime_minutes"].sum())
            n_ut_emps     = df_ut["employee_id"].nunique()
            avg_ut        = round(df_ut["undertime_minutes"].mean(), 1)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Undertime Incidents", total_ut_days)
            c2.metric("Total Undertime Minutes",   f"{total_ut_mins:,} min")
            c3.metric("Employees Affected",        n_ut_emps)
            c4.metric("Avg Undertime (per incident)", f"{avg_ut} min")

            st.divider()
            st.subheader("Top Undertime Employees")

            agg_ut = (
                df_ut.groupby(["employee_id", "employee_name", "department"])
                .agg(count=("undertime_minutes", "count"), total_mins=("undertime_minutes", "sum"))
                .reset_index()
                .sort_values("total_mins", ascending=False)
            )
            agg_ut["avg_mins"] = (agg_ut["total_mins"] / agg_ut["count"]).round(1)

            for _, row in agg_ut.iterrows():
                eid   = row["employee_id"]
                ename = row["employee_name"]
                dept  = row["department"] or "—"
                col_info, col_btn = st.columns([8, 1])
                with col_info:
                    st.markdown(
                        f"**{ename}** &nbsp;·&nbsp; {dept} &nbsp;·&nbsp; "
                        f"🟠 **{int(row['count'])}× undertime** &nbsp;·&nbsp; "
                        f"⏱ **{int(row['total_mins'])} min total** &nbsp;·&nbsp; "
                        f"avg {row['avg_mins']} min/incident"
                    )
                with col_btn:
                    if st.button(
                        "", key=f"ut_cal_{eid}", icon="📅",
                        help="Show 3-month undertime calendar",
                    ):
                        toggle_key = f"show_ut_cal_{eid}"
                        st.session_state[toggle_key] = not st.session_state.get(toggle_key, False)

                if st.session_state.get(f"show_ut_cal_{eid}", False):
                    cal_end   = today
                    cal_start = (today.replace(day=1) - timedelta(days=60)).replace(day=1)
                    emp_logs  = df_ut[(df_ut["employee_id"] == eid) &
                                      (df_ut["work_date"] >= str(cal_start)) &
                                      (df_ut["work_date"] <= str(cal_end))]
                    if not emp_logs.empty:
                        cal_df = emp_logs.copy()
                        cal_df["work_date"] = pd.to_datetime(cal_df["work_date"])
                        cal_df["dow"]   = cal_df["work_date"].dt.day_name()
                        cal_df["label"] = cal_df["work_date"].dt.strftime("%b %d")
                        fig_ut = px.scatter(
                            cal_df, x="label", y="dow",
                            size="undertime_minutes", color="undertime_minutes",
                            color_continuous_scale="Oranges",
                            text="undertime_minutes",
                            title=f"Undertime Minutes — {ename} (last 3 months)",
                            labels={"label": "Date", "dow": "Day",
                                    "undertime_minutes": "Undertime (min)"},
                            size_max=40,
                        )
                        fig_ut.update_traces(textposition="middle center",
                                             textfont=dict(color="white", size=10))
                        fig_ut.update_layout(
                            height=320,
                            margin=dict(l=0, r=0, t=50, b=0),
                            yaxis=dict(categoryorder="array",
                                       categoryarray=list(reversed(_DOW_ORDER))),
                        )
                        st.plotly_chart(fig_ut, use_container_width=True,
                                        key=f"ut_plot_{eid}")
                    else:
                        st.caption("No undertime records in the last 3 months.")

    # =========================================================================
    # TAB 4 — Break Monitoring
    # =========================================================================
    with tab_brk:
        st.info(
            "**Break Monitoring** tracks when employees clock out for break and clock back in. "
            "This requires break clock-out / clock-in to be logged via the Employee Portal. "
            "Once break times are recorded, this tab will show overbreak counts and minutes per employee.",
            icon="☕",
        )

        # Derive implied break utilization from existing time_logs data
        range_start4 = date(selected_year, 1, 1)
        range_end4   = min(date(selected_year, 12, 31), today)
        logs_raw4    = _load_time_logs(range_start4, range_end4)
        emp_map4     = _load_employee_map()

        # Load scheduled break_minutes via schedules join
        try:
            scheds_raw = (
                get_db().table("schedules")
                .select("id, name, break_minutes")
                .eq("company_id", get_company_id())
                .execute()
            ).data or []
            sched_break_map = {s["id"]: int(s.get("break_minutes", 60)) for s in scheds_raw}
        except Exception:
            sched_break_map = {}

        # Use real break data (break_out/break_in columns) where available;
        # fall back to implied break (span − gross) for rows without portal punches.
        break_data = []
        has_real_break = False
        for r in logs_raw4:
            if not r.get("time_in") or not r.get("time_out"):
                continue
            try:
                from backend.dtr import _parse_time, _to_min
                # ── Real break data takes priority ──────────────────────────────
                if r.get("break_in") and r.get("actual_break_minutes") is not None:
                    actual_break_min = int(r["actual_break_minutes"] or 0)
                    overbreak_min    = int(r.get("overbreak_minutes") or 0)
                    is_real          = True
                    has_real_break   = True
                else:
                    # ── Implied break: span − gross_hours ───────────────────────
                    in_m  = _to_min(_parse_time(r["time_in"]))
                    out_m = _to_min(_parse_time(r["time_out"]))
                    if out_m < in_m:
                        out_m += 1440
                    gross_h = float(r.get("gross_hours") or 0)
                    span_m  = out_m - in_m
                    actual_break_min = max(0, span_m - int(gross_h * 60))
                    overbreak_min    = 0
                    is_real          = False

                break_data.append({
                    "employee_id":    r["employee_id"],
                    "work_date":      r["work_date"],
                    "break_min":      actual_break_min,
                    "overbreak_min":  overbreak_min,
                    "is_real":        is_real,
                })
            except Exception:
                continue

        if break_data:
            df_brk = pd.DataFrame(break_data)
            df_brk["employee_name"] = df_brk["employee_id"].map(
                lambda eid: emp_map4.get(eid, {}).get("name", "Unknown")
            )
            agg_brk = (
                df_brk.groupby(["employee_id", "employee_name"])
                .agg(
                    days=("break_min", "count"),
                    total_break=("break_min", "sum"),
                    avg_break=("break_min", "mean"),
                    total_overbreak=("overbreak_min", "sum"),
                    real_days=("is_real", "sum"),
                )
                .reset_index()
                .sort_values("total_overbreak", ascending=False)
            )
            agg_brk["avg_break"]     = agg_brk["avg_break"].round(1)
            agg_brk["real_days"]     = agg_brk["real_days"].astype(int)

            st.subheader("Break Duration Summary")
            if has_real_break:
                st.caption(
                    "Real break times from portal clock-out/in where available; "
                    "implied break (span − gross hours) used for remaining rows."
                )
            else:
                st.caption(
                    "Implied break = total time at work minus computed gross hours. "
                    "Enable break clock-out/in in the portal for precise tracking "
                    "and overbreak detection."
                )

            disp_df = agg_brk[
                ["employee_name", "days", "avg_break", "total_break", "total_overbreak", "real_days"]
            ].rename(columns={
                "employee_name":  "Employee",
                "days":           "Days Logged",
                "avg_break":      "Avg Break (min)",
                "total_break":    "Total Break (min)",
                "total_overbreak": "Overbreak (min)",
                "real_days":      "Portal Days",
            })
            disp_df.index = range(1, len(disp_df) + 1)
            st.dataframe(
                disp_df,
                use_container_width=True,
                column_config={
                    "Overbreak (min)": st.column_config.NumberColumn(
                        "Overbreak (min)",
                        help="Minutes beyond scheduled break; 0 for implied-only rows.",
                        format="%d",
                    ),
                    "Portal Days": st.column_config.NumberColumn(
                        "Portal Days",
                        help="Number of days with real break tracking via employee portal.",
                        format="%d",
                    ),
                },
            )
        else:
            st.caption("No time log data yet for the selected year.")
