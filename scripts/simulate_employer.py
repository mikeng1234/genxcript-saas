"""
simulate_employer.py
====================
Employer audit script — browses every dashboard section and validates
data consistency. Reports mismatches, anomalies, and missing data.

Think of this as an employer who opens every tab and checks the numbers.

Run:
  cd I:/SaaS/PaySys/genxcript-saas
  python -m scripts.simulate_employer

Exit code: 0 = all clear, 1 = issues found
Log: scripts/employer_log.txt
"""

import os, sys, logging
from datetime import date, time, timedelta
from collections import defaultdict

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from db.connection import get_supabase_admin_client

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_FILE = os.path.join(os.path.dirname(__file__), "employer_log.txt")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
    ],
)
log = logging.getLogger("employer")

ISSUES: list[str] = []   # accumulate all problems

def php(c): return float(c) / 100.0

def sep(title):
    log.info(""); log.info("=" * 66); log.info(f"  {title}"); log.info("=" * 66)

def chk(label, ok: bool, detail="", warn_only=False):
    if ok:
        log.info(f"  [PASS]  {label}" + (f"  ({detail})" if detail else ""))
    else:
        tag = "[WARN]" if warn_only else "[FAIL]"
        msg = f"  {tag}  {label}" + (f"  ->  {detail}" if detail else "")
        if warn_only:
            log.warning(msg)
        else:
            log.error(msg)
            ISSUES.append(f"{label}: {detail}")

def note(msg):
    log.info(f"  [INFO]  {msg}")

# ── DB ────────────────────────────────────────────────────────────────────────
try:
    DB = get_supabase_admin_client()
except Exception as e:
    logging.critical(f"Cannot connect: {e}"); sys.exit(1)

def q(t): return DB.table(t)

def working_days_in(period_start: str, period_end: str):
    d    = date.fromisoformat(period_start)
    end  = date.fromisoformat(period_end)
    days = []
    while d <= end:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days

# ═══════════════════════════════════════════════════════════════════════════════
# CHECK 1 — Company setup
# ═══════════════════════════════════════════════════════════════════════════════

def check_company_setup(cid, company):
    sep("CHECK 1 -- Company Setup")

    chk("Company name set",    bool(company.get("name")), company.get("name",""))
    chk("Address set",         bool(company.get("address")), warn_only=True,
        detail=company.get("address","MISSING"))
    chk("BIR TIN set",         bool(company.get("bir_tin")), warn_only=True,
        detail=company.get("bir_tin","MISSING"))
    chk("SSS employer no set", bool(company.get("sss_employer_no")), warn_only=True,
        detail=company.get("sss_employer_no","MISSING"))
    chk("PhilHealth employer set", bool(company.get("philhealth_employer_no")), warn_only=True)
    chk("Pag-IBIG employer set",   bool(company.get("pagibig_employer_no")), warn_only=True)

    # Schedules
    scheds = q("schedules").select("*").eq("company_id", cid).execute().data
    chk("At least 1 schedule exists", len(scheds) >= 1, f"{len(scheds)} found")
    for s in scheds:
        chk(f"Schedule '{s['name']}' has work_days",
            bool(s.get("work_days")), str(s.get("work_days")))
        chk(f"Schedule '{s['name']}' has start/end time",
            bool(s.get("start_time")) and bool(s.get("end_time")))

    # Leave templates
    templates = q("leave_entitlement_templates").select("*").eq("company_id", cid).execute().data
    chk("At least 1 leave template exists", len(templates) >= 1, f"{len(templates)} found")
    for t in templates:
        chk(f"Template '{t['name']}' VL >= 0", t.get("vl_days", -1) >= 0)
        chk(f"Template '{t['name']}' SL >= 0", t.get("sl_days", -1) >= 0)

    # Locations
    locs = q("company_locations").select("*").eq("company_id", cid).eq("is_active", True).execute().data
    chk("At least 1 active location", len(locs) >= 1, f"{len(locs)} found", warn_only=True)
    for loc in locs:
        chk(f"Location '{loc['name']}' has valid GPS",
            bool(loc.get("latitude")) and bool(loc.get("longitude")))
        chk(f"Location '{loc['name']}' radius > 0", (loc.get("radius_m") or 0) > 0)

# ═══════════════════════════════════════════════════════════════════════════════
# CHECK 2 — Employee roster
# ═══════════════════════════════════════════════════════════════════════════════

def check_employees(cid):
    sep("CHECK 2 -- Employee Roster")

    employees = q("employees").select("*").eq("company_id", cid).eq("is_active", True).execute().data
    chk("At least 1 active employee", len(employees) >= 1, f"{len(employees)} found")

    # Duplicate employee_no
    emp_nos = [e.get("employee_no") for e in employees]
    dupes   = [no for no in emp_nos if emp_nos.count(no) > 1 and no]
    chk("No duplicate employee_no", len(dupes) == 0,
        f"Duplicates: {list(set(dupes))}" if dupes else "")

    # Load profiles
    prof_rows = q("employee_profiles").select("employee_id,department").eq("company_id", cid).execute().data
    prof_map  = {r["employee_id"]: r for r in prof_rows}

    no_schedule = no_template = no_profile = salary_zero = 0
    for emp in employees:
        emp_no = emp.get("employee_no", emp["id"][:8])

        if not emp.get("schedule_id"):
            chk(f"{emp_no} has schedule assigned", False, "No schedule", warn_only=True)
            no_schedule += 1

        if not emp.get("leave_template_id"):
            chk(f"{emp_no} has leave template assigned", False, "No template", warn_only=True)
            no_template += 1

        if emp["id"] not in prof_map:
            chk(f"{emp_no} has profile record", False, "Missing employee_profile row", warn_only=True)
            no_profile += 1

        sal = emp.get("basic_salary", 0)
        if sal <= 0:
            chk(f"{emp_no} salary > 0", False, f"salary={sal}")
            salary_zero += 1

        if sal > 0 and php(sal) > 500_000:
            chk(f"{emp_no} salary sanity check", False,
                f"PHP {php(sal):,.0f} seems unusually high", warn_only=True)

    note(f"Employees missing schedule:     {no_schedule}")
    note(f"Employees missing leave tmpl:   {no_template}")
    note(f"Employees missing profile:      {no_profile}")
    note(f"Employees with zero salary:     {salary_zero}")

    return employees

# ═══════════════════════════════════════════════════════════════════════════════
# CHECK 3 — Attendance / DTR
# ═══════════════════════════════════════════════════════════════════════════════

def check_attendance(cid, employees):
    sep("CHECK 3 -- Attendance & DTR")

    # Check last full month (Feb 2026)
    period_start, period_end = "2026-02-01", "2026-02-28"
    wdays = working_days_in(period_start, period_end)
    note(f"Checking Feb 2026 ({len(wdays)} working days, {len(employees)} employees)")

    logs = q("time_logs").select("*").eq("company_id", cid) \
        .gte("work_date", period_start).lte("work_date", period_end).execute().data

    log_by_emp = defaultdict(list)
    for tl in logs:
        log_by_emp[tl["employee_id"]].append(tl)

    # Coverage check
    emp_map = {e["id"]: e for e in employees}
    for emp in employees:
        emp_no  = emp.get("employee_no", emp["id"][:8])
        emp_logs = log_by_emp.get(emp["id"], [])
        coverage = len(emp_logs) / len(wdays) * 100 if wdays else 0
        chk(f"{emp_no} attendance coverage >= 50%", coverage >= 50,
            f"{len(emp_logs)}/{len(wdays)} days ({coverage:.0f}%)", warn_only=True)

    # Data integrity per log
    neg_gross = out_before_in = negative_late = late_but_in_before_sched = 0
    for tl in logs:
        emp_no = emp_map.get(tl["employee_id"], {}).get("employee_no", "?")
        wd     = tl["work_date"]

        if tl["status"] in ("absent", "on_leave", "holiday", "rest_day"):
            continue

        t_in  = tl.get("time_in")
        t_out = tl.get("time_out")

        if t_in and t_out:
            ti = time.fromisoformat(t_in)
            to = time.fromisoformat(t_out)
            # Detect overnight: explicit expected_start flag OR time_in >= 18:00 with time_out <= 12:00
            exp_start_str = (tl.get("expected_start") or "08:00:00")[:5]
            is_night = (exp_start_str >= "18:00" or exp_start_str <= "06:00") \
                       or (ti.hour >= 18 and to.hour <= 12)
            if not is_night and to <= ti:
                chk(f"{emp_no} {wd}: time_out after time_in", False,
                    f"in={t_in} out={t_out}")
                out_before_in += 1

        gross = tl.get("gross_hours", 0) or 0
        if gross < 0:
            chk(f"{emp_no} {wd}: gross_hours >= 0", False, f"gross={gross}")
            neg_gross += 1

        late = tl.get("late_minutes", 0) or 0
        if late < 0:
            chk(f"{emp_no} {wd}: late_minutes >= 0", False, f"late={late}")
            negative_late += 1

        # Sanity: if late_minutes > 0 but gross_hours == expected, flag
        exp_hrs = tl.get("expected_hours") or 8
        if late > 120 and gross >= exp_hrs:
            chk(f"{emp_no} {wd}: late 120min but full hours logged", False,
                f"late={late}m gross={gross}h", warn_only=True)

    note(f"time_out before time_in:   {out_before_in}")
    note(f"Negative gross_hours:      {neg_gross}")
    note(f"Negative late_minutes:     {negative_late}")

    # Corrections
    corrs = q("dtr_corrections").select("*").eq("company_id", cid).execute().data
    pend  = [c for c in corrs if c["status"] == "pending"]
    chk("No stale pending corrections (>7 days old)", all(
        (date.today() - date.fromisoformat(c["created_at"][:10])).days <= 7
        for c in pend
    ), f"{len(pend)} pending" if pend else "", warn_only=True)
    note(f"DTR corrections: {len(corrs)} total, {len(pend)} pending")

# ═══════════════════════════════════════════════════════════════════════════════
# CHECK 4 — Payroll
# ═══════════════════════════════════════════════════════════════════════════════

def check_payroll(cid, employees):
    sep("CHECK 4 -- Payroll")

    periods = q("pay_periods").select("*").eq("company_id", cid).order("period_start").execute().data
    chk("At least 1 pay period exists", len(periods) >= 1, f"{len(periods)} found")
    note(f"Pay periods: {len(periods)}")
    for p in periods:
        note(f"  {p['period_start']} to {p['period_end']}  [{p['status']}]")

    emp_ids = [e["id"] for e in employees]

    for period in periods:
        pid   = period["id"]
        label = f"{period['period_start']} [{period['status']}]"

        entries = q("payroll_entries").select("*") \
            .eq("pay_period_id", pid).execute().data

        if period["status"] in ("finalized", "reviewed"):
            # Only check employees hired on or before the period end
            period_end_date = period["period_end"]
            eligible = [e for e in employees
                        if (e.get("date_hired") or "2000-01-01") <= period_end_date]
            entry_emp_ids = {e["employee_id"] for e in entries}
            missing = [e for e in eligible if e["id"] not in entry_emp_ids]
            chk(f"{label}: all eligible employees have payroll entry",
                len(missing) == 0,
                f"Missing: {[e['employee_no'] for e in missing]}" if missing else "")

        math_errors = 0
        sss_errors  = 0
        net_errors  = 0
        for entry in entries:
            gross  = php(entry.get("gross_pay", 0))
            net    = php(entry.get("net_pay", 0))
            total_ded = php(entry.get("total_deductions", 0))
            sss    = php(entry.get("sss_employee", 0))
            phic   = php(entry.get("philhealth_employee", 0))
            pagibig= php(entry.get("pagibig_employee", 0))
            wht    = php(entry.get("withholding_tax", 0))

            # Net pay math: gross - total_ded = net  (allow 1 PHP rounding)
            expected_net = round(gross - total_ded, 2)
            if abs(expected_net - net) > 1.0:
                emp_no = next((e["employee_no"] for e in employees if e["id"] == entry["employee_id"]), "?")
                chk(f"{label} {emp_no}: net = gross - deductions", False,
                    f"gross={gross:.2f} ded={total_ded:.2f} net={net:.2f} expected={expected_net:.2f}")
                net_errors += 1

            # SSS cap
            if sss > 1350.01:
                emp_no = next((e["employee_no"] for e in employees if e["id"] == entry["employee_id"]), "?")
                chk(f"{label} {emp_no}: SSS <= PHP 1,350", False, f"SSS={sss:.2f}")
                sss_errors += 1

            # Pag-IBIG cap
            if pagibig > 100.01:
                emp_no = next((e["employee_no"] for e in employees if e["id"] == entry["employee_id"]), "?")
                chk(f"{label} {emp_no}: Pag-IBIG <= PHP 100", False, f"Pag-IBIG={pagibig:.2f}")

            # No negative net pay
            if net < 0:
                emp_no = next((e["employee_no"] for e in employees if e["id"] == entry["employee_id"]), "?")
                chk(f"{label} {emp_no}: net pay >= 0", False, f"net={net:.2f}")

        if entries:
            chk(f"{label}: payroll math errors", math_errors == 0, f"{math_errors} found")
            chk(f"{label}: SSS cap violations",  sss_errors == 0,  f"{sss_errors} found")
            note(f"  {label}: {len(entries)} entries checked")

# ═══════════════════════════════════════════════════════════════════════════════
# CHECK 5 — Leave requests
# ═══════════════════════════════════════════════════════════════════════════════

def check_leaves(cid, employees):
    sep("CHECK 5 -- Leave Requests")

    leaves = q("leave_requests").select("*").eq("company_id", cid).execute().data
    note(f"Total leave requests: {len(leaves)}")

    emp_map = {e["id"]: e for e in employees}

    # Valid statuses
    valid_statuses = {"pending", "approved", "rejected", "cancelled"}
    bad_status = [l for l in leaves if l["status"] not in valid_statuses]
    chk("All leave requests have valid status", len(bad_status) == 0,
        f"{len(bad_status)} invalid" if bad_status else "")

    # Valid leave types
    valid_types = {"VL", "SL", "CL", "ML", "PL", "SPL"}
    bad_type = [l for l in leaves if l["leave_type"] not in valid_types]
    chk("All leave requests have valid type", len(bad_type) == 0,
        f"Invalid types: {list(set(l['leave_type'] for l in bad_type))}" if bad_type else "")

    # end_date >= start_date
    date_errors = 0
    for l in leaves:
        if l.get("start_date") and l.get("end_date"):
            if l["end_date"] < l["start_date"]:
                emp_no = emp_map.get(l["employee_id"], {}).get("employee_no", "?")
                chk(f"{emp_no} leave end >= start", False,
                    f"{l['start_date']} to {l['end_date']}")
                date_errors += 1

    chk("No leave requests with end < start", date_errors == 0, f"{date_errors} found")

    # Overlapping approved leaves per employee
    by_emp = defaultdict(list)
    for l in leaves:
        if l["status"] == "approved":
            by_emp[l["employee_id"]].append(l)

    overlap_count = 0
    for emp_id, emp_leaves in by_emp.items():
        emp_no = emp_map.get(emp_id, {}).get("employee_no", "?")
        sorted_leaves = sorted(emp_leaves, key=lambda x: x["start_date"])
        for i in range(len(sorted_leaves) - 1):
            a, b = sorted_leaves[i], sorted_leaves[i+1]
            if a["end_date"] >= b["start_date"]:
                chk(f"{emp_no}: overlapping approved leaves", False,
                    f"{a['start_date']}-{a['end_date']} overlaps {b['start_date']}-{b['end_date']}")
                overlap_count += 1

    chk("No overlapping approved leaves", overlap_count == 0, f"{overlap_count} found")

    # Days field sanity
    for l in leaves:
        days = l.get("days", 0) or 0
        if days <= 0 and l["status"] == "approved":
            emp_no = emp_map.get(l["employee_id"], {}).get("employee_no", "?")
            chk(f"{emp_no} approved leave has days > 0", False, f"days={days}", warn_only=True)

    # Stale pending (>5 days)
    stale = [l for l in leaves if l["status"] == "pending" and
             (date.today() - date.fromisoformat(l["created_at"][:10])).days > 5]
    chk("No stale pending leaves (>5 days)", len(stale) == 0,
        f"{len(stale)} stale" if stale else "", warn_only=True)

# ═══════════════════════════════════════════════════════════════════════════════
# CHECK 6 — OT requests
# ═══════════════════════════════════════════════════════════════════════════════

def check_ot(cid, employees):
    sep("CHECK 6 -- OT Requests")

    ots = q("overtime_requests").select("*").eq("company_id", cid).execute().data
    note(f"Total OT requests: {len(ots)}")

    emp_map = {e["id"]: e for e in employees}

    # Hours sanity (max 12 per day)
    for ot in ots:
        emp_no = emp_map.get(ot["employee_id"], {}).get("employee_no", "?")
        hours  = float(ot.get("hours") or 0)
        chk(f"{emp_no} OT {ot['ot_date']}: hours <= 12", hours <= 12,
            f"{hours}h", warn_only=True)
        chk(f"{emp_no} OT {ot['ot_date']}: hours > 0", hours > 0,
            f"{hours}h")

    # start_time before end_time
    time_errors = 0
    for ot in ots:
        if ot.get("start_time") and ot.get("end_time"):
            if ot["end_time"] <= ot["start_time"]:
                emp_no = emp_map.get(ot["employee_id"], {}).get("employee_no", "?")
                chk(f"{emp_no} OT {ot['ot_date']}: end_time > start_time", False,
                    f"{ot['start_time']} -> {ot['end_time']}")
                time_errors += 1

    chk("No OT requests with end <= start", time_errors == 0, f"{time_errors} found")

    # Stale pending
    stale = [o for o in ots if o["status"] == "pending" and
             (date.today() - date.fromisoformat(o["created_at"][:10])).days > 5]
    chk("No stale pending OT (>5 days)", len(stale) == 0,
        f"{len(stale)} stale" if stale else "", warn_only=True)

# ═══════════════════════════════════════════════════════════════════════════════
# CHECK 7 — Cross-table consistency
# ═══════════════════════════════════════════════════════════════════════════════

def check_cross_table(cid, employees):
    sep("CHECK 7 -- Cross-Table Consistency")

    # Payroll entries reference valid employee IDs
    emp_ids   = {e["id"] for e in employees}
    periods   = q("pay_periods").select("id").eq("company_id", cid).execute().data
    period_ids = [p["id"] for p in periods]

    if period_ids:
        entries = q("payroll_entries").select("employee_id,pay_period_id") \
            .in_("pay_period_id", period_ids).execute().data
        orphan_entries = [e for e in entries if e["employee_id"] not in emp_ids]
        chk("No payroll entries with orphaned employee_id", len(orphan_entries) == 0,
            f"{len(orphan_entries)} orphaned")

    # time_logs reference valid employees
    logs = q("time_logs").select("employee_id").eq("company_id", cid) \
        .gte("work_date", "2026-01-01").execute().data
    orphan_logs = [l for l in logs if l["employee_id"] not in emp_ids]
    chk("No time_logs with orphaned employee_id", len(orphan_logs) == 0,
        f"{len(orphan_logs)} orphaned")

    # leave_requests reference valid employees
    leaves = q("leave_requests").select("employee_id").eq("company_id", cid).execute().data
    orphan_leaves = [l for l in leaves if l["employee_id"] not in emp_ids]
    chk("No leave_requests with orphaned employee_id", len(orphan_leaves) == 0,
        f"{len(orphan_leaves)} orphaned")

    # OT requests reference valid employees
    ots = q("overtime_requests").select("employee_id").eq("company_id", cid).execute().data
    orphan_ots = [o for o in ots if o["employee_id"] not in emp_ids]
    chk("No overtime_requests with orphaned employee_id", len(orphan_ots) == 0,
        f"{len(orphan_ots)} orphaned")

    # DTR corrections reference valid employees
    corrs = q("dtr_corrections").select("employee_id").eq("company_id", cid).execute().data
    orphan_corrs = [c for c in corrs if c["employee_id"] not in emp_ids]
    chk("No dtr_corrections with orphaned employee_id", len(orphan_corrs) == 0,
        f"{len(orphan_corrs)} orphaned")

    # Approved OT requests that are included in a finalized payroll
    finalized = [p for p in q("pay_periods").select("*").eq("company_id", cid).execute().data
                 if p["status"] == "finalized"]
    for period in finalized:
        pid = period["id"]
        entries_map = {e["employee_id"]: e for e in
                       q("payroll_entries").select("*").eq("pay_period_id", pid).execute().data}
        approved_ots = q("overtime_requests").select("*").eq("company_id", cid) \
            .eq("status", "approved") \
            .gte("ot_date", period["period_start"]) \
            .lte("ot_date", period["period_end"]).execute().data

        for ot in approved_ots:
            entry = entries_map.get(ot["employee_id"])
            emp_no = next((e["employee_no"] for e in employees if e["id"] == ot["employee_id"]), "?")
            if entry:
                ot_pay = php(entry.get("overtime_pay", 0))
                chk(f"{emp_no} approved OT reflected in finalized payroll",
                    ot_pay > 0,
                    f"period={period['period_start']} ot_pay=PHP {ot_pay:.2f}", warn_only=True)
            else:
                chk(f"{emp_no} has payroll entry in finalized period with approved OT", False,
                    f"period={period['period_start']}")

# ═══════════════════════════════════════════════════════════════════════════════
# CHECK 8 — Dashboard metrics (simulate what the dashboard would show)
# ═══════════════════════════════════════════════════════════════════════════════

def check_dashboard(cid, employees):
    sep("CHECK 8 -- Dashboard Metrics Simulation")

    # Headcount
    active_count = len(employees)
    note(f"Active employee headcount: {active_count}")
    chk("Headcount > 0", active_count > 0)

    # Pending approvals
    leave_pend = q("leave_requests").select("id", count="exact").eq("company_id", cid) \
        .eq("status", "pending").execute().count
    ot_pend    = q("overtime_requests").select("id", count="exact").eq("company_id", cid) \
        .eq("status", "pending").execute().count
    corr_pend  = q("dtr_corrections").select("id", count="exact").eq("company_id", cid) \
        .eq("status", "pending").execute().count
    note(f"Pending leave: {leave_pend}  OT: {ot_pend}  Corrections: {corr_pend}")

    # Pay periods
    periods = q("pay_periods").select("*").eq("company_id", cid).order("period_start").execute().data
    draft   = [p for p in periods if p["status"] == "draft"]
    final   = [p for p in periods if p["status"] == "finalized"]
    note(f"Pay periods: {len(periods)} total, {len(draft)} draft, {len(final)} finalized")

    if draft:
        period_ids = [p["id"] for p in periods]
        payroll_count = q("payroll_entries").select("id", count="exact") \
            .in_("pay_period_id", period_ids).execute().count if period_ids else 0
        note(f"Total payroll entries: {payroll_count}")
        expected = len(employees) * len(periods)
        coverage = payroll_count / expected * 100 if expected else 0
        chk(f"Payroll entry coverage >= 50%", coverage >= 50,
            f"{payroll_count}/{expected} ({coverage:.0f}%)", warn_only=True)

    # Recent time log activity
    today     = date.today()
    week_ago  = today - timedelta(days=7)
    recent    = q("time_logs").select("id", count="exact").eq("company_id", cid) \
        .gte("work_date", str(week_ago)).execute().count
    note(f"Time logs in last 7 days: {recent}")
    chk("Recent attendance activity exists", recent > 0,
        f"{recent} logs in last 7 days", warn_only=True)

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    log.info("=" * 66)
    log.info("  MABINI DIGITAL CO. -- EMPLOYER AUDIT / VALIDATION")
    log.info(f"  Run date: {datetime.today().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("=" * 66)

    # Load company
    rows = q("companies").select("*").eq("name", "Mabini Digital Co.").execute().data
    if not rows:
        log.critical("Mabini Digital Co. not found. Run seed first.")
        sys.exit(1)
    company = rows[0]
    cid     = company["id"]
    log.info(f"  Company: {company['name']}  id={cid[:8]}...")

    # Run all checks
    check_company_setup(cid, company)
    employees = check_employees(cid)
    check_attendance(cid, employees)
    check_payroll(cid, employees)
    check_leaves(cid, employees)
    check_ot(cid, employees)
    check_cross_table(cid, employees)
    check_dashboard(cid, employees)

    # Final report
    sep("AUDIT COMPLETE -- Final Report")
    if ISSUES:
        log.error(f"  {len(ISSUES)} ISSUE(S) FOUND:")
        for i, issue in enumerate(ISSUES, 1):
            log.error(f"    {i}. {issue}")
        log.info(f"\n  Full log: {LOG_FILE}")
        sys.exit(1)
    else:
        log.info("  ALL CHECKS PASSED (warnings may exist — review log)")
        log.info(f"  Full log: {LOG_FILE}")
        sys.exit(0)


from datetime import datetime   # needed for strftime in main
if __name__ == "__main__":
    main()
