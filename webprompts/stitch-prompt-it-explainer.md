# GeNXcript Payroll SaaS — Technical Explainer for IT Teams

## INSTRUCTION

Generate a complete, single-file, self-contained HTML technical documentation website (HTML + CSS + JS inline) for **GeNXcript Payroll** — a cloud-based Payroll & HR Management System built for Philippine SMEs. This is a **technical deep-dive for IT teams** — NOT a marketing page. The audience is senior developers, sysadmins, and IT architects who need to understand the architecture, data flow, deployment, security, and integration points of the system.

The output must be a single HTML file. No external dependencies except Google Fonts. All CSS and JS inline. Responsive. Print-friendly.

---

## GLOBAL DESIGN SYSTEM

### Colors (Dark Developer Theme)
```
--bg:          #0f1117     /* Near-black page background */
--surface:     #1a1d27     /* Dark card / panel background */
--surface2:    #141720     /* Slightly darker variant for nested panels */
--border:      #2d3748     /* Subtle border */
--border-light:#3d4758     /* Lighter border for hover states */
--primary:     #3b82f6     /* Blue — headings, links, active nav */
--primary-dim: #1e3a5f     /* Dim blue for backgrounds */
--accent:      #10b981     /* Green — success, active status, checkmarks */
--accent-dim:  #064e3b     /* Dim green for backgrounds */
--warning:     #f59e0b     /* Amber — warnings, highlights */
--warning-dim: #3b2f0a     /* Dim amber for backgrounds */
--error:       #ef4444     /* Red — errors, danger, breaking changes */
--error-dim:   #3b1515     /* Dim red for backgrounds */
--text:        #e2e8f0     /* Primary text — light gray */
--text2:       #94a3b8     /* Secondary text — muted */
--text3:       #64748b     /* Tertiary text — very muted */
--code:        #a78bfa     /* Purple — inline code, technical terms */
--code-bg:     #1e1b2e     /* Code block background */
--code-border: #2d2640     /* Code block border */
--tag-blue:    #60a5fa     /* Tag / label blue */
--tag-green:   #34d399     /* Tag / label green */
--tag-amber:   #fbbf24     /* Tag / label amber */
--tag-purple:  #c084fc     /* Tag / label purple */
--tag-red:     #f87171     /* Tag / label red */
```

### Typography
- **Primary font:** `'Plus Jakarta Sans', sans-serif` — import from `https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap`
- **Code font:** `'Source Code Pro', monospace` — import from `https://fonts.googleapis.com/css2?family=Source+Code+Pro:wght@400;500;600&display=swap`
- Page title: 800 weight, 2rem
- Section headings (h2): 700 weight, 1.75rem, color var(--primary)
- Subsection headings (h3): 600 weight, 1.25rem, color var(--text)
- Body text: 400 weight, 0.9375rem (15px), line-height 1.7, color var(--text)
- Secondary text: 0.875rem, color var(--text2)
- Code inline: `Source Code Pro` 500 weight, 0.8125rem, color var(--code), background var(--code-bg), padding 2px 6px, border-radius 4px
- Code blocks: `Source Code Pro` 400 weight, 0.8125rem, background var(--code-bg), border 1px solid var(--code-border), border-radius 8px, padding 16px, overflow-x auto

### Layout
- Max content width: 1100px
- Sidebar: fixed left, 260px expanded, 56px collapsed
- Section padding: 48px vertical
- Card border-radius: 12px
- Card border: 1px solid var(--border)
- Card background: var(--surface)

### Effects
- Card hover: border-color transitions to var(--border-light), subtle box-shadow `0 4px 12px rgba(0,0,0,0.3)`
- Smooth scroll behavior on html element
- Transitions: `transition: all 0.2s ease`
- Collapsible sections: CSS + JS, rotatable chevron icon, smooth max-height animation
- Print: `@media print` — white background, black text, no sidebar, no interactive elements, page-break-inside:avoid on cards

---

## PAGE STRUCTURE

### Fixed Left Sidebar Navigation
- Fixed position, full viewport height
- Background: var(--surface2) with right border
- Top: "GeNXcript Payroll" title + "Technical Documentation" subtitle in small caps
- Below: scrollable list of section links, each with:
  - A small emoji or Unicode icon (no images)
  - Section name
  - Active state: left border accent + text color var(--primary)
- Collapsible: hamburger toggle at top; on collapse, show only icons (56px width); on expand, show icons + labels (260px)
- Smooth scroll to section on click
- Highlight current section based on scroll position (Intersection Observer)
- At bottom of sidebar: "v1.0 — Last updated 2026-03-27" in small muted text

### Top Search Bar
- Sticky within the content area (not the sidebar)
- Input field with magnifying glass icon
- JS: on keyup, scans all section headings and content paragraphs; hides sections that don't match; highlights matching text with a yellow background span
- "X" clear button to reset search

### Main Content Area
- Left margin to accommodate sidebar
- Smooth scroll between sections
- Each section has an `id` for anchor linking
- Auto-generated Table of Contents at the very top (before Section 1) — a clickable outline of all sections and subsections

---

## SECTION 1: System Architecture Overview

### 1.1 — High-Level Architecture Diagram
Build a **CSS-only 3-tier architecture diagram** (no images, no SVG, no canvas). Use colored `div` boxes with rounded corners, connected by CSS pseudo-element lines/arrows:

```
┌─────────────────────────────────────────────────────────────────┐
│  CLIENT TIER                                                     │
│  ┌─────────────┐                                                │
│  │  Browser     │  HTML/CSS/JS rendered by Streamlit             │
│  │  (Any OS)    │  Custom components via components.html()       │
│  └──────┬──────┘                                                │
│         │ HTTPS (Streamlit WebSocket + HTTP)                     │
├─────────┼───────────────────────────────────────────────────────┤
│  APPLICATION TIER                                                │
│  ┌──────┴──────┐  ┌──────────────┐  ┌─────────────────┐        │
│  │  Streamlit   │  │  Backend     │  │  Email Sender   │        │
│  │  Server      │──│  Engines     │  │  (SMTP)         │        │
│  │  (Python)    │  │  (payroll,   │  └─────────────────┘        │
│  │              │  │   dtr,       │                              │
│  │  main.py     │  │   deadlines) │                              │
│  └──────┬──────┘  └──────────────┘                              │
│         │ HTTPS (Supabase REST API)                              │
├─────────┼───────────────────────────────────────────────────────┤
│  DATA TIER                                                       │
│  ┌──────┴──────┐  ┌──────────────┐  ┌─────────────────┐        │
│  │  PostgreSQL  │  │  GoTrue Auth │  │  Supabase       │        │
│  │  17 (via     │  │  (JWT-based) │  │  Storage        │        │
│  │  Supabase)   │  │              │  │  (photos, docs) │        │
│  └─────────────┘  └──────────────┘  └─────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

Render this visually with CSS boxes, colored headers per tier (blue for client, green for app, purple for data), and dotted connector lines between them. Each box is clickable to expand a tooltip with more detail.

### 1.2 — Tech Stack Breakdown
Display as a responsive card grid (3 columns on desktop, 1 on mobile). Each card:

| Component | Technology | Details |
|-----------|-----------|---------|
| Frontend | Streamlit (Python) | Custom HTML/CSS/JS via `st.markdown(unsafe_allow_html=True)` and `components.html()`. No React/Vue/Angular. CSS-in-Python via `styles.py` with 10+ theme variants. |
| Backend | Python 3.12 + Streamlit 1.x | Single-process monolith. Streamlit's execution model: entire script re-executes on every user interaction. Backend engines in `backend/` (payroll.py, dtr.py, deadlines.py). |
| Database | PostgreSQL 17 via Supabase | Managed PostgreSQL with PostgREST auto-generated REST API. 28+ migration files. All monetary values in centavos (integer) to avoid floating-point errors. |
| Auth | Supabase GoTrue | JWT-based authentication. Password hashing handled by GoTrue (bcrypt). PKCE flow for password resets. Service role key for admin operations. |
| Storage | Supabase Storage | Buckets: `employee-photos` (compressed JPEG, max 200px), `dtr-snapshots` (clock-in face photos, compressed 640px JPEG quality 55). |
| Email | SMTP (Python smtplib) | `app/email_sender.py` — sends temp password emails for employee portal invites. Branded HTML templates. Falls back to manual sharing if SMTP not configured. |
| Hosting | Cloud VM / Docker | Run via `streamlit run app/main.py`. HTTPS via ngrok or Cloudflare Tunnel for portal GPS. |

### 1.3 — Key Design Decisions (WHY)
Collapsible accordion. Each item has a question ("Why X?") and an expandable answer:

- **Why Streamlit?** — Rapid prototyping for a Python team. No separate frontend build step. Rich widget library. Custom HTML/CSS/JS injection when Streamlit's widgets are insufficient (modals, org charts, maps). Tradeoff: every user interaction re-executes the full script (managed via caching). Tradeoff: limited to single-thread per user session.
- **Why Supabase (not raw PostgreSQL)?** — Managed PostgreSQL with zero-ops. Built-in JWT auth (GoTrue) eliminates custom auth. PostgREST provides instant REST API. Storage API for file uploads. Row Level Security for defense-in-depth. Free tier sufficient for development and small production. Region: ap-northeast-1 (Tokyo) — closest to PH.
- **Why monolith-first?** — Single `main.py` entry point. No microservices, no API gateway, no message queues. Appropriate for MVP/early stage (< 50 concurrent users). All modules are Python files in `app/pages/`. Easier to debug, deploy, and iterate. Can be decomposed later if needed.
- **Why centavos (integer) for money?** — IEEE 754 floating-point cannot represent ₱0.01 exactly. Using integer centavos (₱1,500.00 = 150000) eliminates rounding errors in government contribution calculations where ₱1 discrepancy triggers filing rejection.
- **Why service role key (bypass RLS) in the app?** — Streamlit runs server-side; the browser never sees the service key. Manual `company_id` filtering on every query provides tenant isolation. Service role avoids complex RLS policy management for the 5-role hierarchy. RLS is enabled as defense-in-depth but not the primary isolation mechanism.

---

## SECTION 2: Data Flow Diagrams

Build interactive CSS/JS diagrams for each flow. Each diagram uses colored boxes (div elements) connected by arrows (CSS pseudo-elements or border tricks). Clicking a box expands it to show more detail in a slide-down panel.

### 2.1 — Login Flow
```
[Browser] → [Streamlit main.py] → [GoTrue Auth API] → [JWT Returned]
                                                            ↓
                                                    [Session Created]
                                                            ↓
[user_company_access] ← [Query by user_id] → [company_id + role]
        ↓
[Server-side cache] ← [UUID session token] → [st.query_params["sid"]]
        ↓
[Page routing] → [Dashboard / Employee Portal based on role]
```

Detail panels:
- **Browser**: User enters email (or Employee ID like "EMP-001") + password. Employee ID is resolved to email via `_resolve_login_email()` using service role client (pre-auth lookup).
- **GoTrue Auth**: `sign_in_with_password()` — validates credentials, returns JWT + user object. Timeout set to 15s (PH→Tokyo latency).
- **Session Store**: `_session_cache()` is a `@st.cache_resource` dict (lives for Streamlit process lifetime). Token is a UUID stored in URL as `?sid=TOKEN`. On F5 refresh, `restore_from_query_params()` reads the sid and restores session state.
- **First-time employee login**: If no `user_company_access` row exists but an `employees` row matches the email, auto-create access with `role=employee` and link `user_id`.
- **Password reset**: PKCE flow — Supabase sends email with `?code=TOKEN`, app exchanges code for session via `exchange_recovery_code()`.

### 2.2 — Payroll Computation Flow
```
[Employee Master] → [Basic Salary + Tax Status + Employment Type]
        ↓
[DTR Engine] → [Absent Days, OT Hours, NSD Hours, Late/UT]
        ↓
[Government Rates] → [SSS Bracket, PhilHealth %, Pag-IBIG Tier, BIR TRAIN Brackets]
        ↓
[Payroll Engine (backend/payroll.py)]
        ↓
[Compute: Gross = Basic + OT + Holiday + NSD + Allowances - Absent Deduction]
[Compute: SSS EE/ER, PhilHealth EE/ER, Pag-IBIG EE/ER]
[Compute: Taxable Income = Gross - SSS_EE - PhilHealth_EE - PagIBIG_EE]
[Compute: WHT via TRAIN Law 6-bracket progressive table]
[Compute: Net = Gross - Total Deductions]
        ↓
[payroll_entries table] → [One row per employee per pay period]
        ↓
[Payslip PDF generation] → [Download / Email]
```

Detail panels for each computation step.

### 2.3 — Multi-Tenant Data Isolation
```
[Every Query] → [.eq("company_id", session.company_id)]
        ↓
[Service Role Client] → [Bypasses RLS — manual filtering is primary guard]
        ↓
[RLS Policies] → [Defense-in-depth — 20+ policies across all tables]
        ↓
[user_company_access] → [Maps auth.uid() → company_id(s) + role]
```

Explain: Every table has a `company_id` column. The `get_company_id()` helper reads from `st.session_state` (server-side). A user can belong to multiple companies via `user_company_access`. Company switching updates session state and cache. No cross-tenant data leakage is possible because every DB call filters by `company_id`.

### 2.4 — Caching Strategy Diagram
Visual 3-layer cake diagram:

| Layer | Mechanism | Scope | TTL | Example |
|-------|-----------|-------|-----|---------|
| App-Level | `@st.cache_resource` | Shared across all users | Process lifetime (or TTL) | DB connection (45 min TTL), session cache (permanent), hierarchy data |
| Data Cache | `@st.cache_data` | Per-function, keyed by args | TTL-based (60–300s) | Employee lists, payroll history, government rates, dashboard stats |
| Session State | `st.session_state` | Per-user session | Until logout/server restart | Current selections, dialog state, form inputs, company_id, role |

---

## SECTION 3: Database Schema

### 3.1 — Entity Relationship Diagram
Build a CSS-only ER diagram. Each table is a card with:
- Table name as header (bold, colored)
- Column list with types (use code font)
- Primary key marked with 🔑
- Foreign keys marked with 🔗 and a colored line to the referenced table

Core tables to show with relationships:

**Tenant & Auth:**
- `companies` (id, name, address, region, pay_frequency, bir_tin, sss_employer_no, philhealth_employer_no, pagibig_employer_no, daily_rate_divisor, leave_vl/sl/cl_days)
- `user_company_access` (user_id → auth.users, company_id → companies, role)
- `audit_logs` (company_id → companies, user_id, action, entity_type, entity_id, details JSONB)

**Employee:**
- `employees` (id, company_id → companies, employee_no [UNIQUE per company], first_name, last_name, position, department, employment_type, date_hired, basic_salary [centavos], salary_type, tax_status, sss_no, philhealth_no, pagibig_no, bir_tin, is_active, user_id → auth.users, reports_to → employees, schedule_id → schedules, photo_url)
- `employee_profiles` (extended info: education, addresses, contact details)

**Payroll:**
- `pay_periods` (id, company_id → companies, period_start, period_end, payment_date, status [draft→reviewed→finalized→paid], reviewed_by, reviewed_at)
- `payroll_entries` (id, pay_period_id → pay_periods, employee_id → employees, basic_pay, overtime_pay, holiday_pay, night_differential, allowances_nontaxable, allowances_taxable, commission, thirteenth_month_accrual, gross_pay, sss_employee/employer, philhealth_employee/employer, pagibig_employee/employer, withholding_tax, sss_loan, pagibig_loan, cash_advance, other_deductions, total_deductions, net_pay) — ALL in centavos

**Time & Attendance:**
- `schedules` (id, company_id, name, start_time, end_time, break_minutes, working_days, is_overnight)
- `time_logs` (id, company_id, employee_id, work_date, schedule snapshot fields, time_in/out with timestamps + GPS coords + snapshot URLs, computed: gross_hours/late_minutes/undertime_minutes/ot_hours/nsd_hours, status, is_out_of_range)
- `dtr_corrections` (employee-submitted correction requests with approval workflow)
- `company_locations` (GPS geofencing sites: name, lat/lng, radius_m)

**Leave & OT:**
- `leave_requests` (employee_id, leave_type [VL/SL/CL], start_date, end_date, days, status [pending/approved/rejected])
- `overtime_requests` (employee_id, ot_date, start_time, end_time, hours, status)
- `leave_entitlement_templates` (named tiers with VL/SL/CL days, carry-over caps, conversion rates)

**Government:**
- `government_rates` (agency [SSS/PhilHealth/PagIBIG/BIR], rate_type, value JSONB, effective_date) — versioned rate tables
- `holidays` (date, name, type [regular/special_non_working/special_working], observed_date)
- `remittance_records` (company × agency × month tracking)

**Other:**
- `deduction_types` (company-scoped custom deductions)
- `user_preferences` (theme, date format, display settings per user)
- `sync_queue` (future offline-first capability)

### 3.2 — Migration File Index
Display as a styled table with alternating row colors:

| # | File | Description |
|---|------|-------------|
| 001 | `001_schema.sql` | Core schema: companies, employees, pay_periods, payroll_entries, deduction_types, government_rates, user_company_access, sync_queue + RLS policies |
| 002 | `002_seed_government_rates.sql` | 2025 SSS (44 brackets), PhilHealth (5%), Pag-IBIG (tiered), BIR TRAIN Law (6 brackets) |
| 003 | `003_dev_setup.sql` | Development environment seed data |
| 004 | `004_holidays.sql` | 2025–2026 Philippine national holidays (regular + special non-working + special working) |
| 005 | `005_approval_workflow.sql` | Payroll approval: reviewed_by, reviewed_at columns; status flow draft→reviewed→finalized→paid |
| 006 | `006_employee_self_service.sql` | Employee portal foundation |
| 007 | `007_leave_ot_requests.sql` | Leave requests (VL/SL/CL) + overtime requests + approval workflow + RLS |
| 008 | `008_leave_entitlement_templates.sql` | Named leave tiers with configurable VL/SL/CL days |
| 009 | `009_company_custom_holidays.sql` | Company-specific custom holiday CRUD |
| 010 | `010_employee_extended_info.sql` | Regularization/separation dates, education, contact info, addresses |
| 011 | `011_leave_balance_policy.sql` | Leave credits, carry-over, cash conversion |
| 012 | `012_schedules.sql` | Shift schedule profiles + per-employee assignment + single-day overrides |
| 013 | `013_dtr.sql` | Time logs (GPS, snapshots, computed attendance), DTR corrections, company locations (geofencing) |
| 014 | `014_remittance_records.sql` | Government remittance tracking per agency per month |
| 015 | `015_org_structure.sql` | Organizational structure support |
| 016 | `016_manager_hierarchy.sql` | Manager hierarchy with recursive SQL function `get_supervisor_tree()` |
| 017 | `017_special_leaves.sql` | Special leave types |
| 018 | `018_company_hr_policy.sql` | Company HR policy configuration |
| 019 | `019_holiday_observed.sql` | `observed_date` column for weekend-shifted holidays |
| 020 | `020_nsd_break_tracking.sql` | Night Shift Differential hours + portal break tracking (break_out/break_in/actual_break_minutes/overbreak_minutes) |
| 021 | `021_daily_rate_divisor.sql` | Company-level daily rate divisor (22/26/30) |
| 022 | `022_absent_deduction.sql` | Absent deduction computation support |
| 023 | `023_rls_user_preferences.sql` | RLS hardening for user_preferences table |
| 024 | `024_rls_audit_logs.sql` | RLS hardening for audit_logs table |
| 025 | `025_reports_to.sql` | `reports_to` self-referencing FK on employees for supervisor hierarchy |
| 026 | `026_employee_photo.sql` | `photo_url` column + Supabase Storage bucket |
| 027 | `027_require_break_clock.sql` | Company setting to require break clock-in/out |
| 028 | `028_user_roles.sql` | 5-role model (admin/hr_manager/payroll_officer/supervisor/employee), updated RLS policies |

### 3.3 — Multi-Tenant Pattern
Show a code block with the pattern used in every query:
```python
# Every database query follows this pattern:
db = get_db()  # Service role client (bypasses RLS)
company_id = get_company_id()  # From session state

result = (
    db.table("employees")
    .select("*")
    .eq("company_id", company_id)  # ← TENANT ISOLATION
    .eq("is_active", True)
    .execute()
)
```

---

## SECTION 4: Module Architecture

### 4.1 — Page Module Map
Display as a visual grid/card layout. Each card represents a page module:

| Module File | Display Name | Access Roles | Key Tables | Cache | Description |
|------------|-------------|-------------|-----------|-------|-------------|
| `_dashboard.py` | Dashboard | Admin, HR Mgr, Payroll Officer, Supervisor | employees, pay_periods, payroll_entries, leave_requests, overtime_requests | `@st.cache_data(ttl=120)` + session_state | Bento grid: KPI cards, payroll expenditure, recent activity, quick actions, mini calendar. Supervisor variant: team-scoped, financial data hidden. |
| `_employees.py` | Employees | Admin, HR Mgr, Payroll Officer (RO) | employees, employee_profiles, leave_requests, overtime_requests | `@st.cache_data` with `_cid` keying | Card grid with department grouping, photo avatars, swipe-to-reveal actions. CRUD + bulk operations. Leave/OT approval. Leave balance report. |
| `_payroll_run.py` | Payroll Run | Admin, Payroll Officer | pay_periods, payroll_entries, employees, government_rates, time_logs | `@st.cache_data` for rates + employee lists | Create pay period, compute per-employee (auto-suggests from DTR), review breakdown, submit→approve→finalize workflow. |
| `_payroll_comparison.py` | Payroll Comparison | Admin, HR Mgr (RO), Payroll Officer | payroll_entries, pay_periods, employees | `@st.cache_data` | Period-over-period analysis: new hires, salary changes, OT spikes, anomaly detection. |
| `_ot_heatmap.py` | Workforce Analytics | Admin, HR Mgr, Payroll Officer (RO) | time_logs, employees, schedules | `@st.cache_data` | 4 tabs: OT Analytics (heatmap + top contributors), Late Monitoring (bubble calendar), Undertime, Break Monitoring. Spotfire-style linked charts. |
| `_dtr.py` | Attendance | Admin, HR Mgr, Payroll Officer (RO), Supervisor (RO) | time_logs, employees, schedules, dtr_corrections | `@st.cache_data` | Daily time record: per-date admin view, per-employee summary, DTR corrections approval. NSD hours column. |
| `_government_reports.py` | Government Reports | Admin, HR Mgr, Payroll Officer | payroll_entries, employees, government_rates | `@st.cache_data` | SSS R3, PhilHealth RF-1, Pag-IBIG MCRF, BIR 1601-C, BIR 2316, BIR 1604-C, DOLE 13th Month. PDF export. |
| `_calendar_view.py` | Calendar | Admin, HR Mgr, Payroll Officer, Supervisor (RO) | pay_periods, holidays, company_holidays | `@st.cache_data` | CSS Grid month calendar with pay period spans, holidays, remittance deadlines. Upcoming events sidebar with countdowns. |
| `_company_setup.py` | Company Setup | Admin, HR Mgr (RO) | companies, employees, schedules, holidays, company_locations, user_company_access | Minimal caching | Tabs: Profile, Departments, Schedules, Holidays, Locations (Leaflet maps), Users & Roles, Payroll Policy. d3-org-chart. |
| `_preferences.py` | Preferences | All staff roles | user_preferences | session_state | Theme selection (10+ themes), date format, display options. Persisted per user. |
| `_employee_portal.py` | Employee Portal | Employee | employees, time_logs, payroll_entries, leave_requests, overtime_requests | session_state | 5 tabs: Profile, Payslips, Time & Leave, Documents (COE, BIR 2316), Preferences. Portal clock-in with GPS + photo. |
| `_login.py` | Login | Unauthenticated | user_company_access, employees | None | Email or Employee ID login. Forgot password (PKCE flow). Link to register. |
| `_register.py` | Register | Unauthenticated | companies, user_company_access | None | New company signup with region + pay frequency. |

### 4.2 — Backend Engines

| Engine File | Purpose | Key Functions |
|------------|---------|---------------|
| `backend/payroll.py` | Pure computation engine | SSS bracket lookup, PhilHealth calculation, Pag-IBIG tiered rates, BIR TRAIN Law progressive tax. Zero DB calls — takes inputs, returns outputs. |
| `backend/dtr.py` | DTR computation | `compute_dtr_fields()` — calculates late_minutes, undertime_minutes, ot_hours, nsd_hours, gross_hours, status from raw time_in/time_out + schedule. NSD: 10PM–6AM per DOLE Art. 86. OT: only time past scheduled_end (never offsets late). |
| `backend/deadlines.py` | Compliance calendar | Government remittance deadlines. Auto-shifts past weekends and holidays. SSS (10th), PhilHealth (15th), Pag-IBIG (15th), BIR (10th). |
| `app/email_sender.py` | SMTP email | `generate_temp_password()`, `send_temp_password_email()`. Branded HTML template. |

### 4.3 — Supporting Files

| File | Purpose |
|------|---------|
| `app/main.py` | Entry point. Session restore, auth gate, sidebar, page routing, company switcher, topbar injection. |
| `app/auth.py` | All auth logic: login, signup, logout, session store/restore, role definitions, page access matrix, password reset, employee invite. |
| `app/db_helper.py` | `get_db()` (cached service-role client, TTL 45 min), `get_company_id()`, `log_action()` (audit logging). |
| `db/connection.py` | `get_supabase_client()` (anon key, respects RLS), `get_supabase_admin_client()` (service key, bypasses RLS, auto_refresh_token=False). |
| `app/styles.py` | CSS injection system. 10+ themes with `--gxp-*` CSS custom properties. Plus Jakarta Sans + Material Symbols fonts. Pill buttons, pill inputs, card shadows. |
| `app/ui_helpers.py` | Hierarchy badge system (hexagon/star/square/triangle/circle by org depth), avatar-with-badge composition. |

---

## SECTION 5: Authentication & Authorization

### 5.1 — Auth Flow Diagram
Interactive diagram showing the complete flow:

```
[Signup] → [GoTrue create user] → [Create company] → [Create user_company_access (role=admin)] → [Store session] → [Dashboard]
                                                                                                        ↑
[Login] → [GoTrue sign_in_with_password] → [Query user_company_access] → [Get role + company_id] → [Store session] → [Route by role]
                                                                                                        │
[Employee ID Login] → [Resolve EMP-001 → email via service key lookup] → [Same login flow]              │
                                                                                                        │
[F5 Refresh] → [Read ?sid= from URL] → [Lookup in server-side cache] → [Restore session state] ────────┘
                                                                                                        │
[Password Reset] → [GoTrue reset_password_email] → [Email with ?code=TOKEN] → [PKCE exchange] → [Set new password form]
```

### 5.2 — Role Hierarchy
Visual pyramid or stacked bar:

```
┌─────────────────────────────────┐
│           ADMIN                 │  Full access to everything
│      (Blue #1d4ed8)            │  Can manage users, roles, company settings
├─────────────────────────────────┤
│        HR MANAGER               │  Employee management, analytics, reports
│      (Green #15803d)           │  Read-only: Payroll Comparison, Company Setup
├─────────────────────────────────┤
│      PAYROLL OFFICER            │  Payroll run, government reports
│      (Amber #b45309)           │  Read-only: Employees, Analytics, Attendance
├─────────────────────────────────┤
│        SUPERVISOR               │  Team dashboard, team attendance, calendar
│      (Purple #7c3aed)          │  Scoped to reporting tree (recursive)
│                                 │  Read-only: Attendance, Calendar
├─────────────────────────────────┤
│         EMPLOYEE                │  Self-service portal only
│      (Slate #64748b)           │  Own payslips, DTR, leave/OT requests
└─────────────────────────────────┘
```

### 5.3 — Permission Matrix
Render as a styled table with colored cells (green = full access, yellow = read-only, red = no access):

| Page | Admin | HR Manager | Payroll Officer | Supervisor | Employee |
|------|-------|-----------|----------------|-----------|---------|
| Dashboard | ✅ Full | ✅ Full | ✅ Full | ✅ Team Only | ❌ Portal |
| Employees | ✅ Full | ✅ Full | 🟡 Read-Only | ❌ | ❌ |
| Payroll Run | ✅ Full | ❌ | ✅ Full | ❌ | ❌ |
| Payroll Comparison | ✅ Full | 🟡 Read-Only | ✅ Full | ❌ | ❌ |
| Workforce Analytics | ✅ Full | ✅ Full | 🟡 Read-Only | ❌ | ❌ |
| Attendance | ✅ Full | ✅ Full | 🟡 Read-Only | 🟡 Read-Only | ❌ |
| Government Reports | ✅ Full | ✅ Full | ✅ Full | ❌ | ❌ |
| Calendar | ✅ Full | ✅ Full | ✅ Full | 🟡 Read-Only | ❌ |
| Company Setup | ✅ Full | 🟡 Read-Only | ❌ | ❌ | ❌ |
| Preferences | ✅ | ✅ | ✅ | ✅ | ✅ (in portal) |
| Employee Portal | ❌ | ❌ | ❌ | ❌ | ✅ Full |

### 5.4 — Session Management Detail
Code block + explanation:

```python
# Server-side session store — cached for Streamlit process lifetime
@st.cache_resource
def _session_cache() -> dict:
    return {}

# On login:
token = str(uuid.uuid4())
_session_cache()[token] = {
    "user_id", "user_email", "company_id", "user_role",
    "accessible_companies", "company_name", "display_name"
}
st.query_params["sid"] = token  # Survives F5 refresh

# On every page load:
restore_from_query_params()  # Reads ?sid=TOKEN → restores session
```

Key points:
- No JWT stored client-side (browser only sees the session UUID token in the URL)
- Server restart invalidates all sessions (users must re-login)
- Session cache lives in Python process memory (not Redis, not database)
- Multi-company: user can switch companies without re-login via `update_active_company()`

### 5.5 — Multi-Company Access
Diagram showing: one `auth.users` row → multiple `user_company_access` rows → different roles per company.

---

## SECTION 6: Security Architecture

### 6.1 — Data Isolation
- **Primary mechanism:** Every DB query includes `.eq("company_id", company_id)` where `company_id` comes from server-side session state (never from client input).
- **Defense-in-depth:** RLS policies enabled on all tables via `get_user_company_ids()` function. Even if the app has a bug, RLS prevents cross-tenant reads at the PostgreSQL level.
- **Service role key:** Used by the app because the 5-role permission model is more complex than RLS can express. Service key is only in `.env` on the server — never sent to the browser.

### 6.2 — Password Handling
- Supabase GoTrue handles all password hashing (bcrypt).
- App never sees plaintext passwords after the auth API call.
- Employee invite flow: system generates random temp password, sends via SMTP email. If SMTP fails, temp password is shown to the admin for manual sharing.
- Password change: re-authenticates with current password before allowing update.

### 6.3 — Session Security
- Session token is a random UUID (not a JWT, not predictable).
- Token is stored in URL query params (`?sid=TOKEN`) — survives page refresh but not shared across browser tabs (each tab gets its own Streamlit session).
- Server-side cache invalidation on logout.
- No cookies used for session management.

### 6.4 — Audit Logging
```python
def log_action(action, entity_type, entity_id, entity_label, details):
    # Writes to audit_logs table
    # Captures: company_id, user_id, user_email, action, entity_type,
    #           entity_id, entity_label, details (JSONB with before/after diffs)
    # Never raises — logging must not break main operations
```
Tracked actions: employee CRUD (with full field diff), payroll finalization, leave/OT approvals, user role changes, company settings changes.

### 6.5 — Input Handling
- Streamlit's built-in XSS protection for standard widgets (`st.text_input`, `st.selectbox`, etc.).
- `unsafe_allow_html=True` used in `st.markdown()` for custom card layouts — content is server-generated, not user-input.
- `components.html()` used for JS injection (sidebar, topbar, maps, org chart) — runs in sandboxed iframe.

### 6.6 — Secrets Management
```
.env file contains:
├── SUPABASE_URL          # Project URL (public)
├── SUPABASE_KEY          # Anon key (public, used for auth API)
├── SUPABASE_SERVICE_KEY  # Service role key (SECRET — bypasses RLS)
├── APP_URL               # Public URL for email links
├── SMTP_HOST             # Email server
├── SMTP_USER             # Email username
├── SMTP_PASSWORD         # Email password (SECRET)
└── SMTP_FROM             # Sender address
```

⚠️ **Known Consideration:** The service role key is the most sensitive credential. If leaked, an attacker can read/write ALL data across ALL tenants. Mitigation: server-side only, `.env` file not committed to git, environment variables in production.

---

## SECTION 7: Government Compliance Engine

### 7.1 — Philippine Statutory Deductions
Interactive tabs — one per agency:

**SSS (Social Security System):**
- Bracket-based lookup table with 44 monthly salary credit (MSC) brackets from ₱5,000 to ₱35,000.
- Employee share: 5% of MSC. Employer share: 10% of MSC. Total: 15%.
- EC (Employment Compensation): ₱10 if MSC ≤ ₱15,000, ₱30 if MSC > ₱15,000.
- Rate table stored in `government_rates` with `agency='SSS'` and `effective_date` versioning.

**PhilHealth:**
- Premium: 5% of basic salary (2.5% EE + 2.5% ER).
- Floor: ₱10,000 monthly salary (minimum premium ₱500).
- Ceiling: ₱100,000 monthly salary (maximum premium ₱5,000).
- Rate stored as percentage in `government_rates`.

**Pag-IBIG (HDMF):**
- Employee: 1% if basic ≤ ₱1,500, 2% if > ₱1,500 (max contribution ₱200).
- Employer: always 2% (max ₱200).
- Rate stored as tiered JSONB in `government_rates`.

**BIR Withholding Tax (TRAIN Law):**
- 6-bracket progressive table (annual, prorated to pay frequency):
  - ₱0–₱250,000: 0%
  - ₱250,001–₱400,000: 15% of excess
  - ₱400,001–₱800,000: ₱22,500 + 20% of excess
  - ₱800,001–₱2,000,000: ₱102,500 + 25% of excess
  - ₱2,000,001–₱8,000,000: ₱402,500 + 30% of excess
  - Over ₱8,000,000: ₱2,202,500 + 35% of excess
- Taxable income = Gross − SSS_EE − PhilHealth_EE − PagIBIG_EE.
- Non-taxable allowances and de minimis benefits excluded.

### 7.2 — Rate Table Versioning
- `government_rates` table has `effective_date` column.
- Payroll engine queries rates WHERE `effective_date <= pay_period.period_end` ORDER BY `effective_date DESC` LIMIT 1.
- New rates can be loaded via new seed scripts without breaking historical payroll.

### 7.3 — Government Reports
List each report with its format, data source, and filing deadline:

| Report | Agency | Format | Frequency | Deadline | Data Source |
|--------|--------|--------|-----------|----------|-------------|
| SSS R3 | SSS | PDF | Monthly | 10th of following month | payroll_entries (sss_employee, sss_employer) |
| PhilHealth RF-1 | PhilHealth | PDF | Monthly | 15th of following month | payroll_entries (philhealth_employee, philhealth_employer) |
| Pag-IBIG MCRF | HDMF | PDF | Monthly | 15th of following month | payroll_entries (pagibig_employee, pagibig_employer) |
| BIR 1601-C | BIR | PDF | Monthly | 10th of following month | payroll_entries (withholding_tax) |
| BIR 2316 | BIR | PDF per employee | Annual | Jan 31 | YTD payroll_entries aggregation |
| BIR 1604-C | BIR | PDF | Annual | Jan 31 | All employees' annual tax data |
| DOLE 13th Month | DOLE | PDF | Annual | Jan 31 | thirteenth_month_accrual per employee |

### 7.4 — 13th Month Pay
- Mandated by PD 851: all rank-and-file employees who worked at least 1 month.
- Computation: 1/12 of total basic salary earned during the calendar year.
- Pro-rated for employees who didn't work the full year.
- Exempt from tax up to ₱90,000 (TRAIN Law de minimis).

---

## SECTION 8: Deployment Guide

### 8.1 — Prerequisites
```
Python 3.12+
pip (or uv for faster installs)
Supabase account (free tier works for dev)
PostgreSQL 17 (managed by Supabase)
SMTP server (optional — for employee portal invites)
```

### 8.2 — Environment Setup
```bash
# Clone the repository
git clone <repo-url>
cd genxcript-saas

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your Supabase credentials:
# SUPABASE_URL=https://xxxxx.supabase.co
# SUPABASE_KEY=eyJhbGci...        (anon key)
# SUPABASE_SERVICE_KEY=eyJhbGci... (service role key)
# APP_URL=http://localhost:8501     (for email links)
```

### 8.3 — Database Migration
```bash
# Run migrations in order in Supabase SQL Editor:
# 001_schema.sql
# 002_seed_government_rates.sql
# 003_dev_setup.sql (optional — dev seed data)
# 004_holidays.sql
# ... through 028_user_roles.sql

# Migrations are numbered sequentially and must be run in order.
# Each migration is idempotent (uses IF NOT EXISTS where possible).
```

### 8.4 — Running Locally
```bash
streamlit run app/main.py

# App opens at http://localhost:8501
# First user: register → creates company → auto-assigned admin role
```

### 8.5 — HTTPS for Portal GPS
```bash
# Browser Geolocation API requires HTTPS (except localhost).
# For remote access / mobile clock-in, use a tunnel:

# Option 1: ngrok
ngrok http 8501 --domain your-domain.ngrok-free.dev

# Option 2: Cloudflare Tunnel
cloudflared tunnel run --url http://localhost:8501
```

### 8.6 — Production Considerations
- **HTTPS:** Required for GPS geolocation in employee portal. Use ngrok, Cloudflare Tunnel, or a reverse proxy (nginx/Caddy).
- **Scaling:** Streamlit is single-process. For > 50 concurrent users, consider running multiple instances behind a load balancer with sticky sessions.
- **Backups:** Supabase provides daily automatic backups on paid plans. For free tier, export via `pg_dump`.
- **Monitoring:** Check Supabase dashboard for DB size, API usage, and auth events.

---

## SECTION 9: Caching & Performance

### 9.1 — Three-Layer Caching Model
Visual diagram (3 stacked colored panels):

**Layer 1: `@st.cache_resource` (App-Level)**
- Scope: shared across ALL users and reruns
- Lifetime: Streamlit process lifetime OR explicit TTL
- Use cases:
  - `get_db()` — Supabase admin client (TTL=2700s / 45 min to prevent stale JWT)
  - `_session_cache()` — server-side session store (permanent)
  - Hierarchy data (computed once per company per session)
- Invalidation: `get_db.clear()` on JWT errors; server restart clears everything

**Layer 2: `@st.cache_data` (Data Cache)**
- Scope: per-function, keyed by arguments (including `_cid=company_id`)
- Lifetime: TTL-based (typically 60–300 seconds)
- Use cases:
  - Employee lists, payroll history, government rates
  - Dashboard stats, calendar events
  - ~35 cached functions across all pages
- Invalidation: TTL expiry; `function_name.clear()` after mutations
- Pattern: `_cid` parameter (company_id) as cache key to prevent cross-tenant cache hits

**Layer 3: `st.session_state` (Per-User)**
- Scope: single user session
- Lifetime: until logout or server restart
- Use cases:
  - Current selections (active page, selected employee, date range)
  - Dialog state (open/closed, form inputs)
  - Company context (company_id, role, accessible companies)
  - Display preferences (theme, date format)
- Invalidation: explicit `st.session_state.pop()` or page navigation

### 9.2 — Streamlit Rerun Model
Explain the critical concept:
```
Every user interaction (button click, dropdown change, form submit)
triggers a FULL re-execution of main.py from top to bottom.

This means:
1. All imports re-execute (but Python caches modules)
2. All DB queries re-execute (unless cached with @st.cache_data)
3. All UI rendering re-executes (Streamlit diffs the output)
4. Session state persists across reruns (it's the only state)

Consequence: Without caching, a page with 5 DB queries would
make 5 DB calls on EVERY button click. The caching system
makes this viable for production.
```

### 9.3 — Frontend Performance Techniques
- **`components.html()` for JS-heavy features:** Org chart (d3), maps (Leaflet), geolocation — run in sandboxed iframes, bypass Streamlit's rerun model.
- **CSS-only animations:** Counting numbers, skeleton shimmer, card entrance animations — no JS reruns needed.
- **`on_click` callback pattern:** Buttons use `on_click=lambda: ...` to set session state BEFORE the rerun, preventing stale data flash in dialogs.
- **Batch queries:** Dashboard loads all KPI data in 2–3 bulk queries instead of N+1 per-employee queries.

---

## SECTION 10: Integration Points & API Surface

### 10.1 — Current Integrations
Cards for each integration:

| Integration | Protocol | Purpose | Configuration |
|------------|----------|---------|---------------|
| Supabase PostgREST | HTTPS REST | All CRUD operations. Auto-generated from PostgreSQL schema. Python SDK wraps REST calls. | `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` |
| Supabase GoTrue | HTTPS REST | Authentication: signup, login, password reset, user management. JWT issuance. | `SUPABASE_URL` + `SUPABASE_KEY` (anon for auth) |
| Supabase Storage | HTTPS REST | File uploads: employee photos (200px JPEG), DTR snapshots (640px JPEG). Bucket-based access control. | Same credentials. Buckets: `employee-photos`, `dtr-snapshots` |
| SMTP Email | SMTP/TLS | Employee portal invite emails with temp password. Password reset emails (via GoTrue). | `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` |
| Browser Geolocation API | JavaScript | Portal clock-in GPS capture. Haversine distance calculation. EXIF GPS fallback from camera photos. | Requires HTTPS. Company locations defined in `company_locations` table. |
| ngrok / Cloudflare Tunnel | HTTPS Tunnel | Expose local Streamlit to internet with HTTPS (required for mobile GPS). | ngrok static domain or Cloudflare tunnel config. |

### 10.2 — Future Integration Opportunities
Styled as "coming soon" cards with dimmed appearance:

- **Accounting Software:** QuickBooks, Xero — export journal entries for payroll expenses.
- **Banking APIs:** BDO, BPI, Metrobank — automated salary disbursement files (CSV/DAT).
- **Biometric Devices:** ZKTeco, Suprema — import DTR punch logs via USB/API.
- **Mobile App:** React Native or Flutter — employee self-service + clock-in.
- **Webhook Notifications:** Slack, Teams, email — payroll approval, leave request alerts.
- **Government e-Filing:** BIR eFPS, SSS online, PhilHealth online — direct submission.

---

## SECTION 11: Development Workflow

### 11.1 — Project Structure
```
genxcript-saas/
├── app/
│   ├── main.py                 # Entry point — auth gate, routing, sidebar
│   ├── auth.py                 # Authentication, roles, session management
│   ├── db_helper.py            # Cached DB client, audit logging
│   ├── styles.py               # CSS injection, themes, design system
│   ├── ui_helpers.py           # Hierarchy badges, avatar composition
│   ├── email_sender.py         # SMTP email for invites
│   ├── pages/
│   │   ├── _dashboard.py       # Admin/supervisor dashboard
│   │   ├── _employees.py       # Employee directory + CRUD
│   │   ├── _payroll_run.py     # Payroll computation + approval
│   │   ├── _payroll_comparison.py  # Period comparison
│   │   ├── _ot_heatmap.py      # Workforce analytics
│   │   ├── _dtr.py             # Attendance / time logs
│   │   ├── _government_reports.py  # Statutory reports + PDF
│   │   ├── _calendar_view.py   # Calendar with deadlines
│   │   ├── _company_setup.py   # Company configuration
│   │   ├── _preferences.py     # User preferences
│   │   ├── _employee_portal.py # Employee self-service
│   │   ├── _login.py           # Login page
│   │   └── _register.py        # Signup page
│   ├── components/             # Custom Streamlit components
│   │   ├── geolocation.py      # Browser GPS capture
│   │   └── hash_auth.py        # URL hash reader for auth flows
│   ├── reports/                # PDF generation
│   │   └── dole_13th_month_pdf.py
│   └── static/                 # Static assets (logos, fonts)
├── backend/
│   ├── payroll.py              # Pure payroll computation engine
│   ├── dtr.py                  # DTR computation engine
│   └── deadlines.py            # Government remittance deadlines
├── db/
│   ├── connection.py           # Supabase client factory
│   ├── 001_schema.sql          # Core schema + RLS
│   ├── 002_seed_government_rates.sql
│   ├── ... (28 migration files)
│   └── seed_*.sql              # Test data seeds
├── scripts/
│   └── archive_snapshots.py    # DTR snapshot archival
├── .env                        # Environment variables (not committed)
├── requirements.txt            # Python dependencies
├── ROADMAP.md                  # Development roadmap
└── .streamlit/
    └── config.toml             # Streamlit configuration
```

### 11.2 — Adding a New Page Module
```python
# 1. Create app/pages/_my_new_page.py
def render():
    """Entry point. Called by main.py when user navigates here."""
    from app.db_helper import get_db, get_company_id
    from app.styles import inject_css
    inject_css()

    db = get_db()
    company_id = get_company_id()

    st.title("My New Page")
    # ... page logic ...

# 2. Add to PAGE_ACCESS in app/auth.py
PAGE_ACCESS = {
    ...
    "My New Page": [ROLE_ADMIN, ROLE_HR_MANAGER],
}

# 3. Add routing in app/main.py (in the page dispatch section)
elif selected == "My New Page":
    from app.pages._my_new_page import render
    render()

# 4. Add to sidebar navigation (icon + label)
```

### 11.3 — Adding a Database Table
```bash
# 1. Create db/029_my_table.sql
# 2. Include CREATE TABLE with company_id FK, RLS policies
# 3. Run in Supabase SQL Editor
# 4. Add to the migration index in documentation
```

### 11.4 — Code Conventions
- **File naming:** Page modules prefixed with `_` (e.g., `_dashboard.py`) — prevents Streamlit multi-page auto-discovery.
- **CSS-in-Python:** All styles in `styles.py` using CSS custom properties (`--gxp-*`). No external CSS files.
- **Money:** Always integer centavos. Display with `₱{amount/100:,.2f}`.
- **Imports:** Lazy imports inside functions for pages (reduces startup time).
- **Caching:** Every DB query function gets `@st.cache_data` with `_cid` parameter. Clear cache after mutations.

---

## SECTION 12: Roadmap & Technical Debt

### 12.1 — Completed Phases
Render as a vertical timeline with green checkmarks:

- ✅ **Phase UI** — Material 3 Design System (Tactile Sanctuary). 10+ themes, custom sidebar, topbar, card grids, Spotfire-style analytics, Leaflet maps, d3 org charts.
- ✅ **Phase 1: MVP** — Multi-tenant payroll engine, employee CRUD, government reports, audit trail, company management.
- ✅ **Phase 2: Enhancements** — Employee self-service portal, payroll comparison, calendar, analytics, custom sidebar, leave entitlements.
- ✅ **Phase 3A: Holidays** — Full PH holiday calendar with observed dates, DOLE rate reference.
- ✅ **Phase 3B: Extended Employee Info** — Education, addresses, contact details, regularization/separation dates.
- ✅ **Phase 3C: Leave Foundation** — Leave types (VL/SL/CL), request/approval workflow, entitlement templates, balance tracking.
- ✅ **Phase 3E: Roles** — 5-role model (admin, hr_manager, payroll_officer, supervisor, employee) with full RBAC.
- ✅ **Phase 4A: Scheduling** — Shift profiles, per-employee assignment, overnight support.
- ✅ **Phase 4B: DTR** — Time logs with GPS + snapshots, NSD computation, DTR corrections, geofencing.
- ✅ **Phase 5C: Flexible Transactions (partial)** — NSD auto-fill, OT from approved requests, absent deduction, daily rate divisor.

### 12.2 — In Progress
Render with amber indicators:

- 🟡 **Supervisor Dashboard v2** — ADP-style manager tool with DTR exceptions, holiday pay validator, OT authorization.
- 🟡 **Company Policy Wizard** — "Mind Joggler" interactive questionnaire for new client onboarding.

### 12.3 — Upcoming Phases
Render with gray indicators:

- ⬜ **Phase 5A: Loans Module** — SSS/Pag-IBIG/company salary loans with amortization.
- ⬜ **Phase 5B: Special Payroll** — 13th month pay run, backpay/separation pay, bonus runs.
- ⬜ **Phase 5D: Bank Disbursement** — BDO/BPI/Metrobank/UnionBank file generation.
- ⬜ **Phase 6: Portal Expansion** — DTR viewing, notifications, attendance certification PDF.
- ⬜ **Phase 6B: HR Compliance** — Disciplinary actions (DOLE two-notice rule), HMO, probation tracker.
- ⬜ **Phase 7: Business Intelligence** — Budget vs actual, burn rate, turnover analytics, ghost employee detection.
- ⬜ **Phase 8: Demo Simulator** — Day-by-day HR playback script for demos and testing.
- ⬜ **Phase 9: Security Hardening** — Penetration testing, OWASP compliance.

### 12.4 — Known Technical Debt
Render as a styled list with severity tags:

- 🔴 **No automated tests.** The payroll engine (`backend/payroll.py`) is pure Python with no DB calls — ideal for unit testing but no tests exist yet.
- 🟡 **Session store is in-memory.** Server restart logs out all users. No Redis/DB-backed session store. Acceptable for single-instance deployment.
- 🟡 **No API layer.** All data access goes through the Supabase Python SDK. No REST/GraphQL API for third-party integrations. Would need to be built for mobile app or external integrations.
- 🟡 **RLS bypassed by design.** Service role key bypasses RLS; tenant isolation is manual. A code bug could leak cross-tenant data. Mitigated by: code review + RLS as defense-in-depth.
- 🟡 **No rate limiting.** Login endpoint has no brute-force protection beyond Supabase GoTrue's built-in limits.
- 🟠 **CSS-in-Python is verbose.** `styles.py` is large and mixes concerns. Could benefit from a CSS preprocessor or component library.
- 🟠 **No database migrations runner.** Migrations must be run manually in Supabase SQL Editor. No Alembic/Flyway equivalent.
- 🟠 **Single-process Streamlit.** Cannot handle high concurrency. Horizontal scaling requires sticky sessions.
- 🟢 **Deprecated role mapping.** `viewer` role mapped to `hr_manager` for backward compatibility. Can be removed after all existing users are migrated.

### 12.5 — Future Architecture Considerations
- **API Layer:** FastAPI or Supabase Edge Functions for mobile app and third-party integrations.
- **Microservices:** Payroll engine, notification service, and report generator could be extracted as independent services if scaling demands it.
- **Mobile App:** React Native or Flutter for employee self-service (clock-in, payslips, leave requests).
- **Real-time:** Supabase Realtime for live dashboard updates and notification delivery.
- **CI/CD:** GitHub Actions for automated testing, migration validation, and deployment.

---

## INTERACTIVE FEATURES (JS)

### Collapsible Sections
Every section and subsection has a clickable header. Clicking toggles the content visibility with a smooth slide animation. A chevron (▶/▼) rotates to indicate state. All sections start expanded.

### Tabbed Content
Within sections (e.g., Government Compliance → SSS / PhilHealth / PagIBIG / BIR tabs), implement horizontal pill-shaped tabs. Active tab has var(--primary) background. Content swaps on click without page reload.

### Copy-to-Clipboard
All code blocks have a "Copy" button (absolute positioned top-right). On click, copies text content to clipboard and shows brief "Copied!" tooltip.

### Search
Top search bar filters sections by keyword. Non-matching sections are hidden (display:none). Matching text is wrapped in `<mark>` with yellow background on dark theme (background: #f59e0b33, color: var(--warning)).

### Scroll Spy
Sidebar navigation highlights the current section based on scroll position. Use Intersection Observer API.

### Print Styles
```css
@media print {
  body { background: white; color: black; }
  .sidebar { display: none; }
  .search-bar { display: none; }
  .collapsible-content { display: block !important; max-height: none !important; }
  code { background: #f3f4f6; color: #1a1a1a; }
  a { color: black; text-decoration: underline; }
  .no-print { display: none; }
  h2 { page-break-before: always; }
  .card { break-inside: avoid; border: 1px solid #ccc; }
}
```

---

## TONE & STYLE GUIDE

- **Technical, precise, no marketing fluff.** This is for people who will maintain, extend, or integrate with this system.
- **Assumes familiarity** with web development, databases, PostgreSQL, REST APIs, and cloud services.
- **Includes "why" alongside "what."** Every design decision has a rationale. Every tradeoff is acknowledged.
- **Honest about limitations.** Technical debt is listed openly. Security considerations are frank.
- **Code examples are real** — taken from actual codebase, not pseudo-code.
- **Philippine context** — government agencies (SSS, PhilHealth, Pag-IBIG, BIR) are explained with their full names and regulatory references (DOLE Art. 86, PD 851, TRAIN Law).

---

## FOOTER

Include at the bottom:
- "GeNXcript Payroll — Technical Documentation v1.0"
- "Generated for IT team onboarding and architecture review"
- "Last updated: March 2026"
- "Built with Streamlit + Supabase + Python"
