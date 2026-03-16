# GenXcript Payroll — Product Roadmap

> Last updated: 2026-03-17
> Strategy: Payroll-first → HR Compliance → Attendance → Advanced Payroll → Portal → BI → Scale
> Each phase unlocks the next. Features within a phase are ordered by dependency.

---

## Phase 1: MVP ✅ Complete
> **What we built:** A fully functional Philippine-compliant payroll engine from scratch — multi-tenant, cloud-hosted, and ready to process real employee payroll from day one.

- [x] **Database schema + government rates seed** — Multi-tenant Supabase schema with 2025 SSS, PhilHealth, Pag-IBIG, and BIR TRAIN Law rates pre-loaded; all monetary values stored as centavos for precision
- [x] **Core payroll computation engine** — Pure Python engine computing SSS (5%/10%), PhilHealth (2.5% each), Pag-IBIG (tiered 1–2%), and withholding tax via 6-bracket TRAIN Law; zero DB calls for testability
- [x] **Employee Master File** — Full CRUD with position, department, salary, employment type, and tax status; position/department stored as company-scoped dropdowns with live "Add new" flow
- [x] **Payroll Run** — Create pay periods, enter per-employee earnings (basic, OT, allowances, holiday pay), auto-compute all contributions and tax, review breakdown, and finalize
- [x] **Payslip Generation** — Professional PDF payslip export per employee with full earnings and deduction breakdown
- [x] **Dashboard** — KPI metrics (headcount, total gross, total deductions, net payroll), remittance deadlines, government contribution summaries, and payroll trend charts
- [x] **Company Setup** — Company profile, government employer numbers, pay frequency configuration
- [x] **Government Report Generation** — SSS R3, PhilHealth RF-1, Pag-IBIG MCRF, BIR 1601-C monthly remittance forms; BIR 2316 annual certificate per employee; BIR 1604-C annual alphalist (due Jan 31)
- [x] **Auth / Multi-tenant login** — Supabase Auth with company-scoped RLS; employee login via Employee ID or email; case-insensitive lookup with distinct error messages for "not found" vs "no portal access"
- [x] **Multi-company management** — Admin can register and switch between multiple companies; all data is strictly scoped per company
- [x] **Audit trail** — Activity log records every action (who, what, when); employee updates log full before/after field diffs (old value in red, new value in green) with full-text search

---

## Phase 2: Enhancements ✅ Mostly Complete
> **What we built:** Transformed the raw payroll engine into a product — adding self-service, approvals, visibility, and a polished UI that doesn't feel like internal tooling.

- [x] **Employee onboarding checklist** — Tracks whether each employee's SSS, PhilHealth, Pag-IBIG, and TIN numbers are on file; flags incomplete profiles before payroll runs
- [x] **Payroll approval workflow** — Two-step flow: HR submits for review → Admin approves and finalizes; prevents accidental premature payroll release; reviewer and timestamp recorded
- [x] **Payroll comparison** — Period-over-period analysis; immediately surfaces new hires, salary adjustments, and OT spikes so employers can catch anomalies before finalizing
- [x] **Calendar view** — Visual month grid showing pay period spans, payment dates, government remittance deadlines, and Philippine holidays side-by-side; deadlines auto-shift to next business day when they fall on weekends or holidays
- [x] **Employee self-service portal** — Employees log in with their Employee ID or email, view their own payslips, download their BIR 2316 and COE, and update personal profile information
- [x] **Philippine holiday calendar** — 2025–2026 national holidays pre-seeded (regular + special non-working + special working); used by deadline engine and calendar view
- [x] **Dashboard charts** — Payroll cost trend (line), deductions breakdown (pie), headcount over time (bar); draggable/resizable card layout with show/hide controls per card
- [x] **UI/UX design pass** — Shared CSS styles module with full inject_css() coverage across all pages; financial data styled with consistent typography; colored status badges; remittance agency cards with progress indicators; uniform h1 sizing via native st.title() on all pages
- [x] **Leave Entitlement Templates** — Named leave tiers (e.g., "0–1 Year", "Regular Staff") with configurable VL/SL/CL days; assignable per employee; defaults to 15/15/5 if unassigned
- [x] **OT Heat Maps** — Visualize which days and cost centers drive overtime spikes; baseline for Phase 7 BI analytics
- [ ] **PWA cache** — Offline-capable for areas with unstable internet *(low priority, skip for now)*

---

## Phase 3: Core HR Completion
> Prerequisite for Phases 4 and 5. These unlock correct OT multipliers, attendance deductions, and statutory leave compliance.

### 3A — Holidays Management ✅ Complete
- [x] Holiday type definitions — regular, special non-working, special working *(done in migration 004)*
- [x] Annual holiday calendar — 2025–2026 PH proclamation holidays pre-seeded *(done in migration 004)*
- [x] Calendar view integration — holidays shown with colored cell backgrounds alongside pay periods *(done in calendar_view.py)*
- [x] Remittance deadline adjustment — deadlines auto-shift past weekends and holidays *(done in backend/deadlines.py)*
- [x] **Holiday Management UI** — Company Setup "Holidays" tab: national holidays read-only list with type badges, company-specific custom holiday CRUD *(migration 009)*
- [x] **Holiday pay multiplier reference** — DOLE-mandated rate table (Regular 200%/260% OT, Special NW 130%/169% OT, rest day combos) in Company Setup as expandable reference for HR staff

### 3B — Employee Extended Information ✅ Complete
- [x] Regularization date, resignation date fields *(migration 010)*
- [ ] Birthday leave trigger *(deferred — low priority, company-specific)*
- [x] Classification / profession type *(migration 010)*
- [x] Educational background (degree, school, year graduated) *(migration 010)*
- [x] Additional contact info (personal email, home/mobile/work phone, Facebook, LinkedIn) *(migration 010)*
- [x] Permanent vs current address distinction *(done in Phase 2 employee portal)*

### 3C — Leave Foundation ✅ Mostly Complete
- [x] Leave types (VL, SL, CL) with request flow *(migration 007)*
- [x] Leave profiles — named entitlement templates with year-end policy: carry-over cap, cash convertible flag, conversion rate *(migrations 008, 011)*
- [x] Leave credits & running balance per employee — computed from approved requests; `leave_balance` table stores carry-over opening balances *(migration 011)*
- [ ] Leave deductions in payroll — unpaid absences auto-deduct from gross pay *(deferred: requires Phase 4B DTR first)*
- [x] Leave summary report — admin "📊 Leave Balances" tab: all employees, VL/SL/CL used/remaining with progress bars, year selector, dept filter *(employees.py)*

---

## Phase 4: Attendance & Time
> Depends on Phase 3C (leave rules) and 3A (holidays). Without schedule templates, DTR has no basis for computing late/undertime.

### 4A — Scheduling ✅ Mostly Complete
- [x] Shift schedule profiles — name, start/end time, break duration, working days, overnight flag *(migration 012, Company Setup → Schedules tab)*
- [x] Per-employee schedule assignment — dropdown in employee form; `employees.schedule_id` FK *(migration 012)*
- [x] Single-day schedule override table — `schedule_overrides` with rest-day flag and reason *(migration 012, UI deferred to Phase 4B DTR page)*
- [ ] Compensatory Time-off (CTO) — OT hours converted to leave credits *(deferred: needs DTR computation first)*

### 4B — DTR / Time Logs *(depends on 4A for late/undertime thresholds)*
- [ ] Manual time log entry (daily punch-in / punch-out per employee)
- [ ] Daily Time Record (DTR) view — formatted timesheet per employee per period
- [ ] Late, undertime, and absent computation against scheduled shift
- [ ] DTR correction requests (employee submits → supervisor approves)
- [ ] BTR correction request history

### 4C — OT & Leave Request Workflows *(partially done; depends on 4B for full DTR-backed computation)*
- [x] Overtime request form — employee portal submits OT request with date/time/hours *(employee_portal.py)*
- [x] Leave request form — employee portal submits leave with balance check warning *(employee_portal.py)*
- [x] Admin approval — single-level approve/reject with notes; Leave & OT Approvals tab *(employees.py)*
- [x] Request history list — employee sees own requests + statuses *(employee_portal.py)*
- [ ] 2-level approval (Supervisor → HR/Admin) *(deferred: requires schedule/reporting structure)*
- [ ] Auto-email notifications to supervisor on submission *(deferred: needs 2-level approval first)*

---

## Phase 5: Advanced Payroll
> Depends on Phase 4 (attendance affects deductions). These are additive payroll computation features.

### 5A — Loans Module *(common deduction type not yet tracked)*
- [ ] Loan types (SSS Salary Loan, Pag-IBIG MP2, Company Salary Loan)
- [ ] Loan records per employee (principal, interest, term, start date)
- [ ] Amortization schedule auto-computation
- [ ] Auto-deduction in payroll run per period

### 5B — Special Payroll Runs
- [ ] 13th Month Pay computation (dedicated run type — Jan 31 deadline)
- [ ] Mid-year bonus / performance bonus runs (custom multiplier)

### 5C — Flexible Transactions
- [ ] Payroll adjustments (ad-hoc corrections within a pay run)
- [ ] Custom transaction types (define your own earning/deduction codes)
- [ ] Custom transaction entries per employee per period
- [ ] Payroll rate profiles (per-group rate sets — e.g. Rank & File vs Managerial)
- [ ] Payroll code profiles (earning/deduction code dictionary)

### 5D — Piece Work / Output-Based Pay
- [ ] Piece rate definitions (rate per unit)
- [ ] Piece rate multipliers (holiday, OT, night diff factors on piece work)
- [ ] Per-employee piece work entries per period

### 5E — Bank Disbursement
- [ ] Bank account per employee (bank name, account number, account type)
- [ ] Bank file generation (BDO, BPI, Metrobank formats) at end of payroll run
- [ ] Salary disbursement record (mark as disbursed, disbursement date)

---

## Phase 6: Employee Portal Expansion
> Connects all Phase 3–5 features to the self-service portal. Employees become active users, not just recipients.

- [x] **Preferences tab** — Personalise appearance, date formats, display settings, and notifications from within the employee portal (embedded as 5th tab alongside Profile / Payslips / Time & Leave / Documents)
- [ ] View daily time record (DTR) per period
- [ ] View full time log history
- [ ] Submit leave request (with leave balance shown)
- [ ] View leave request history + statuses
- [ ] Submit overtime request
- [ ] View overtime request history + statuses
- [ ] Submit DTR correction request
- [ ] View DTR correction history + statuses
- [ ] View/acknowledge assigned schedule
- [ ] View leave summary report (credits, used, remaining per type)
- [ ] View loan balance and amortization schedule
- [ ] Change password

---

## Phase 7: Business Intelligence *(ADP-Style Fiscal Control)*
> Source: ADP "Fiscal Control Center" framework adapted for PH SMEs. Research: 2026-03-15.

### 7A — After 10 Paying Customers
- [x] OT Heat Maps — visualize which days/managers drive overtime spikes
- [ ] Budget vs Actual Variance — upload annual labor budget, show red/green vs actual spend
- [ ] Owner's Digest PDF — scheduled Monday morning 1-page PDF: top 5 fiscal risks from prior week

### 7B — After 50 Paying Customers (Premium Tier)
- [ ] Real-Time Burn Rate — Basic Pay + OT + Night Diff + Employer Statutories aggregated live
- [ ] Cost Center Tagging — tag every peso to department/project; Sales vs Direct comparison
- [ ] Geographic Cost Comparison — multi-site SMEs (NCR HQ vs Laguna factory) cost efficiency
- [ ] Turnover Cost Analytics — fiscal impact of exits: retraining cost + productivity loss
- [ ] Absenteeism Productivity Loss — quantify unplanned leave cost to bottom line
- [ ] Ghost Employee & Fraud Detection — AI audit: flag duplicate clock-ins from same IP/device
- [ ] Headcount Velocity — hiring speed vs exits; ensures recruitment keeps pace with growth
- [ ] Attendance analytics integration (links Phase 4 data to BI layer)

---

## Phase 8: Scale
> Only after product-market fit is confirmed. These are infra and platform decisions, not features.

- [ ] React frontend (replace Streamlit for production-grade UX)
- [ ] Electron desktop app (if clients demand offline-first)
- [ ] Mobile app (React Native or Flutter) — employee portal goes mobile
- [ ] API layer (REST/GraphQL) — enables 3rd-party integrations (payroll banks, HRIS)
- [ ] White-label support — resellers can rebrand for their own clients
- [ ] Record retention module (5–7 year archival per DOLE and BIR requirements)

---

## Feature Dependency Map

```
Phase 1 (Payroll Core)
  └── Phase 2 (UX + Visibility)
        └── Phase 3 (Core HR)
              ├── 3A Holidays ──────────────── → Phase 5 (OT multipliers)
              ├── 3B Employee Info ──────────── → standalone, no deps
              └── 3C Leave Foundation ──────── → Phase 4C (Leave requests)
                    └── Phase 4 (Attendance)
                          ├── 4A Scheduling ── → 4B DTR
                          ├── 4B DTR ──────── → 4C Workflows + Phase 5
                          └── 4C Workflows ── → Phase 6 Portal
                                └── Phase 5 (Advanced Payroll)
                                      └── Phase 6 (Portal Expansion)
                                            └── Phase 7 (BI)
                                                  └── Phase 8 (Scale)
```
