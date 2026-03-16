"""
Payroll Comparison — Streamlit page.

Compares two finalized/paid pay periods side by side, highlighting:
- Summary metric deltas (gross, net, gov contributions, headcount)
- Per-employee changes in basic pay, gross, and net
- New employees, removed employees, and notable pay changes (>5%)
"""

import streamlit as st
from app.db_helper import get_db, get_company_id
from app.styles import inject_css


# ============================================================
# Helpers
# ============================================================

def _fmt(centavos: int) -> str:
    """Format integer centavos as Philippine peso string."""
    return f"₱{centavos / 100:,.2f}"


def _fmt_delta(centavos: int) -> str:
    """Format a centavo delta with sign and arrow indicator."""
    if centavos > 0:
        return f"▲ {_fmt(centavos)}"
    elif centavos < 0:
        return f"▼ {_fmt(abs(centavos))}"
    return "—"


def _delta_color(centavos: int) -> str:
    """Return Streamlit color tag name for a numeric delta."""
    if centavos > 0:
        return "green"
    elif centavos < 0:
        return "red"
    return "normal"


def _period_label(period: dict) -> str:
    """Human-readable label for a pay period dropdown."""
    return f"{period['period_start']} → {period['period_end']}  [{period['status'].upper()}]"


# ============================================================
# Database operations
# ============================================================

def _load_pay_periods() -> list[dict]:
    """Load all finalized/paid pay periods for this company, newest first."""
    db = get_db()
    result = (
        db.table("pay_periods")
        .select("*")
        .eq("company_id", get_company_id())
        .in_("status", ["finalized", "paid"])
        .order("period_start", desc=True)
        .execute()
    )
    return result.data


def _load_payroll_entries(pay_period_id: str) -> dict:
    """Return {employee_id: entry_row} for a given pay period."""
    db = get_db()
    result = (
        db.table("payroll_entries")
        .select("*")
        .eq("pay_period_id", pay_period_id)
        .execute()
    )
    return {row["employee_id"]: row for row in result.data}


def _load_employees() -> dict:
    """Return {employee_id: employee_row} for this company, ordered by last name."""
    db = get_db()
    result = (
        db.table("employees")
        .select("id, employee_no, first_name, last_name, basic_salary")
        .eq("company_id", get_company_id())
        .order("last_name")
        .execute()
    )
    return {e["id"]: e for e in result.data}


# ============================================================
# Comparison logic
# ============================================================

def _gov_contributions(entry: dict) -> int:
    """Sum of employee-side gov contributions + withholding tax (all in centavos)."""
    return (
        (entry.get("sss_employee") or 0)
        + (entry.get("philhealth_employee") or 0)
        + (entry.get("pagibig_employee") or 0)
        + (entry.get("withholding_tax") or 0)
    )


def _summary_totals(entries: dict) -> dict:
    """Aggregate gross, net, gov contributions, and headcount across all entries."""
    gross = sum(e.get("gross_pay") or 0 for e in entries.values())
    net = sum(e.get("net_pay") or 0 for e in entries.values())
    gov = sum(_gov_contributions(e) for e in entries.values())
    headcount = len(entries)
    return {"gross": gross, "net": net, "gov": gov, "headcount": headcount}


def _classify_change(gross_a: int, gross_b: int) -> str:
    """Classify a per-employee change relative to Period A gross pay."""
    if gross_a == 0:
        return "New"
    pct = abs(gross_b - gross_a) / gross_a
    if pct > 0.01:
        return "Changed"
    return "Same"


# ============================================================
# Main Page Render
# ============================================================

def render():
    inject_css()
    st.title("Payroll Comparison")
    st.caption("Compare two finalized pay periods to spot changes in pay, headcount, and government contributions.")

    # ------------------------------------------------------------------
    # Load periods — need at least 2 finalized to compare
    # ------------------------------------------------------------------
    periods = _load_pay_periods()

    if len(periods) < 2:
        st.info("You need at least 2 finalized pay periods to compare.")
        return

    # Build {id: period} lookup and ordered list of IDs
    period_by_id = {p["id"]: p for p in periods}
    period_ids = [p["id"] for p in periods]  # newest → oldest

    # ------------------------------------------------------------------
    # Period selector — two dropdowns side by side
    # Default: Period A = second-most-recent, Period B = most recent
    # ------------------------------------------------------------------
    col_a, col_b = st.columns(2)

    with col_a:
        id_a = st.selectbox(
            "Period A (Earlier)",
            options=period_ids,
            index=1,  # second-most-recent
            format_func=lambda x: _period_label(period_by_id[x]),
            key="cmp_period_a",
        )

    with col_b:
        id_b = st.selectbox(
            "Period B (Later)",
            options=period_ids,
            index=0,  # most recent
            format_func=lambda x: _period_label(period_by_id[x]),
            key="cmp_period_b",
        )

    # Guard: same period selected
    if id_a == id_b:
        st.warning("Please select two different periods.")
        return

    st.divider()

    # ------------------------------------------------------------------
    # Load data for both periods
    # ------------------------------------------------------------------
    entries_a = _load_payroll_entries(id_a)
    entries_b = _load_payroll_entries(id_b)
    employees = _load_employees()

    totals_a = _summary_totals(entries_a)
    totals_b = _summary_totals(entries_b)

    # ------------------------------------------------------------------
    # Summary metrics row
    # ------------------------------------------------------------------
    st.subheader("Summary")

    m1, m2, m3, m4 = st.columns(4)

    gross_delta = totals_b["gross"] - totals_a["gross"]
    net_delta = totals_b["net"] - totals_a["net"]
    gov_delta = totals_b["gov"] - totals_a["gov"]
    headcount_delta = totals_b["headcount"] - totals_a["headcount"]

    with m1:
        st.metric(
            "Total Gross Pay",
            _fmt(totals_b["gross"]),
            delta=f"{_fmt(abs(gross_delta))} {'▲' if gross_delta >= 0 else '▼'}",
            delta_color=_delta_color(gross_delta),
        )

    with m2:
        st.metric(
            "Total Net Pay",
            _fmt(totals_b["net"]),
            delta=f"{_fmt(abs(net_delta))} {'▲' if net_delta >= 0 else '▼'}",
            delta_color=_delta_color(net_delta),
        )

    with m3:
        st.metric(
            "Gov Contributions + WHT",
            _fmt(totals_b["gov"]),
            delta=f"{_fmt(abs(gov_delta))} {'▲' if gov_delta >= 0 else '▼'}",
            delta_color=_delta_color(gov_delta),
        )

    with m4:
        st.metric(
            "Headcount",
            totals_b["headcount"],
            delta=headcount_delta,
            delta_color=_delta_color(headcount_delta),
        )

    st.divider()

    # ------------------------------------------------------------------
    # Per-employee comparison table
    # ------------------------------------------------------------------
    st.subheader("Per-Employee Comparison")

    # Union of all employee IDs across both periods
    all_emp_ids = set(entries_a.keys()) | set(entries_b.keys())

    # Build rows for the table
    table_rows = []
    new_employees = []
    removed_employees = []
    notable_changes = []  # gross changed >5%

    for emp_id in all_emp_ids:
        emp = employees.get(emp_id)
        if emp is None:
            # Employee record deleted — use placeholder name
            name = f"[Unknown #{emp_id[:8]}]"
        else:
            name = f"{emp['last_name']}, {emp['first_name']}"

        in_a = emp_id in entries_a
        in_b = emp_id in entries_b

        entry_a = entries_a.get(emp_id, {})
        entry_b = entries_b.get(emp_id, {})

        basic_a = entry_a.get("basic_pay") or 0
        basic_b = entry_b.get("basic_pay") or 0
        gross_a = entry_a.get("gross_pay") or 0
        gross_b = entry_b.get("gross_pay") or 0
        net_a = entry_a.get("net_pay") or 0
        net_b = entry_b.get("net_pay") or 0

        # Determine status
        if in_b and not in_a:
            status = "New"
            new_employees.append({"name": name, "emp": emp, "entry_b": entry_b})
        elif in_a and not in_b:
            status = "Removed"
            removed_employees.append({"name": name, "emp": emp, "entry_a": entry_a})
        else:
            status = _classify_change(gross_a, gross_b)

        # Flag notable changes (>5% gross shift, excluding new/removed)
        if status == "Changed" and gross_a > 0:
            pct_change = (gross_b - gross_a) / gross_a
            if abs(pct_change) > 0.05:
                notable_changes.append({
                    "name": name,
                    "emp": emp,
                    "gross_a": gross_a,
                    "gross_b": gross_b,
                    "pct_change": pct_change,
                })

        table_rows.append({
            "name": name,
            "basic_a": basic_a,
            "basic_b": basic_b,
            "gross_a": gross_a,
            "gross_b": gross_b,
            "net_a": net_a,
            "net_b": net_b,
            "status": status,
        })

    # Sort: New first, then Removed, then Changed, then Same — then alphabetical
    status_order = {"New": 0, "Removed": 1, "Changed": 2, "Same": 3}
    table_rows.sort(key=lambda r: (status_order.get(r["status"], 9), r["name"]))

    # Render table using st.dataframe via a list of display dicts
    # We manually render rows with markdown for color support
    header_cols = st.columns([3, 2, 2, 3, 3, 3, 3, 2])
    headers = ["Employee", "Basic A", "Basic B", "Gross A", "Gross B", "Net A", "Net B", "Status"]
    for col, hdr in zip(header_cols, headers):
        col.markdown(f"**{hdr}**")

    st.markdown("---")

    for row in table_rows:
        cols = st.columns([3, 2, 2, 3, 3, 3, 3, 2])

        # Employee name
        cols[0].markdown(row["name"])

        # Basic pay columns
        cols[1].markdown(_fmt(row["basic_a"]) if row["basic_a"] else "—")

        # Show basic pay change indicator
        if row["basic_b"] != row["basic_a"] and row["status"] not in ("New", "Removed"):
            basic_diff = row["basic_b"] - row["basic_a"]
            color = "green" if basic_diff > 0 else "red"
            cols[2].markdown(f":{color}[{_fmt(row['basic_b'])}]")
        else:
            cols[2].markdown(_fmt(row["basic_b"]) if row["basic_b"] else "—")

        # Gross pay A
        cols[3].markdown(_fmt(row["gross_a"]) if row["gross_a"] else "—")

        # Gross pay B with delta
        if row["status"] not in ("New", "Removed"):
            gross_d = row["gross_b"] - row["gross_a"]
            if gross_d != 0:
                color = "green" if gross_d > 0 else "red"
                arrow = "▲" if gross_d > 0 else "▼"
                cols[4].markdown(f":{color}[{_fmt(row['gross_b'])} {arrow}]")
            else:
                cols[4].markdown(_fmt(row["gross_b"]) if row["gross_b"] else "—")
        else:
            cols[4].markdown(_fmt(row["gross_b"]) if row["gross_b"] else "—")

        # Net pay A
        cols[5].markdown(_fmt(row["net_a"]) if row["net_a"] else "—")

        # Net pay B with delta
        if row["status"] not in ("New", "Removed"):
            net_d = row["net_b"] - row["net_a"]
            if net_d != 0:
                color = "green" if net_d > 0 else "red"
                arrow = "▲" if net_d > 0 else "▼"
                cols[6].markdown(f":{color}[{_fmt(row['net_b'])} {arrow}]")
            else:
                cols[6].markdown(_fmt(row["net_b"]) if row["net_b"] else "—")
        else:
            cols[6].markdown(_fmt(row["net_b"]) if row["net_b"] else "—")

        # Status badge
        status_colors = {
            "New": "green",
            "Removed": "red",
            "Changed": "orange",
            "Same": "gray",
        }
        s_color = status_colors.get(row["status"], "gray")
        cols[7].markdown(f":{s_color}[{row['status']}]")

    st.divider()

    # ------------------------------------------------------------------
    # Change highlights section
    # ------------------------------------------------------------------
    has_highlights = new_employees or removed_employees or notable_changes

    if has_highlights:
        st.subheader("Change Highlights")

        # New employees
        if new_employees:
            st.markdown("**🆕 New Employees** — appeared in Period B but not Period A")
            for item in new_employees:
                entry_b = item["entry_b"]
                gross = entry_b.get("gross_pay") or 0
                net = entry_b.get("net_pay") or 0
                st.markdown(
                    f"- :green[{item['name']}] — "
                    f"Gross: {_fmt(gross)} | Net: {_fmt(net)}"
                )
            st.markdown("")

        # Removed employees
        if removed_employees:
            st.markdown("**❌ Removed Employees** — in Period A but not in Period B")
            for item in removed_employees:
                entry_a = item["entry_a"]
                gross = entry_a.get("gross_pay") or 0
                net = entry_a.get("net_pay") or 0
                st.markdown(
                    f"- :red[{item['name']}] — "
                    f"Last Gross: {_fmt(gross)} | Last Net: {_fmt(net)}"
                )
            st.markdown("")

        # Notable pay changes (>5%)
        if notable_changes:
            st.markdown("**📈 Notable Changes** — gross pay shifted by more than 5%")
            # Sort by absolute percent change descending
            notable_changes.sort(key=lambda x: abs(x["pct_change"]), reverse=True)
            for item in notable_changes:
                pct = item["pct_change"] * 100
                color = "green" if pct > 0 else "red"
                arrow = "▲" if pct > 0 else "▼"
                gross_delta_val = item["gross_b"] - item["gross_a"]
                st.markdown(
                    f"- :{color}[{item['name']}] — "
                    f"{_fmt(item['gross_a'])} → {_fmt(item['gross_b'])} "
                    f"({arrow} {_fmt(abs(gross_delta_val))}, {abs(pct):.1f}%)"
                )
