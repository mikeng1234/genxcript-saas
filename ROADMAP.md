# GenXcript Payroll — Product Roadmap

> Last updated: 2026-03-16
> Strategy: Payroll-first → HR Compliance → Attendance → Advanced Payroll → Portal → BI → Scale
> Each phase unlocks the next. Features within a phase are ordered by dependency.

---

## Phase 1: MVP ✅ Complete

- [x] Database schema + government rates seed
- [x] Core payroll computation engine (SSS, PhilHealth, Pag-IBIG, BIR withholding tax)
- [x] Employee Master File (CRUD, positions, departments)
- [x] Payroll Run (earnings input, auto-compute, finalize)
- [x] Payslip Generation (PDF export)
- [x] Dashboard (KPIs, remittance summary, deadlines)
- [x] Company Setup
- [x] Government Report Generation (SSS R3, PhilHealth RF-1, Pag-IBIG MCRF, BIR 1601-C)
- [x] Auth / Multi-tenant Login (Supabase Auth + Employee ID login)
- [x] Multi-company management (admin switches between companies)
- [x] Audit trail (activity log — who changed what and when, before/after diffs)
- [x] BIR Form 2316 (annual certificate per employee)
- [x] BIR Form 1604-C (annual alphalist, due Jan 31)

---

## Phase 2: Enhancements ✅ Mostly Complete

- [x] Employee onboarding checklist — track if gov IDs are complete
- [x] Payroll approval workflow — "Submit for Review → Approve & Finalize" with reviewer tracking
- [x] Payroll comparison — period-over-period changes (new hires, salary adjustments, OT spikes)
- [x] Calendar view — visual timeline of pay periods, deadlines, and PH holidays
- [x] Employee self-service portal — employees view payslips, COE, BIR 2316 via own login
- [x] Philippine holiday calendar — auto-adjust remittance deadlines to next business day
- [x] Dashboard charts — payroll cost trend, deductions breakdown, headcount over time
- [x] Draggable dashboard layout — reorderable, resizable, hideable cards
- [x] OT Heat Maps — visualize which days/managers drive overtime spikes
- [ ] PWA cache — offline-capable for areas with unstable internet

---

## Phase 3: Core HR Completion
> Prerequisite for Phases 4 and 5. These unlock correct OT multipliers, attendance deductions, and statutory leave compliance.

### 3A — Holidays Management *(small lift, high compliance impact)*
- [ ] Holiday type definitions (Regular, Special Non-Working, Special Working)
- [ ] Annual holiday calendar per company (pre-seeded with PH proclamation holidays)
- [ ] Holiday pay multiplier rules (200% regular, 130% special, 150% OT on holiday)
- [ ] Calendar view integration — holidays shown alongside pay periods

### 3B — Employee Extended Information *(low-hanging fruit, common HR ask)*
- [ ] Regularization date, resignation date fields
- [ ] Birthday (affects birthday leave in some companies)
- [ ] Classification / profession type (Engineer, Lawyer, etc.)
- [ ] Educational background (degree, school, year graduated)
- [ ] Additional contact info (personal email, home/mobile/work phone, Facebook, LinkedIn)
- [ ] Permanent vs current address distinction

### 3C — Leave Foundation *(dependency: leave deductions in payroll need this first)*
- [ ] Leave types (SL, VL, EL, ML, PL, SPL — configurable per company)
- [ ] Leave profiles (rules: accrual rate, carry-over cap, convertible to cash, who qualifies)
- [ ] Leave credits & running balance per employee
- [ ] Leave deductions in payroll (unpaid absences auto-deduct from gross pay)
- [ ] Leave summary report (admin view: all employees, type, used, remaining)

---

## Phase 4: Attendance & Time
> Depends on Phase 3C (leave rules) and 3A (holidays). Without schedule templates, DTR has no basis for computing late/undertime.

### 4A — Scheduling *(prerequisite for DTR computation)*
- [ ] Shift schedule profiles (e.g. "Morning 8am–5pm", "Night 10pm–6am")
- [ ] Per-employee schedule assignment (calendar view, checkbox multi-select)
- [ ] Single-day schedule override (one-off adjustments)
- [ ] Compensatory Time-off (CTO) — earned OT converted to leave balance

### 4B — DTR / Time Logs *(depends on 4A for late/undertime thresholds)*
- [ ] Manual time log entry (daily punch-in / punch-out per employee)
- [ ] Daily Time Record (DTR) view — formatted timesheet per employee per period
- [ ] Late, undertime, and absent computation against scheduled shift
- [ ] DTR correction requests (employee submits → supervisor approves)
- [ ] BTR correction request history

### 4C — OT & Leave Request Workflows *(depends on 4B and 3C)*
- [ ] Overtime request form (employee submits → 2-level approval)
- [ ] Leave request form (employee submits → auto-deducts from leave credits on approval)
- [ ] 2-level approval system (Supervisor → HR/Admin) for all requests
- [ ] Auto-email notifications to supervisor on Leave/OT request submission
  *(infra already exists in `email_sender.py` — just needs workflow wiring)*
- [ ] Request history list (employee sees own requests + statuses)

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
