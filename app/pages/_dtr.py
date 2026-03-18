"""
Attendance & DTR — Admin page (Phase 4B)

Three tabs:
  📅 Daily Entry      — select a date, enter time-in/out for all employees
  📊 Attendance Summary — per-employee summary across a date range
  🔧 Corrections       — review and approve/reject employee DTR correction requests
"""

import streamlit as st
from datetime import date, datetime, time, timedelta, timezone
from app.db_helper import get_db, get_company_id, log_action
from app.styles import inject_css
from backend.dtr import (
    compute_dtr, compute_nsd_hours, resolve_schedule_for_date, schedule_expected_hours,
    nearest_location, haversine_distance_m, _parse_time,
)


# ============================================================
# Database helpers
# ============================================================

def _load_employees() -> list[dict]:
    return (
        get_db().table("employees")
        .select("id, employee_no, first_name, last_name, position, schedule_id")
        .eq("company_id", get_company_id())
        .eq("is_active", True)
        .order("last_name")
        .execute()
    ).data or []


def _load_schedules() -> dict:
    rows = (
        get_db().table("schedules")
        .select("*")
        .eq("company_id", get_company_id())
        .execute()
    ).data or []
    return {r["id"]: r for r in rows}


def _load_overrides_for_date(work_date: date) -> dict:
    rows = (
        get_db().table("schedule_overrides")
        .select("*")
        .eq("company_id", get_company_id())
        .eq("override_date", str(work_date))
        .execute()
    ).data or []
    return {(r["employee_id"], str(work_date)): r for r in rows}


def _load_time_logs_for_date(work_date: date) -> dict:
    rows = (
        get_db().table("time_logs")
        .select("*")
        .eq("company_id", get_company_id())
        .eq("work_date", str(work_date))
        .execute()
    ).data or []
    return {r["employee_id"]: r for r in rows}


def _load_time_logs_range(start: date, end: date) -> list[dict]:
    return (
        get_db().table("time_logs")
        .select("*")
        .eq("company_id", get_company_id())
        .gte("work_date", str(start))
        .lte("work_date", str(end))
        .execute()
    ).data or []


def _load_employee_profiles() -> dict:
    """Returns {employee_id: department}"""
    rows = (
        get_db().table("employee_profiles")
        .select("employee_id, department")
        .eq("company_id", get_company_id())
        .execute()
    ).data or []
    return {r["employee_id"]: (r.get("department") or "") for r in rows}


def _load_dept_names_from_table() -> list[str]:
    """Load structured department names for filter dropdowns."""
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
        return [r["name"] for r in (result.data or [])]
    except Exception:
        return []


def _upsert_time_log(row: dict):
    """Insert or update a time_log row. Uses UNIQUE(employee_id, work_date)."""
    existing = (
        get_db().table("time_logs")
        .select("id")
        .eq("employee_id", row["employee_id"])
        .eq("work_date", row["work_date"])
        .execute()
    ).data
    if existing:
        get_db().table("time_logs").update(row).eq("id", existing[0]["id"]).execute()
    else:
        row["company_id"] = get_company_id()
        get_db().table("time_logs").insert(row).execute()


def _load_corrections(status_filter: str = "pending") -> list[dict]:
    q = (
        get_db().table("dtr_corrections")
        .select("*, employees(first_name, last_name, employee_no)")
        .eq("company_id", get_company_id())
        .order("created_at", desc=True)
    )
    if status_filter != "all":
        q = q.eq("status", status_filter)
    return q.execute().data or []


def _update_correction(corr_id: str, status: str, admin_notes: str):
    get_db().table("dtr_corrections").update({
        "status": status,
        "admin_notes": admin_notes,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", corr_id).execute()


# ============================================================
# Helpers
# ============================================================

def _employee_display_name(emp: dict) -> str:
    return f"{emp['last_name']}, {emp['first_name']}"


def _status_html(status: str) -> str:
    mapping = {
        "present":    ('<i class="mdi mdi-check-circle-outline"></i>', "var(--gxp-success)", "var(--gxp-success-bg)"),
        "half_day":   ("½", "var(--gxp-warning)", "var(--gxp-warning-bg)"),
        "absent":     ('<i class="mdi mdi-close-circle-outline"></i>', "var(--gxp-danger)", "var(--gxp-danger-bg)"),
        "on_leave":   ('<i class="mdi mdi-umbrella-beach"></i>', "var(--gxp-accent)", "var(--gxp-accent-bg)"),
        "holiday":    ('<i class="mdi mdi-party-popper"></i>', "var(--gxp-accent)", "var(--gxp-accent-bg)"),
        "rest_day":   ('<i class="mdi mdi-sleep"></i>', "var(--gxp-text3)", "var(--gxp-surface2)"),
        "no_schedule": ("—", "var(--gxp-text3)", "var(--gxp-surface2)"),
    }
    icon, color, bg = mapping.get(status, ("?", "var(--gxp-text2)", "var(--gxp-surface)"))
    label = status.replace("_", " ").title()
    return (
        f'<span style="background:{bg};color:{color};padding:2px 8px;'
        f'border-radius:4px;font-size:12px;font-weight:600;">'
        f'{icon} {label}</span>'
    )


def _fmt_time(t) -> str:
    if t is None:
        return "—"
    if isinstance(t, str):
        return t[:5]
    return t.strftime("%H:%M")


def _fmt_mins(m: int) -> str:
    if not m:
        return "—"
    h, rem = divmod(m, 60)
    return f"{h}h {rem}m" if h else f"{rem}m"


# ============================================================
# Tab 1 — Daily Entry
# ============================================================

def _render_daily_entry():
    # ── Persistent save message (survives st.rerun) ───────────
    if "dtr_save_msg" in st.session_state:
        kind, msg = st.session_state.pop("dtr_save_msg")
        if kind == "success":
            st.success(msg)
        elif kind == "info":
            st.info(msg)
        else:
            st.error(msg)

    # ── Date navigation ──────────────────────────────────────
    # Separate backing key so the Today button can write freely without
    # hitting Streamlit's rule that forbids writing to a widget's own key
    # after it has been instantiated in the same run.
    if "dtr_nav_date" not in st.session_state:
        st.session_state["dtr_nav_date"] = date.today()

    # Pre-set the widget key BEFORE st.date_input() — only safe window.
    st.session_state["dtr_date_picker"] = st.session_state["dtr_nav_date"]

    col_date, _ = st.columns([2, 3])
    with col_date:
        work_date = st.date_input(
            "Date",
            key="dtr_date_picker",
            label_visibility="collapsed",
        )
        # Sync manual calendar picks back to the backing key
        st.session_state["dtr_nav_date"] = work_date

    if st.button("Today", key="dtr_today", help="Jump to today"):
        st.session_state["dtr_nav_date"] = date.today()
        st.rerun()

    st.caption(f"**{work_date.strftime('%A, %B %d, %Y')}**")

    # ── Load data ─────────────────────────────────────────────
    employees = _load_employees()
    schedules = _load_schedules()
    overrides = _load_overrides_for_date(work_date)
    existing  = _load_time_logs_for_date(work_date)

    if not employees:
        st.info("No active employees found.")
        return

    profiles = _load_employee_profiles()   # {employee_id: department}
    for emp in employees:
        emp["department"] = profiles.get(emp["id"], "")

    # ── Filter bar ────────────────────────────────────────────
    all_positions = sorted({(e.get("position") or "").strip() for e in employees} - {""})
    all_depts     = sorted({(e.get("department") or "").strip() for e in employees} - {""})
    _dept_names_structured = _load_dept_names_from_table()
    if _dept_names_structured:
        all_depts = _dept_names_structured
    de_s, de_p, de_d = st.columns([2, 1.5, 1.5])
    with de_s:
        de_search = st.text_input("Search", placeholder="Name or employee no…",
                                  label_visibility="collapsed", key="de_search")
    with de_p:
        de_sel_pos  = st.multiselect("Position",   all_positions, key="de_f_pos",  placeholder="All positions")
    with de_d:
        de_sel_dept = st.multiselect("Department", all_depts,     key="de_f_dept", placeholder="All departments")

    def _de_match(emp):
        if de_search:
            q = de_search.lower()
            name = f"{emp['last_name']} {emp['first_name']}".lower()
            if q not in name and q not in (emp.get("employee_no") or "").lower():
                return False
        if de_sel_pos  and (emp.get("position") or "") not in de_sel_pos:
            return False
        if de_sel_dept and (emp.get("department") or "") not in de_sel_dept:
            return False
        return True

    # ── Build per-employee rows ───────────────────────────────
    # Each entry: {emp, sched, existing_log, computed_result}
    entries = []
    for emp in employees:
        if not _de_match(emp):
            continue
        sched = resolve_schedule_for_date(emp, schedules, overrides, work_date)
        log   = existing.get(emp["id"])
        entries.append({"emp": emp, "sched": sched, "log": log})

    # ── Quick-action buttons ──────────────────────────────────
    qa1, _ = st.columns([1.5, 6.5])
    with qa1:
        save_all = st.button("Save All", type="primary", key="dtr_save_all", width="stretch")

    st.divider()

    # ── Column headers ────────────────────────────────────────
    cols_w = [1, 1.5, 1.2, 1.2, 1.8, 1.3, 1.3, 1, 1, 1, 1.5]
    hdr = st.columns(cols_w)
    for c, lbl in zip(hdr, ["No.", "Name", "Position", "Dept", "Shift", "Time In", "Time Out", "Late", "Undertime", "OT", "Status"]):
        c.markdown(f"**{lbl}**")

    # ── Per-employee rows ─────────────────────────────────────
    new_logs = {}   # employee_id → dict to upsert on Save All

    for entry in entries:
        emp   = entry["emp"]
        sched = entry["sched"]
        log   = entry["log"]
        eid   = emp["id"]
        name  = _employee_display_name(emp)

        # If rest day or no schedule — show greyed row
        if sched is None:
            row = st.columns(cols_w)
            row[0].caption(emp.get("employee_no", ""))
            row[1].text(_employee_display_name(emp))
            row[2].caption(emp.get("position") or "—")
            row[3].caption(emp.get("department") or "—")
            row[4].caption("—")   # Shift
            row[5].text("—"); row[6].text("—"); row[7].text("—")
            row[8].text("—"); row[9].text("—")
            row[10].markdown(_status_html("rest_day"), unsafe_allow_html=True)
            continue

        # Parse existing times
        existing_in  = _parse_time(log["time_in"])  if log and log.get("time_in")  else None
        existing_out = _parse_time(log["time_out"]) if log and log.get("time_out") else None

        row = st.columns(cols_w)
        row[0].caption(emp.get("employee_no", ""))
        row[1].text(_employee_display_name(emp))
        row[2].caption(emp.get("position") or "—")
        row[3].caption(emp.get("department") or "—")

        # Shift name (col 4)
        sched_name = sched.get("name", "—") if sched else "—"
        _s_start   = (sched.get("start_time") or "")[:5]
        _s_end     = (sched.get("end_time")   or "")[:5]
        row[4].caption(f"{sched_name}\n{_s_start}–{_s_end}" if _s_start else sched_name)

        with row[5]:
            t_in = st.time_input("In", value=existing_in or time(8, 0),
                                 key=f"dtr_in_{eid}", label_visibility="collapsed")
        with row[6]:
            t_out = st.time_input("Out", value=existing_out or time(17, 0),
                                  key=f"dtr_out_{eid}", label_visibility="collapsed")

        # Real-time DTR computation
        exp_hours    = schedule_expected_hours(sched)
        exp_start    = _parse_time(sched["start_time"])
        exp_end      = _parse_time(sched["end_time"])
        break_min    = int(sched.get("break_minutes", 60))
        is_overnight = bool(sched.get("is_overnight", False))

        # Only compute if user has actual times (not just defaults)
        has_entry = (log is not None) or (
            st.session_state.get(f"dtr_in_{eid}") is not None
        )
        if has_entry or log:
            result = compute_dtr(t_in, t_out, exp_start, exp_end,
                                  exp_hours, break_min, is_overnight)
            row[7].text(_fmt_mins(result.late_minutes))
            row[8].text(_fmt_mins(result.undertime_minutes))
            row[9].text(f"{result.ot_hours:.1f}h" if result.ot_hours else "—")
            row[10].markdown(_status_html(result.status), unsafe_allow_html=True)
        else:
            for i in range(7, 10):
                row[i].text("—")
            row[10].markdown(_status_html("absent"), unsafe_allow_html=True)
            result = None

        # Stage for bulk save
        if result:
            new_logs[eid] = {
                "employee_id":       eid,
                "work_date":         str(work_date),
                "schedule_id":       sched["id"],
                "expected_start":    str(exp_start),
                "expected_end":      str(exp_end),
                "expected_hours":    exp_hours,
                "time_in":           str(t_in),
                "time_out":          str(t_out),
                "time_in_method":    "manual",
                "time_out_method":   "manual",
                "gross_hours":       result.gross_hours,
                "late_minutes":      result.late_minutes,
                "undertime_minutes": result.undertime_minutes,
                "ot_hours":          result.ot_hours,
                "nsd_hours":         result.nsd_hours,
                "status":            result.status,
            }

    # ── Save All ──────────────────────────────────────────────
    if save_all:
        saved = 0
        errors = []
        for eid, row_data in new_logs.items():
            try:
                _upsert_time_log(row_data)
                saved += 1
            except Exception as ex:
                errors.append(str(ex))
        if errors:
            st.session_state["dtr_save_msg"] = (
                "error",
                f"Saved {saved} rows with {len(errors)} error(s): {errors[0]}",
            )
        else:
            log_action("batch_saved", "time_logs", get_company_id(),
                       f"{work_date} — {saved} records")
            label = work_date.strftime('%A, %B %d, %Y')
            st.session_state["dtr_save_msg"] = (
                "success",
                f"Saved {saved} attendance record(s) for **{label}**.",
            )
        st.rerun()


# ============================================================
# Tab 2 — Attendance Summary
# ============================================================

def _render_summary():
    today = date.today()
    month_start = today.replace(day=1)

    # Range picker — first click sets "from", second click sets "to"
    date_range = st.date_input(
        "Select date range",
        value=(month_start, today),
        key="dtr_sum_range",
        help="Click a start date, then click an end date",
    )
    # date_input returns a tuple when a range is selected; guard for partial picks
    if not isinstance(date_range, (list, tuple)) or len(date_range) < 2:
        st.info("Pick a start and end date to view the summary.")
        return
    range_start, range_end = date_range[0], date_range[1]

    if range_start > range_end:
        st.error("Start date must be before end date.")
        return

    employees = _load_employees()
    profiles  = _load_employee_profiles()
    logs      = _load_time_logs_range(range_start, range_end)

    if not employees:
        st.info("No active employees found.")
        return

    # Merge department into employees
    for emp in employees:
        emp["department"] = profiles.get(emp["id"], "")

    # ── Filter bar ────────────────────────────────────────────
    all_positions = sorted({(e.get("position") or "").strip() for e in employees} - {""})
    all_depts     = sorted({(e.get("department") or "").strip() for e in employees} - {""})
    _dept_names_structured = _load_dept_names_from_table()
    if _dept_names_structured:
        all_depts = _dept_names_structured
    sm_s, sm_p, sm_d = st.columns([2, 1.5, 1.5])
    with sm_s:
        sm_search   = st.text_input("Search", placeholder="Name or employee no…",
                                    label_visibility="collapsed", key="sm_search")
    with sm_p:
        sm_sel_pos  = st.multiselect("Position",   all_positions, key="sm_f_pos",  placeholder="All positions")
    with sm_d:
        sm_sel_dept = st.multiselect("Department", all_depts,     key="sm_f_dept", placeholder="All departments")

    # Aggregate per employee
    from collections import defaultdict
    agg: dict[str, dict] = {}
    for emp in employees:
        eid = emp["id"]
        agg[eid] = {
            "emp_no":    emp.get("employee_no", ""),
            "name":      _employee_display_name(emp),
            "position":  emp.get("position") or "—",
            "dept":      emp.get("department") or "—",
            "present":   0,
            "half_day":  0,
            "absent":    0,
            "late":      0,
            "late_mins": 0,
            "undertime_mins": 0,
            "ot_hours":  0.0,
            "nsd_hours": 0.0,
            "days_logged": 0,
        }

    for log in logs:
        eid = log["employee_id"]
        if eid not in agg:
            continue
        a = agg[eid]
        a["days_logged"] += 1
        status = log.get("status", "absent")
        if status == "present":
            a["present"] += 1
        elif status == "half_day":
            a["half_day"] += 1
        elif status == "absent":
            a["absent"] += 1
        lm = log.get("late_minutes") or 0
        if lm > 0:
            a["late"] += 1
            a["late_mins"] += lm
        a["undertime_mins"] += log.get("undertime_minutes") or 0
        a["ot_hours"]       += float(log.get("ot_hours")  or 0)
        a["nsd_hours"]      += float(log.get("nsd_hours") or 0)

    # Render summary table
    hdr_cols = [1, 1.8, 1.5, 1.5, 1, 1, 1, 1, 1.2, 1.2, 1.5]
    hdr = st.columns(hdr_cols)
    for c, lbl in zip(hdr, ["No.", "Name", "Position", "Dept", "Present", "Late", "Half Day", "Absent", "OT Hrs", "NSD Hrs", "Late Time"]):
        c.markdown(f"**{lbl}**")

    for emp in employees:
        eid = emp["id"]
        a = agg[eid]
        if a["days_logged"] == 0:
            continue

        # Apply filters
        if sm_search:
            q = sm_search.lower()
            if q not in a["name"].lower() and q not in a["emp_no"].lower():
                continue
        if sm_sel_pos  and (emp.get("position") or "") not in sm_sel_pos:
            continue
        if sm_sel_dept and (emp.get("department") or "") not in sm_sel_dept:
            continue

        row = st.columns(hdr_cols)
        row[0].caption(a["emp_no"])
        row[1].text(a["name"])
        row[2].caption(a["position"])
        row[3].caption(a["dept"])
        row[4].text(str(a["present"]))

        # Color-code late count
        late_color = "var(--gxp-warning)" if a["late"] > 0 else "var(--gxp-text)"
        row[5].markdown(
            f'<span style="color:{late_color};font-weight:600">{a["late"]}</span>',
            unsafe_allow_html=True,
        )
        row[6].text(str(a["half_day"]))

        # Color-code absent count
        abs_color = "var(--gxp-danger)" if a["absent"] > 3 else "var(--gxp-text)"
        row[7].markdown(
            f'<span style="color:{abs_color};font-weight:600">{a["absent"]}</span>',
            unsafe_allow_html=True,
        )
        row[8].text(f"{a['ot_hours']:.1f}" if a["ot_hours"] else "—")
        row[9].text(f"{a['nsd_hours']:.2f}" if a["nsd_hours"] else "—")
        row[10].text(_fmt_mins(a["late_mins"]))

    # ── Expandable per-employee detail ────────────────────────
    st.divider()
    st.subheader("Day-by-Day Detail")
    emp_options = {_employee_display_name(e): e["id"] for e in employees}
    selected_name = st.selectbox("Select employee", options=list(emp_options.keys()),
                                  key="dtr_detail_emp")
    selected_id = emp_options[selected_name]

    detail_logs = [l for l in logs if l["employee_id"] == selected_id]
    if not detail_logs:
        st.info("No attendance records in this range for the selected employee.")
        return

    detail_logs.sort(key=lambda l: l["work_date"])
    d_cols = [1.5, 1.2, 1.3, 1.3, 1, 1, 1, 1, 1.5]
    d_hdr = st.columns(d_cols)
    for c, lbl in zip(d_hdr, ["Date", "Day", "Time In", "Time Out", "Late", "UT", "OT", "NSD", "Status"]):
        c.markdown(f"**{lbl}**")

    for l in detail_logs:
        d = date.fromisoformat(l["work_date"])
        d_row = st.columns(d_cols)
        d_row[0].text(d.strftime("%m/%d/%y"))
        d_row[1].text(d.strftime("%a"))
        d_row[2].text(_fmt_time(l.get("time_in")))
        d_row[3].text(_fmt_time(l.get("time_out")))
        d_row[4].text(_fmt_mins(l.get("late_minutes") or 0))
        d_row[5].text(_fmt_mins(l.get("undertime_minutes") or 0))
        d_row[6].text(f"{float(l['ot_hours']):.1f}h" if l.get("ot_hours") else "—")
        d_row[7].text(f"{float(l['nsd_hours']):.2f}h" if l.get("nsd_hours") else "—")
        d_row[8].markdown(_status_html(l.get("status", "absent")), unsafe_allow_html=True)


# ============================================================
# Tab 3 — Corrections
# ============================================================

def _render_corrections():
    col_filter, _ = st.columns([2, 5])
    with col_filter:
        status_filter = st.selectbox(
            "Show", ["pending", "all", "approved", "rejected"],
            key="corr_filter",
        )

    corrections = _load_corrections(status_filter)

    if not corrections:
        st.info("No correction requests found.")
        return

    pending_count = sum(1 for c in corrections if c["status"] == "pending")
    if pending_count:
        st.warning(f"**{pending_count}** correction request(s) pending review.")

    for corr in corrections:
        emp_data = corr.get("employees") or {}
        emp_name = f"{emp_data.get('last_name', '')}, {emp_data.get('first_name', '')}"
        work_date_str = date.fromisoformat(corr["work_date"]).strftime("%B %d, %Y")

        status = corr["status"]
        status_color = {
            "pending":  "var(--gxp-warning)",
            "approved": "var(--gxp-success)",
            "rejected": "var(--gxp-danger)",
        }.get(status, "var(--gxp-text2)")

        with st.container(border=True):
            h1, h2 = st.columns([3, 1])
            h1.markdown(f"**{emp_name}** · {work_date_str}")
            h2.markdown(
                f'<div style="text-align:right;color:{status_color};font-weight:600">'
                f'{status.upper()}</div>',
                unsafe_allow_html=True,
            )

            # Load the original time log for comparison
            original = (
                get_db().table("time_logs")
                .select("time_in, time_out, status")
                .eq("employee_id", corr["employee_id"])
                .eq("work_date", corr["work_date"])
                .execute()
            ).data
            orig = original[0] if original else {}

            c1, c2, c3 = st.columns(3)
            c1.markdown("**Recorded**")
            c1.text(f"In:  {_fmt_time(orig.get('time_in'))}")
            c1.text(f"Out: {_fmt_time(orig.get('time_out'))}")
            c2.markdown("**Requested**")
            c2.text(f"In:  {_fmt_time(corr.get('requested_time_in'))}")
            c2.text(f"Out: {_fmt_time(corr.get('requested_time_out'))}")
            c3.markdown("**Reason**")
            c3.caption(corr.get("reason", "—"))

            if corr.get("admin_notes"):
                st.caption(f"Admin notes: {corr['admin_notes']}")

            if status == "pending":
                notes_key = f"corr_notes_{corr['id']}"
                notes = st.text_input("Admin notes (optional)", key=notes_key,
                                       label_visibility="collapsed",
                                       placeholder="Admin notes (optional)")
                btn1, btn2, _ = st.columns([1.5, 1.5, 5])
                with btn1:
                    if st.button("Approve", key=f"corr_approve_{corr['id']}", type="primary"):
                        try:
                            _update_correction(corr["id"], "approved", notes)
                            # Apply the correction to the time_log
                            if orig:
                                req_in  = corr.get("requested_time_in")
                                req_out = corr.get("requested_time_out")
                                # Reload schedule to re-compute
                                emp_row = (
                                    get_db().table("employees")
                                    .select("*, schedule_id")
                                    .eq("id", corr["employee_id"])
                                    .execute()
                                ).data
                                if emp_row and req_in and req_out:
                                    schedules = _load_schedules()
                                    emp       = emp_row[0]
                                    work_date = date.fromisoformat(corr["work_date"])
                                    overrides = _load_overrides_for_date(work_date)
                                    sched     = resolve_schedule_for_date(emp, schedules, overrides, work_date)
                                    if sched:
                                        exp_h = schedule_expected_hours(sched)
                                        result = compute_dtr(
                                            _parse_time(req_in), _parse_time(req_out),
                                            _parse_time(sched["start_time"]),
                                            _parse_time(sched["end_time"]),
                                            exp_h,
                                            int(sched.get("break_minutes", 60)),
                                            bool(sched.get("is_overnight", False)),
                                        )
                                        _upsert_time_log({
                                            "employee_id":      corr["employee_id"],
                                            "work_date":        corr["work_date"],
                                            "time_in":          req_in,
                                            "time_out":         req_out,
                                            "gross_hours":      result.gross_hours,
                                            "late_minutes":     result.late_minutes,
                                            "undertime_minutes": result.undertime_minutes,
                                            "ot_hours":         result.ot_hours,
                                            "nsd_hours":        result.nsd_hours,
                                            "status":           result.status,
                                        })
                            log_action("approved", "dtr_correction", corr["id"],
                                       f"{emp_name} {corr['work_date']}")
                            st.success("Correction approved and applied.")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Error: {ex}")
                with btn2:
                    if st.button("Reject", key=f"corr_reject_{corr['id']}"):
                        try:
                            _update_correction(corr["id"], "rejected", notes)
                            log_action("rejected", "dtr_correction", corr["id"],
                                       f"{emp_name} {corr['work_date']}")
                            st.success("Correction rejected.")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Error: {ex}")


# ============================================================
# Main render
# ============================================================

def render():
    inject_css()
    st.title("Attendance & DTR")

    tab_entry, tab_summary, tab_corrections = st.tabs([
        "Daily Entry",
        "Attendance Summary",
        "Corrections",
    ])

    with tab_entry:
        _render_daily_entry()

    with tab_summary:
        _render_summary()

    with tab_corrections:
        _render_corrections()
