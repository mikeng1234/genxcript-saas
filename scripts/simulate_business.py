"""
simulate_business.py
====================
Randomized simulation of one month of business operations for Mabini Digital Co.

Each run picks different employees, dates, and amounts so the DB accumulates
diverse data over multiple runs.

Run:
  cd I:/SaaS/PaySys/genxcript-saas
  python -m scripts.simulate_business [--seed 42]

Log: scripts/sim_log.txt
"""

import os, sys, logging, random, argparse
from datetime import date, time, datetime, timedelta

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from db.connection import get_supabase_admin_client
from backend.dtr import compute_dtr

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_FILE = os.path.join(os.path.dirname(__file__), "sim_log.txt")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8"),
    ],
)
log = logging.getLogger("sim")

def sep(title):
    log.info(""); log.info("-" * 64); log.info(f"  {title}"); log.info("-" * 64)
def ok(a, d=""): log.info(f"  [OK]   {a}" + (f"  ->  {d}" if d else ""))
def skip(a, d=""): log.warning(f"  [SKIP] {a}" + (f"  ->  {d}" if d else ""))
def fail(a, e): log.error(f"  [ERR]  {a}  ->  {type(e).__name__}: {e}")

# ── DB ────────────────────────────────────────────────────────────────────────
try:
    DB = get_supabase_admin_client()
    ok("Supabase admin client connected")
except Exception as e:
    logging.critical(f"Cannot connect: {e}"); sys.exit(1)

def q(t): return DB.table(t)
def php(c): return float(c) / 100.0

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_company():
    rows = q("companies").select("*").eq("name", "Mabini Digital Co.").execute().data
    if not rows: raise RuntimeError("Mabini Digital Co. not found — run seed first")
    return rows[0]

def get_employees(cid):
    return q("employees").select("*").eq("company_id", cid).eq("is_active", True).execute().data

def get_profiles(cid):
    rows = q("employee_profiles").select("employee_id,department").eq("company_id", cid).execute().data
    return {r["employee_id"]: r for r in rows}

def get_schedules(cid):
    return {r["id"]: r for r in q("schedules").select("*").eq("company_id", cid).execute().data}

def get_pay_periods(cid):
    return q("pay_periods").select("*").eq("company_id", cid).order("period_start").execute().data

def get_existing_logs(cid, work_date):
    rows = q("time_logs").select("employee_id").eq("company_id", cid).eq("work_date", str(work_date)).execute().data
    return {r["employee_id"] for r in rows}

def working_days(year, month):
    d, days = date(year, month, 1), []
    while d.month == month:
        if d.weekday() < 5: days.append(d)
        d += timedelta(days=1)
    return days

def random_working_day(year, month, rng):
    days = working_days(year, month)
    return rng.choice(days)

def random_ot_window(rng):
    """Returns (start_time_str, end_time_str, hours) for an OT block after 17:00."""
    start_h = 17
    duration = rng.choice([1, 1.5, 2, 2.5, 3, 4])
    end_h = start_h + int(duration)
    end_m = 30 if duration % 1 else 0
    return f"{start_h:02d}:00", f"{end_h:02d}:{end_m:02d}", duration

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Bootstrap
# ═══════════════════════════════════════════════════════════════════════════════

def step_bootstrap(state, rng):
    sep("STEP 1 -- Bootstrap company + roster")
    company = get_company()
    cid = company["id"]
    state.update({"company": company, "cid": cid})

    employees = get_employees(cid)
    profiles  = get_profiles(cid)
    schedules = get_schedules(cid)
    state.update({"employees": employees, "profiles": profiles, "schedules": schedules})

    ok(f"Company: {company['name']}")
    ok(f"Employees: {len(employees)} active")
    for emp in employees:
        dept = profiles.get(emp["id"], {}).get("department", "--")
        log.info(f"       {emp['employee_no']:8}  {emp['last_name']}, {emp['first_name']:<14} [{dept:<12}]  PHP {php(emp['basic_salary']):>10,.2f}")

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Hire a new employee (random name + department)
# ═══════════════════════════════════════════════════════════════════════════════

def step_hire_employee(state, rng):
    sep("STEP 2 -- ADMIN: Hire random new employee")
    cid = state["cid"]

    first_names = ["Leo", "Mae", "Roy", "Liz", "Jon", "Kay", "Rex", "Joy", "Sam", "Ann"]
    last_names  = ["Bautista", "Castillo", "Dela Cruz", "Espiritu", "Fuentes",
                   "Guerrero", "Herrera", "Ibarra", "Jimenez", "Kalaw"]
    positions   = ["Analyst", "Coordinator", "Specialist", "Associate", "Assistant"]
    departments = ["Operations", "Administration", "Sales"]
    salaries    = [1800000, 2000000, 2200000, 2400000, 2500000]  # centavos

    fname = rng.choice(first_names)
    lname = rng.choice(last_names)
    dept  = rng.choice(departments)
    pos   = rng.choice(positions)
    sal   = rng.choice(salaries)

    # Assign next MDC number
    emps = get_employees(cid)
    nums = []
    for e in emps:
        no = e.get("employee_no", "")
        if no.startswith("MDC-") and no[4:].isdigit():
            nums.append(int(no[4:]))
    next_no = f"MDC-{(max(nums) + 1 if nums else 11):03d}"

    # Idempotent: skip if this exact number exists
    existing = q("employees").select("id").eq("company_id", cid).eq("employee_no", next_no).execute().data
    if existing:
        skip(f"{next_no} already exists")
        return

    sched_rows = q("schedules").select("id,name").eq("company_id", cid).execute().data
    day_sched  = next((r["id"] for r in sched_rows if "Day" in r["name"]), None)
    tmpl_rows  = q("leave_entitlement_templates").select("id").eq("company_id", cid).execute().data
    tmpl_id    = tmpl_rows[0]["id"] if tmpl_rows else None

    try:
        result = q("employees").insert({
            "company_id": cid, "employee_no": next_no,
            "first_name": fname, "last_name": lname,
            "position": pos, "employment_type": "probationary",
            "date_hired": str(date.today()),
            "basic_salary": sal, "salary_type": "monthly",
            "tax_status": rng.choice(["S", "ME"]),
            "schedule_id": day_sched, "leave_template_id": tmpl_id,
            "is_active": True,
        }).execute().data
        new_id = result[0]["id"]
        q("employee_profiles").insert({
            "employee_id": new_id, "company_id": cid,
            "department": dept, "nationality": "Filipino",
        }).execute()
        ok(f"Hired {fname} {lname} ({next_no})", f"dept={dept}  pos={pos}  salary=PHP {php(sal):,.0f}")
        # Refresh roster
        state["employees"] = get_employees(cid)
        state["profiles"]  = get_profiles(cid)
    except Exception as e:
        fail("Hire employee", e)

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Create next pay period
# ═══════════════════════════════════════════════════════════════════════════════

def step_create_pay_period(state, rng):
    sep("STEP 3 -- ADMIN: Ensure next pay period exists")
    cid     = state["cid"]
    periods = get_pay_periods(cid)

    # Find the latest period and create the one after
    if periods:
        last     = periods[-1]
        last_end = date.fromisoformat(last["period_end"])
        new_start = last_end + timedelta(days=1)
    else:
        new_start = date(2026, 5, 1)

    # Only create if it doesn't already exist
    existing = q("pay_periods").select("id,status").eq("company_id", cid) \
        .eq("period_start", str(new_start)).execute().data
    if existing:
        state["next_period"] = existing[0]
        skip(f"{new_start.strftime('%b %Y')} period already exists", f"status={existing[0]['status']}")
        return

    new_end  = (new_start.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    pay_date = new_end + timedelta(days=5)

    try:
        result = q("pay_periods").insert({
            "company_id": cid, "period_start": str(new_start),
            "period_end": str(new_end), "payment_date": str(pay_date),
            "status": "draft",
        }).execute().data
        state["next_period"] = result[0]
        ok(f"Created {new_start.strftime('%b %Y')} pay period", f"status=draft")
    except Exception as e:
        fail("Create pay period", e)

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4 — Log attendance for simulation month
# ═══════════════════════════════════════════════════════════════════════════════

def step_log_attendance(state, rng, year=2026, month=3):
    sep(f"STEP 4 -- ADMIN: Log attendance for {date(year, month, 1).strftime('%B %Y')}")
    cid       = state["cid"]
    employees = state["employees"]
    schedules = state["schedules"]

    days = working_days(year, month)
    log.info(f"  Working days: {len(days)}")

    # Randomize personalities per run for employees not in seed
    base = {
        "MDC-001": (0,  0,  5),  "MDC-002": (5,  0,  5),
        "MDC-003": (5,  0,  5),  "MDC-004": (10, 0,  40),
        "MDC-005": (5,  0,  45), "MDC-006": (5,  2,  5),
        "MDC-007": (15, 0,  10), "MDC-008": (5,  0,  5),
        "MDC-009": (35, 0,  5),  "MDC-010": (40, 8,  5),
    }

    inserted = skipped = errors = 0

    for work_date in days:
        existing = get_existing_logs(cid, work_date)

        for emp in employees:
            emp_id = emp["id"]
            emp_no = emp.get("employee_no", "")

            if emp_id in existing:
                skipped += 1
                continue

            if emp_no in base:
                late_pct, absent_pct, ot_pct = base[emp_no]
            else:
                # New hires get random personality each run
                late_pct   = rng.randint(0, 30)
                absent_pct = rng.randint(0, 10)
                ot_pct     = rng.randint(0, 20)

            seed_val = rng.randint(0, 99)

            if seed_val < absent_pct:
                try:
                    q("time_logs").insert({
                        "company_id": cid, "employee_id": emp_id,
                        "work_date": str(work_date), "status": "absent",
                        "gross_hours": 0, "late_minutes": 0,
                        "undertime_minutes": 0, "ot_hours": 0,
                        "time_in_method": "manual",
                    }).execute()
                    inserted += 1
                except Exception as e:
                    fail(f"Absent log {emp_no} {work_date}", e); errors += 1
                continue

            sched    = schedules.get(emp.get("schedule_id", ""))
            is_night = bool(sched and sched.get("is_overnight"))

            if is_night:
                exp_start, exp_end, exp_hrs, brk = time(22, 0), time(6, 0), 7.5, 30
            else:
                exp_start, exp_end, exp_hrs, brk = time(8, 0), time(17, 0), 8.0, 60

            if seed_val < late_pct:
                late_min = rng.randint(6, 90)
                in_min   = exp_start.hour * 60 + exp_start.minute + late_min
                t_in     = time(min(in_min // 60, 23), in_min % 60) if not is_night else time(22, rng.randint(10, 45))
            else:
                t_in = time(exp_start.hour, rng.randint(0, 4)) if not is_night else time(21, rng.randint(50, 59))

            if seed_val > (100 - ot_pct):
                ot_min   = rng.randint(30, 240)
                out_min  = exp_end.hour * 60 + exp_end.minute + ot_min
                t_out    = time(min(out_min // 60, 23), out_min % 60) if not is_night else time(7, rng.randint(0, 30))
            else:
                t_out = time(exp_end.hour, exp_end.minute) if not is_night else time(6, 0)

            try:
                dtr = compute_dtr(t_in, t_out, exp_start, exp_end, exp_hrs, brk, is_night, 5)
                q("time_logs").insert({
                    "company_id": cid, "employee_id": emp_id,
                    "work_date": str(work_date),
                    "schedule_id": emp.get("schedule_id"),
                    "expected_start": str(exp_start), "expected_end": str(exp_end),
                    "expected_hours": exp_hrs,
                    "time_in": str(t_in), "time_out": str(t_out),
                    "time_in_method": "manual", "time_out_method": "manual",
                    "gross_hours": dtr.gross_hours, "late_minutes": dtr.late_minutes,
                    "undertime_minutes": dtr.undertime_minutes,
                    "ot_hours": dtr.ot_hours, "status": dtr.status,
                }).execute()
                inserted += 1
            except Exception as e:
                fail(f"Time log {emp_no} {work_date}", e); errors += 1

    ok("Attendance logged", f"{inserted} inserted, {skipped} skipped, {errors} errors")

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 5 — Employees file leave requests (random count + people)
# ═══════════════════════════════════════════════════════════════════════════════

def step_file_leaves(state, rng):
    sep("STEP 5 -- EMPLOYEES: File leave requests")
    cid       = state["cid"]
    employees = state["employees"]

    count    = rng.randint(2, 4)
    chosen   = rng.sample(employees, min(count, len(employees)))
    types    = ["VL", "SL", "CL"]
    reasons  = {
        "VL": ["Family vacation", "Rest and recuperation", "Personal travel", "Wedding anniversary"],
        "SL": ["Fever and cough", "Dental appointment", "Medical check-up", "Migraine"],
        "CL": ["Family emergency", "Attending graduation", "Moving to new apartment", "Personal matters"],
    }

    filed = 0
    for emp in chosen:
        leave_type = rng.choice(types)
        start      = random_working_day(2026, 4, rng)
        duration   = rng.randint(1, 3)
        end        = start + timedelta(days=duration - 1)

        # Skip if overlapping leave already exists for this employee
        existing = q("leave_requests").select("id").eq("employee_id", emp["id"]) \
            .gte("start_date", str(start)).lte("end_date", str(end)).execute().data
        if existing:
            skip(f"{emp['employee_no']} already has leave in this window")
            continue

        try:
            result = q("leave_requests").insert({
                "company_id": cid, "employee_id": emp["id"],
                "leave_type": leave_type,
                "start_date": str(start), "end_date": str(end),
                "days": duration,
                "reason": rng.choice(reasons[leave_type]),
                "status": "pending",
            }).execute().data
            ok(f"{emp['employee_no']} filed {leave_type} {start} to {end} ({duration}d)",
               f"id={result[0]['id'][:8]}...")
            filed += 1
        except Exception as e:
            fail(f"File leave {emp['employee_no']}", e)

    ok(f"Leave filing done", f"{filed} requests filed")

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 6 — Employees file OT requests (random)
# ═══════════════════════════════════════════════════════════════════════════════

def step_file_ot(state, rng):
    sep("STEP 6 -- EMPLOYEES: File OT requests")
    cid       = state["cid"]
    employees = state["employees"]

    count  = rng.randint(2, 5)
    chosen = rng.sample(employees, min(count, len(employees)))
    ot_reasons = [
        "System deployment after hours",
        "Client presentation preparation",
        "Month-end closing",
        "Emergency maintenance",
        "Project deadline crunch",
        "Inventory reconciliation",
        "Server migration",
        "Audit preparation",
    ]

    filed = 0
    for emp in chosen:
        ot_date           = random_working_day(2026, 3, rng)
        start_str, end_str, hours = random_ot_window(rng)

        existing = q("overtime_requests").select("id").eq("employee_id", emp["id"]) \
            .eq("ot_date", str(ot_date)).execute().data
        if existing:
            skip(f"{emp['employee_no']} OT {ot_date} already exists")
            continue

        try:
            result = q("overtime_requests").insert({
                "company_id": cid, "employee_id": emp["id"],
                "ot_date": str(ot_date),
                "start_time": start_str, "end_time": end_str,
                "hours": hours,
                "reason": rng.choice(ot_reasons),
                "status": "pending",
            }).execute().data
            ok(f"{emp['employee_no']} filed OT {ot_date} {start_str}-{end_str} ({hours}h)",
               f"id={result[0]['id'][:8]}...")
            filed += 1
        except Exception as e:
            fail(f"File OT {emp['employee_no']}", e)

    ok(f"OT filing done", f"{filed} requests filed")

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 7 — Admin reviews leave requests (approve some, reject some)
# ═══════════════════════════════════════════════════════════════════════════════

def step_review_leaves(state, rng):
    sep("STEP 7 -- ADMIN: Review pending leave requests")
    cid = state["cid"]

    pending = q("leave_requests").select("*").eq("company_id", cid) \
        .eq("status", "pending").execute().data

    if not pending:
        skip("No pending leave requests")
        return

    approved_notes = ["Approved. Enjoy!", "Approved.", "Noted and approved."]
    rejected_notes = ["Insufficient leave balance.", "Business-critical period — please refile.",
                      "Overlapping with team deadline."]

    approved = rejected = 0
    for lr in pending:
        # 70% approve, 30% reject
        action = "approved" if rng.random() < 0.7 else "rejected"
        note   = rng.choice(approved_notes if action == "approved" else rejected_notes)
        try:
            q("leave_requests").update({
                "status": action, "admin_notes": note,
                "reviewed_at": datetime.now().isoformat(),
            }).eq("id", lr["id"]).execute()
            ok(f"Leave {lr['id'][:8]}... -> {action}")
            if action == "approved": approved += 1
            else: rejected += 1
        except Exception as e:
            fail(f"Review leave {lr['id'][:8]}", e)

    ok(f"Leave review done", f"{approved} approved, {rejected} rejected")

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 8 — Admin reviews OT requests
# ═══════════════════════════════════════════════════════════════════════════════

def step_review_ot(state, rng):
    sep("STEP 8 -- ADMIN: Review pending OT requests")
    cid = state["cid"]

    pending = q("overtime_requests").select("*").eq("company_id", cid) \
        .eq("status", "pending").execute().data

    if not pending:
        skip("No pending OT requests")
        return

    approved = rejected = 0
    for ot in pending:
        action = "approved" if rng.random() < 0.8 else "rejected"
        note   = "Approved." if action == "approved" else "OT not pre-authorized. Please get sign-off first."
        try:
            q("overtime_requests").update({
                "status": action, "admin_notes": note,
                "reviewed_at": datetime.now().isoformat(),
            }).eq("id", ot["id"]).execute()
            ok(f"OT {ot['id'][:8]}... -> {action}")
            if action == "approved": approved += 1
            else: rejected += 1
        except Exception as e:
            fail(f"Review OT {ot['id'][:8]}", e)

    ok(f"OT review done", f"{approved} approved, {rejected} rejected")

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 9 — Employees file DTR corrections
# ═══════════════════════════════════════════════════════════════════════════════

def step_file_corrections(state, rng):
    sep("STEP 9 -- EMPLOYEES: File DTR corrections")
    cid       = state["cid"]
    employees = state["employees"]

    count  = rng.randint(1, 3)
    chosen = rng.sample(employees, min(count, len(employees)))
    reasons = [
        "Badge scanner malfunction at entrance",
        "Forgot to clock in due to urgent meeting",
        "System was down when I arrived",
        "Clocked in via paper log but not reflected",
        "Remote work — forgot to use portal",
    ]

    filed = 0
    for emp in chosen:
        logs = q("time_logs").select("id,work_date,status").eq("employee_id", emp["id"]) \
            .gte("work_date", "2026-03-01").lte("work_date", "2026-03-31") \
            .order("work_date").execute().data

        # Pick a log without an existing correction
        candidates = []
        for tl in logs:
            ex = q("dtr_corrections").select("id").eq("time_log_id", tl["id"]).execute().data
            if not ex:
                candidates.append(tl)

        if not candidates:
            skip(f"{emp['employee_no']} has no correctable logs")
            continue

        tl = rng.choice(candidates)
        req_in  = f"08:{rng.randint(0, 15):02d}"
        req_out = f"17:{rng.randint(0, 30):02d}"

        try:
            result = q("dtr_corrections").insert({
                "company_id": cid, "employee_id": emp["id"],
                "time_log_id": tl["id"], "work_date": tl["work_date"],
                "requested_time_in": req_in, "requested_time_out": req_out,
                "reason": rng.choice(reasons), "status": "pending",
            }).execute().data
            ok(f"{emp['employee_no']} filed correction for {tl['work_date']}",
               f"{req_in} - {req_out}  id={result[0]['id'][:8]}...")
            filed += 1
        except Exception as e:
            fail(f"File correction {emp['employee_no']}", e)

    ok(f"Corrections filed", f"{filed} submitted")

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 10 — Admin reviews DTR corrections
# ═══════════════════════════════════════════════════════════════════════════════

def step_review_corrections(state, rng):
    sep("STEP 10 -- ADMIN: Review pending DTR corrections")
    cid = state["cid"]

    pending = q("dtr_corrections").select("*").eq("company_id", cid) \
        .eq("status", "pending").execute().data

    if not pending:
        skip("No pending DTR corrections")
        return

    approved = rejected = 0
    for corr in pending:
        action = "approved" if rng.random() < 0.75 else "rejected"
        try:
            q("dtr_corrections").update({
                "status": action,
                "admin_notes": "Verified and approved." if action == "approved"
                               else "Insufficient evidence. Please provide supporting documents.",
                "reviewed_at": datetime.now().isoformat(),
            }).eq("id", corr["id"]).execute()

            if action == "approved" and corr.get("time_log_id") \
                    and corr.get("requested_time_in") and corr.get("requested_time_out"):
                req_in  = time.fromisoformat(corr["requested_time_in"])
                req_out = time.fromisoformat(corr["requested_time_out"])
                dtr = compute_dtr(req_in, req_out, time(8,0), time(17,0), 8.0, 60, False, 5)
                q("time_logs").update({
                    "time_in": str(req_in), "time_out": str(req_out),
                    "late_minutes": dtr.late_minutes,
                    "undertime_minutes": dtr.undertime_minutes,
                    "gross_hours": dtr.gross_hours,
                    "ot_hours": dtr.ot_hours,
                    "status": dtr.status,
                    "updated_at": datetime.now().isoformat(),
                }).eq("id", corr["time_log_id"]).execute()

            ok(f"Correction {corr['id'][:8]}... -> {action} ({corr['work_date']})")
            if action == "approved": approved += 1
            else: rejected += 1
        except Exception as e:
            fail(f"Review correction {corr['id'][:8]}", e)

    ok(f"Corrections reviewed", f"{approved} approved, {rejected} rejected")

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 11 — Compute payroll for the latest draft period
# ═══════════════════════════════════════════════════════════════════════════════

def step_run_payroll(state, rng):
    sep("STEP 11 -- ADMIN: Compute payroll for latest draft period")
    cid       = state["cid"]
    employees = state["employees"]
    schedules = state["schedules"]
    periods   = get_pay_periods(cid)

    draft = next((p for p in reversed(periods) if p["status"] == "draft"), None)
    if not draft:
        skip("No draft pay period found")
        return

    period_id    = draft["id"]
    period_label = f"{draft['period_start']} to {draft['period_end']}"
    log.info(f"  Period: {period_label}  id={period_id[:8]}...")

    # Collect approved OT hours per employee for this period
    ot_approvals = q("overtime_requests").select("employee_id,hours") \
        .eq("company_id", cid).eq("status", "approved") \
        .gte("ot_date", draft["period_start"]).lte("ot_date", draft["period_end"]).execute().data
    ot_map = {}
    for row in ot_approvals:
        ot_map[row["employee_id"]] = ot_map.get(row["employee_id"], 0) + float(row["hours"])

    inserted = updated = errors = 0

    for emp in employees:
        emp_id     = emp["id"]
        emp_no     = emp.get("employee_no", "?")
        salary_php = php(emp["basic_salary"])
        hourly     = salary_php / 22 / 8

        sss     = round(min(1350.0, salary_php * 0.045), 2)
        phic    = round(min(salary_php, 100000) * 0.025, 2)
        pagibig = round(min(100.0, salary_php * 0.02), 2)
        total_gov = sss + phic + pagibig

        ot_hrs = ot_map.get(emp_id, 0)
        ot_pay = round(hourly * ot_hrs * 1.25, 2)

        sched    = schedules.get(emp.get("schedule_id", ""))
        is_night = bool(sched and sched.get("is_overnight"))
        nsd_pay  = round(hourly * 7.5 * 22 * 0.10, 2) if is_night else 0.0

        gross = round(salary_php + ot_pay + nsd_pay, 2)

        annual_taxable = (gross - total_gov) * 12
        if annual_taxable <= 250_000:       wht = 0.0
        elif annual_taxable <= 400_000:     wht = (annual_taxable - 250_000) * 0.20 / 12
        elif annual_taxable <= 800_000:     wht = (30_000 + (annual_taxable - 400_000) * 0.25) / 12
        elif annual_taxable <= 2_000_000:   wht = (130_000 + (annual_taxable - 800_000) * 0.30) / 12
        elif annual_taxable <= 8_000_000:   wht = (490_000 + (annual_taxable - 2_000_000) * 0.32) / 12
        else:                               wht = (2_410_000 + (annual_taxable - 8_000_000) * 0.35) / 12
        wht = round(wht, 2)

        net = round(gross - total_gov - wht, 2)

        entry = {
            "employee_id": emp_id, "pay_period_id": period_id,
            "basic_pay":                round(salary_php * 100),
            "overtime_pay":             round(ot_pay * 100),
            "night_differential":       round(nsd_pay * 100),
            "allowances_taxable":       0, "allowances_nontaxable": 0,
            "commission":               0, "thirteenth_month_accrual": 0,
            "gross_pay":                round(gross * 100),
            "sss_employee":             round(sss * 100),
            "philhealth_employee":      round(phic * 100),
            "pagibig_employee":         round(pagibig * 100),
            "sss_employer":             round(sss * 100),
            "philhealth_employer":      round(phic * 100),
            "pagibig_employer":         round(pagibig * 100),
            "withholding_tax":          round(wht * 100),
            "sss_loan": 0, "pagibig_loan": 0, "cash_advance": 0, "other_deductions": 0,
            "total_deductions":         round((total_gov + wht) * 100),
            "net_pay":                  round(net * 100),
        }

        try:
            existing = q("payroll_entries").select("id") \
                .eq("pay_period_id", period_id).eq("employee_id", emp_id).execute().data
            if existing:
                q("payroll_entries").update(entry).eq("id", existing[0]["id"]).execute()
                updated += 1
            else:
                q("payroll_entries").insert(entry).execute()
                inserted += 1
            log.info(
                f"       {emp_no:8}  gross=PHP {gross:>9,.2f}  net=PHP {net:>9,.2f}"
                f"{'  [OT '+str(ot_hrs)+'h]' if ot_hrs else ''}"
                f"{'  [NSD]' if nsd_pay else ''}"
            )
        except Exception as e:
            fail(f"Payroll {emp_no}", e); errors += 1

    ok(f"Payroll done", f"{inserted} inserted, {updated} updated, {errors} errors")

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 12 — Finalize the oldest reviewed period
# ═══════════════════════════════════════════════════════════════════════════════

def step_finalize_period(state, rng):
    sep("STEP 12 -- ADMIN: Finalize oldest reviewed period")
    cid     = state["cid"]
    periods = get_pay_periods(cid)

    reviewed = next((p for p in periods if p["status"] == "reviewed"), None)
    if not reviewed:
        # Promote a draft to reviewed, then finalize it next run
        draft = next((p for p in periods if p["status"] == "draft"), None)
        if draft:
            q("pay_periods").update({"status": "reviewed"}).eq("id", draft["id"]).execute()
            ok(f"Promoted to reviewed", f"{draft['period_start']}")
        else:
            skip("No reviewed or draft periods to act on")
        return

    q("pay_periods").update({"status": "finalized"}).eq("id", reviewed["id"]).execute()
    ok(f"Finalized period", f"{reviewed['period_start']} to {reviewed['period_end']}")

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 13 — Employee portal: clock in/out simulation
# ═══════════════════════════════════════════════════════════════════════════════

def step_portal_clockin(state, rng):
    sep("STEP 13 -- EMPLOYEE: Portal clock-in simulation (today)")
    cid       = state["cid"]
    employees = state["employees"]
    schedules = state["schedules"]

    # Pick 2-4 random employees to clock in today
    count  = rng.randint(2, 4)
    chosen = rng.sample(employees, min(count, len(employees)))
    today  = date.today()

    if today.weekday() >= 5:
        skip("Today is a weekend — no clock-ins")
        return

    locations = q("company_locations").select("id,name,radius_m").eq("company_id", cid) \
        .eq("is_active", True).execute().data
    loc_id = locations[0]["id"] if locations else None

    done = 0
    for emp in chosen:
        existing = q("time_logs").select("id").eq("employee_id", emp["id"]) \
            .eq("work_date", str(today)).execute().data
        if existing:
            skip(f"{emp['employee_no']} already clocked in today")
            continue

        sched    = schedules.get(emp.get("schedule_id", ""))
        is_night = bool(sched and sched.get("is_overnight"))

        if is_night:
            exp_start, exp_end, exp_hrs, brk = time(22, 0), time(6, 0), 7.5, 30
            t_in  = time(22, rng.randint(0, 10))
            t_out = None   # night shift — no clock-out yet
        else:
            exp_start, exp_end, exp_hrs, brk = time(8, 0), time(17, 0), 8.0, 60
            t_in  = time(8, rng.randint(0, 20))
            t_out = None   # no clock-out yet (still working)

        # Simulate in-range geolocation (slight offset from 14.5547, 121.0244)
        lat = 14.5547 + rng.uniform(-0.0005, 0.0005)
        lng = 121.0244 + rng.uniform(-0.0005, 0.0005)
        dist = rng.randint(10, 120)

        try:
            q("time_logs").insert({
                "company_id": cid, "employee_id": emp["id"],
                "work_date": str(today),
                "schedule_id": emp.get("schedule_id"),
                "expected_start": str(exp_start), "expected_end": str(exp_end),
                "expected_hours": exp_hrs,
                "time_in": str(t_in), "time_in_method": "portal",
                "time_in_lat": round(lat, 7), "time_in_lng": round(lng, 7),
                "time_in_distance_m": dist,
                "time_in_location_id": loc_id,
                "is_out_of_range": dist > 150,
                "status": "present",
                "gross_hours": 0, "late_minutes": 0,
                "undertime_minutes": 0, "ot_hours": 0,
            }).execute()
            ok(f"{emp['employee_no']} clocked in via portal",
               f"{t_in}  dist={dist}m  {'OUT-OF-RANGE' if dist > 150 else 'in-range'}")
            done += 1
        except Exception as e:
            fail(f"Portal clock-in {emp['employee_no']}", e)

    ok(f"Portal clock-ins done", f"{done} employees")

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 14 — Update employee profile (random employee)
# ═══════════════════════════════════════════════════════════════════════════════

def step_update_profile(state, rng):
    sep("STEP 14 -- EMPLOYEE: Update personal profile")
    cid      = state["cid"]
    employees = state["employees"]
    emp      = rng.choice(employees)

    mobiles  = ["09171234567", "09281234567", "09391234567", "09501234567", "09171112233"]
    cities   = ["Makati", "Taguig", "Pasig", "Mandaluyong", "Quezon City", "Paranaque"]
    barangays = ["San Lorenzo", "Poblacion", "Pio del Pilar", "Bel-Air", "San Antonio"]

    try:
        existing = q("employee_profiles").select("id").eq("employee_id", emp["id"]).execute().data
        payload = {
            "mobile_no": rng.choice(mobiles),
            "present_address_city": rng.choice(cities),
            "present_address_barangay": rng.choice(barangays),
            "updated_at": datetime.now().isoformat(),
        }
        if existing:
            q("employee_profiles").update(payload).eq("employee_id", emp["id"]).execute()
        else:
            payload.update({"employee_id": emp["id"], "company_id": cid, "nationality": "Filipino"})
            q("employee_profiles").insert(payload).execute()
        ok(f"{emp['employee_no']} updated profile", f"mobile + address")
    except Exception as e:
        fail(f"Update profile {emp['employee_no']}", e)

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 15 — Summary
# ═══════════════════════════════════════════════════════════════════════════════

def step_summary(state, rng):
    sep("SIMULATION COMPLETE -- Summary")
    cid     = state["cid"]
    periods = get_pay_periods(cid)

    try:
        emp_count  = q("employees").select("id", count="exact").eq("company_id", cid).eq("is_active", True).execute().count
        log_count  = q("time_logs").select("id", count="exact").eq("company_id", cid) \
                       .gte("work_date", "2026-03-01").lte("work_date", "2026-03-31").execute().count
        leave_pend = q("leave_requests").select("id", count="exact").eq("company_id", cid).eq("status", "pending").execute().count
        leave_all  = q("leave_requests").select("id", count="exact").eq("company_id", cid).execute().count
        ot_pend    = q("overtime_requests").select("id", count="exact").eq("company_id", cid).eq("status", "pending").execute().count
        ot_all     = q("overtime_requests").select("id", count="exact").eq("company_id", cid).execute().count
        corr_pend  = q("dtr_corrections").select("id", count="exact").eq("company_id", cid).eq("status", "pending").execute().count

        period_ids    = [p["id"] for p in periods]
        payroll_count = q("payroll_entries").select("id", count="exact") \
            .in_("pay_period_id", period_ids).execute().count if period_ids else 0

        log.info(f"  Active employees      : {emp_count}")
        log.info(f"  Mar 2026 time logs    : {log_count}")
        log.info(f"  Leave requests        : {leave_all} total, {leave_pend} pending")
        log.info(f"  OT requests           : {ot_all} total, {ot_pend} pending")
        log.info(f"  Payroll entries       : {payroll_count} total")
        log.info(f"  DTR corrections pend  : {corr_pend}")
        log.info(f"  Pay periods           : {len(periods)}")
        for p in periods:
            log.info(f"       {p['period_start']}  {p['status']}")
        log.info(f"")
        log.info(f"  Log appended to: {LOG_FILE}")
    except Exception as e:
        fail("Summary", e)

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed (omit for truly random each run)")
    args = parser.parse_args()

    seed = args.seed if args.seed is not None else random.randint(0, 999999)
    rng  = random.Random(seed)

    log.info("=" * 66)
    log.info("  MABINI DIGITAL CO. -- BUSINESS SIMULATION")
    log.info(f"  Random seed: {seed}  (rerun with --seed {seed} to repeat)")
    log.info(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("=" * 66)

    state = {}
    step_bootstrap(state, rng)
    step_hire_employee(state, rng)
    step_create_pay_period(state, rng)
    step_log_attendance(state, rng)
    step_file_leaves(state, rng)
    step_file_ot(state, rng)
    step_review_leaves(state, rng)
    step_review_ot(state, rng)
    step_file_corrections(state, rng)
    step_review_corrections(state, rng)
    step_run_payroll(state, rng)
    step_finalize_period(state, rng)
    step_portal_clockin(state, rng)
    step_update_profile(state, rng)
    step_summary(state, rng)

    log.info(f"  Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("=" * 66)


if __name__ == "__main__":
    main()
