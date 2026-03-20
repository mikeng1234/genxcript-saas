# GenXcript Payroll — Product Roadmap

> Last updated: 2026-03-21
> Strategy: Payroll-first → HR Compliance → Attendance → Advanced Payroll → Portal → BI → Scale
> Each phase unlocks the next. Features within a phase are ordered by dependency.

---

## Phase UI: Material 3 Design System ("Tactile Sanctuary") 🎨 In Progress
> Upgrading the entire UI to Google Material 3 design language. Reference designs generated via Google Stitch AI and stored in `fromstitch/` (11 HTML files). Prompts stored in `webprompts/` (11 files with shared design system header).
> **Beelink note:** Pull latest, check `fromstitch/` (01_login.html – 11_preferences.html) and `app/static/` (logos). Run `streamlit run app/main.py` to see current state.

- [x] **Phase A — Global CSS Foundation** — `app/styles.py`: "tactile" theme with full Material 3 token set (`--gxp-*` CSS variables); Plus Jakarta Sans + Material Symbols Outlined fonts; pill buttons, pill inputs, pill tabs, ambient card shadows, rounded modals; `DEFAULT_THEME = "tactile"`
- [x] **Phase B — Sidebar Redesign** — Material Symbols Outlined icons replacing MDI; `injectFonts()` loads fonts directly into `window.parent.document.head`; light-theme fallback colors; pill-shaped active/hover nav items; brand section with "Payroll Solutions" subtitle; `[server] enableStaticServing = true` in config.toml
- [x] **Phase C — Login Page** — `GenXcript_Dark.png` logo in `app/static/` replacing plain text; static file serving via Streamlit; ambient shadow on logo
- [x] **Topbar** — Fixed top bar injected via JS: company name (left) + user chip + Preferences + My Account + Sign Out (right); `My Account` and `Sign Out` removed from sidebar footer (still hidden in DOM for `clickNav()` routing); 48px content push-down
- [x] **Bug fixes** — Checkbox highlight (Emotion class whitelist); Edit employee 2-click (render-level redirect); Activate/Deactivate on_click pattern (data refresh without dialog close); Print 201 blob URL + immediate state clear; salary hidden by default with toggle; search bar repositioned
- [x] **Phase D — Dashboard** — M3 bento hero grid: Next Pay Date hero, Active Employees accent card, Payroll Expenditure mini-bar chart, Recent Activity feed, Quick Actions row; existing KPI/alerts/remittance panels retained below
- [x] **Phase E — Employees** — Table replaced with 3-column M3 card grid: initials avatar (8-color palette), department pill, name/position/emp no, salary toggle, employment type badge, SSS/PH/PI/TIN gov ID dots; editorial heading; all action buttons retained
- [ ] **Phase F — Payroll Run** — Stitch ref: `fromstitch/06_payroll_run.html`
- [ ] **Phase G — Attendance** — Stitch ref: `fromstitch/07_attendance.html`
- [ ] **Phase H — Workforce Analytics** — Stitch ref: `fromstitch/08_ot_analytics.html`
- [ ] **Phase I — Government Reports** — Stitch ref: `fromstitch/09_government_reports.html`; fix duplicate heading
- [ ] **Phase J — Calendar** — Stitch ref: `fromstitch/10_calendar.html`
- [ ] **Phase K — Company Setup** — Stitch ref: `fromstitch/11_company_setup.html`

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
- [x] **Remittance Records table** — `remittance_records` (migration 014): tracks actual filed date, reference number, and amount per company × agency × calendar month; UNIQUE constraint prevents duplicate entries; RLS scoped to company members *(UI pending — see Phase 2)*
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
- [x] **Dashboard interactive pills** — Stat card hover pills (collapsed 10px → 26px on hover, accent-colored glow per card); Reminders section above Alerts with pending Leave/OT counts; Leave/OT/Gov Reports pills open dialogs; cross-column hover scope fixed via CSS :not(:has())
- [x] **Dashboard live clock** — JS-powered HH:MM:SS AM/PM + weekday/date widget top-right of dashboard; also added to Calendar page
- [x] **Custom left sidebar** — Replaces horizontal top nav; collapsed=54px (icons) / expanded=214px (icons + labels) / peek on hover; ◀/▶ toggle; localStorage persistence; Streamlit sidebar hidden and JS-routed
- [ ] **Remittance Tracking UI** — Record and view actual government remittance submissions per agency per month; mark as filed with reference number and amount; `remittance_records` table ready (migration 014)
- [x] **Leave Entitlement Templates** — Named leave tiers (e.g., "0–1 Year", "Regular Staff") with configurable VL/SL/CL days; assignable per employee; defaults to 15/15/5 if unassigned
- [x] **Workforce Analytics** (formerly "OT Heatmap") — 4 tabs: OT Analytics (heatmap + top contributors with dept/shift), Late Monitoring (ranked list + 3-month bubble calendar per employee), Undertime (mirrors Late), Break Monitoring (real portal break data + implied fallback + overbreak column)
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
- [x] **Holiday observed date** — `observed_date` column on holidays (migration 019); national holidays shared across all companies (PH proclamations apply to all employers); company-added holidays scoped per company; observed_date override is system-wide (correct: government proclamation moves apply to all)
- [ ] **Per-company holiday override** — allow a company to observe a national holiday on a different date than the proclamation (e.g., internal policy); requires company-specific shadow record instead of editing the shared national row *(deferred)*

### 3B — Employee Extended Information ✅ Complete
- [x] Regularization date, separation date fields *(migration 010; renamed from "Resignation Date" to "Separation Date")*
- [ ] Birthday leave trigger *(deferred — low priority, company-specific)*
- [x] Classification / profession type *(migration 010; removed from visible form — stored but not shown)*
- [x] Educational background (degree, school, year graduated) *(migration 010)*
- [x] Additional contact info (personal email, home/mobile/work phone, Facebook, LinkedIn) *(migration 010)*
- [x] Permanent vs current address distinction *(done in Phase 2 employee portal)*

### 3C — Leave Foundation ✅ Mostly Complete
- [x] Leave types (VL, SL, CL) with request flow *(migration 007)*
- [x] Leave profiles — named entitlement templates with year-end policy: carry-over cap, cash convertible flag, conversion rate *(migrations 008, 011)*
- [x] Leave credits & running balance per employee — computed from approved requests; `leave_balance` table stores carry-over opening balances *(migration 011)*
- [ ] Leave deductions in payroll — unpaid absences auto-deduct from gross pay *(deferred: requires Phase 4B DTR first)*
- [x] Leave summary report — admin "📊 Leave Balances" tab: all employees, VL/SL/CL used/remaining with progress bars, year selector, dept filter *(employees.py)*

### 3D — User Roles & Access Control *(prerequisite for multi-user companies and 2-level approvals)*
- [ ] Role definitions — Admin, HR Manager, Payroll Processor, Supervisor, Employee (read-only portal)
- [ ] Role-based page access — HR Manager cannot touch Company Setup; Payroll Processor cannot modify employee records; Supervisor sees only their team
- [ ] Supervisor assignment — each employee can be assigned a reporting supervisor; used for 2-level approval chain in Phase 4C
- [ ] Role selector in user management UI — Company Setup "Users & Roles" tab
- [ ] RLS policy updates in Supabase to enforce role boundaries at DB level

### 3E — Employee Exit & Offboarding
- [ ] Exit initiation — HR records last working day, reason (resignation / termination / end of contract), and clearance deadline (DOLE 30-day rule)
- [ ] Clearance checklist — per-item (equipment returned, ID surrendered, accounts deactivated, etc.) with checked-by and date fields
- [ ] Final pay computation trigger — links to Phase 5B (pro-rated 13th month + convertible leave cash-out + separation pay if applicable)
- [ ] Portal access auto-deactivation on last working day
- [ ] Exit summary report — HR-printable PDF of final pay breakdown and clearance status

---

## Phase 4: Attendance & Time
> Depends on Phase 3C (leave rules) and 3A (holidays). Without schedule templates, DTR has no basis for computing late/undertime.

### 4A — Scheduling ✅ Mostly Complete
- [x] Shift schedule profiles — name, start/end time, break duration, working days, overnight flag *(migration 012, Company Setup → Schedules tab)*
- [x] Per-employee schedule assignment — dropdown in employee form; `employees.schedule_id` FK *(migration 012)*
- [x] Single-day schedule override table — `schedule_overrides` with rest-day flag and reason *(migration 012, UI deferred to Phase 4B DTR page)*
- [ ] Compensatory Time-off (CTO) — OT hours converted to leave credits *(deferred: needs DTR computation first)*

### 4B — DTR / Time Logs ✅ Complete
- [x] Manual time log entry (daily punch-in / punch-out per employee) — admin per-date view: all employees for one day, inline time_in/time_out inputs with live late/undertime feedback; includes **Shift** column showing schedule name + start–end times *(app/pages/_dtr.py)*
- [x] Daily Time Record (DTR) view — formatted timesheet per employee per period (Attendance Summary tab with day-by-day detail expandable); shows **NSD Hrs** column *(app/pages/_dtr.py)*
- [x] Late, undertime, absent computation against scheduled shift — pure engine; **OT corrected** to time past scheduled_end only (never offsets late arrival); early clock-in never generates OT *(backend/dtr.py)*
- [x] **Night Shift Differential (NSD)** — compute_nsd_hours() per DOLE Art. 86: 10% premium for 10PM–6AM hours; nsd_hours stored in time_logs (migration 020); shown in DTR summary + payroll suggestions *(backend/dtr.py)*
- [x] **Holiday observed dates** — observed_date column on holidays (migration 019); Company Setup holiday form shows optional observed date override for weekend-maximizing moves
- [x] DTR correction requests + approval — employee submits via portal dialog; approve auto-applies and re-computes DTR including nsd_hours *(app/pages/_dtr.py, _employee_portal.py)*
- [x] **Portal break tracking** — ☕ Start Break / End Break buttons in clock widget; records break_out/break_in timestamps; computes actual_break_minutes and overbreak_minutes vs scheduled break (migration 020) *(app/pages/_employee_portal.py)*

**Web-based Time-In Verification** ✅ Complete *(no mobile app required — browser APIs only)*
- [x] Geofencing — browser Geolocation API via declared component captures lat/long on clock-in; distance computed via Haversine formula; validated against company-defined site radius *(app/components/geolocation.py + geolocation_frontend/index.html)*
- [x] Face snapshot — `st.file_uploader` captures photo at clock-in/out (iOS-compatible over HTTP); uploaded to Supabase Storage bucket `dtr-snapshots`; URL stored per log entry *(employee_portal.py)*
- [x] EXIF GPS extraction — server-side Pillow reads GPS coordinates embedded in phone camera photos; works on HTTP without browser geolocation API; location priority: EXIF GPS → browser geolocation → manual office select *(employee_portal.py: _extract_exif_gps())*
- [x] HTTPS tunnel for full GPS — ngrok v3.37.2 configured with static domain (malarian-kimberlee-postnuptially.ngrok-free.dev); Cloudflare Tunnel as backup; start_ngrok.bat / start_https.bat launch scripts included
- [x] **Snapshot compression** — uploaded photos auto-resized to max 640px JPEG quality 55 server-side; reduces 3–8 MB phone photos to ~60–120 KB (30–60× smaller); storage estimate ≈ 1 GB/year per 20 employees vs 40 GB uncompressed

**Snapshot Storage Maintenance** *(run quarterly)*
- [x] `scripts/archive_snapshots.py` — lists all files in `dtr-snapshots` bucket; downloads files older than 30 days to `archives/dtr-snapshots/YYYY-QN/` on local machine; then deletes them from Supabase; supports `--days N` and `--dry-run`; `archive_snapshots.bat` double-click launcher
- [ ] Scheduled Windows Task — automate quarterly archival via Task Scheduler (trigger: 1st day of Jan/Apr/Jul/Oct at 9AM; action: `archive_snapshots.bat`)
- [ ] Archive request flow — if client needs a photo older than 30 days, they contact their IT → IT contacts GenXcript → retrieve from `archives/dtr-snapshots/YYYY-QN/`
- [ ] **Future (when client has a dedicated PC):** auto-sync archive folder to client's local NAS or PC after each quarter via robocopy / rclone; client retains their own cold copy; no reliance on GenXcript retrieval
- [x] Company Setup: "📍 Locations" tab — named GPS sites CRUD with latitude/longitude/radius/active toggle + Google Maps link *(company_setup.py)*
- [x] Time-in record stores: timestamp, coordinates, distance from nearest site, location_id, snapshot URL, method ('manual'/'portal') *(time_logs table in migration 013)*
- [x] Out-of-range alert — portal warns employee if distance > allowed radius; flag stored in time_logs.is_out_of_range *(employee_portal.py)*

### 4C — OT & Leave Request Workflows *(partially done; depends on 4B for full DTR-backed computation)*
- [x] Overtime request form — employee portal submits OT request with date/time/hours *(employee_portal.py)*
- [x] Leave request form — employee portal submits leave with balance check warning *(employee_portal.py)*
- [x] Admin approval — single-level approve/reject with notes; Leave & OT shown side-by-side in two columns (no tab switching) *(employees.py)*
- [x] Request history list — employee sees own requests + statuses *(employee_portal.py)*
- [ ] 2-level approval (Supervisor → HR/Admin) — *depends on Phase 3D role + supervisor assignment*
- [ ] Auto-email notifications — employee notified on approval/rejection; supervisor notified on new submission *(depends on 2-level approval)*

---

## Phase 5: Advanced Payroll
> Depends on Phase 4 (attendance affects deductions). These are additive payroll computation features.

### 5A — Loans Module *(common deduction type not yet tracked)*
- [ ] Loan types (SSS Salary Loan, Pag-IBIG MP2, Company Salary Loan)
- [ ] Loan records per employee (principal, interest, term, start date)
- [ ] Amortization schedule auto-computation
- [ ] Auto-deduction in payroll run per period

### 5B — Special Payroll Runs *(high priority — legally mandated)*
- [x] **DOLE 13th Month Pay Compliance Report** — PD 851 / DOLE LA 18-18 PDF with 4 sections: Establishment Info, Summary (total employed / benefitted / amount), Per-Employee breakdown sorted A–Z, Contact Person; new "DOLE 13th Month" tab in Government Reports; year selector, metrics, expandable table, PDF download *(reports/dole_13th_month_pdf.py, migration: thirteenth_month_accrual in annual_entries)*
- [ ] **13th Month Pay Run** — dedicated payroll run type; auto-computes 1/12 of total basic pay per employee for the calendar year; generates 13th month payslips; links data to DOLE compliance report above *(Jan 31 DOLE deadline)*
- [ ] **Backpay & Separation Pay** — final pay run for separated employees; computes: unpaid salary for days worked, pro-rated 13th month, cash conversion of unused convertible leave credits, and separation pay (½ month per year of service for authorized causes per DOLE Art. 298); links to Phase 3E exit record; generates final payslip
- [ ] Mid-year bonus / performance bonus runs — custom multiplier, ad-hoc disbursement runs

### 5C — Flexible Transactions
- [x] **Night Differential** — NSD hours computed from DTR (10PM–6AM per DOLE Art. 86); payroll run Night Diff input auto-pre-fills from nsd_hours × hourly_rate × 10% when no saved entry exists; DTR Insights panel shows suggestion vs actual *(migration 020, backend/dtr.py, _payroll_run.py)*
- [x] **OT from approved requests** — Overtime input in payroll run auto-pre-fills from approved overtime_requests × hourly_rate × 125%; DTR Insights panel shows approved OT vs DTR-computed OT *(\_payroll_run.py)*
- [x] **Absenteeism deduction** — absent_days from DTR auto-computed as daily_rate × absent_days; displayed as separate line item in Other Deductions; gross = max(basic + earnings − absent_deduction, 0); late/undertime/overbreak are metrics only (no pay deduction) *(\_payroll_run.py)*
- [x] **Daily rate divisor** — company-level setting (22 = 6-day / 26 = 5-day DOLE standard / 30 = calendar month); migration 021; Payroll Policy section in Company Setup with live preview; governs all daily rate and absent deduction calculations *(\_company_setup.py, migration 021)*
- [ ] Night diff + OT combination — "OT on night shift" rate (DOLE: regular OT 125% + night diff 10% = 137.5%); rate table shown in Company Setup alongside holiday pay reference
- [ ] Payroll adjustments — ad-hoc corrections within a pay run (positive or negative)
- [ ] Custom transaction types — define your own earning/deduction codes (e.g., "Rice Allowance", "Uniform Deduction")
- [ ] Custom transaction entries per employee per period
- [ ] Payroll rate profiles — per-group rate sets (e.g., Rank & File vs. Managerial)
- [ ] Payroll code profiles — earning/deduction code dictionary

### 5D — Bank Disbursement *(moved up: clients request this after first payroll run)*
- [ ] Bank account per employee (bank name, account number, account type)
- [ ] Bank file generation — BDO, BPI, Metrobank, UnionBank CSV/DAT formats at end of payroll finalization
- [ ] Salary disbursement record — mark as disbursed, disbursement date, reference number
- [ ] Disbursement status on payslip — "Disbursed via [Bank] on [Date]" footer line

### 5E — Piece Work / Output-Based Pay
- [ ] Piece rate definitions (rate per unit)
- [ ] Piece rate multipliers (holiday, OT, night diff factors on piece work)
- [ ] Per-employee piece work entries per period

---

## Phase 6: Employee Portal Expansion
> Connects all Phase 3–5 features to the self-service portal. Employees become active users, not just recipients.

- [x] **Preferences tab** — Personalise appearance, date formats, display settings, and notifications from within the employee portal (embedded as 5th tab alongside Profile / Payslips / Time & Leave / Documents)
- [ ] **Attendance Certification PDF** — Employee or HR generates a PDF certifying attendance record for a date range (used for bank loans, visa applications, government transactions); downloadable from employee portal and admin employee view
- [ ] **Email & In-App Notifications** — Automated emails on: leave/OT request approved or rejected, payslip available for the period, DTR correction resolved, account password changed; admin configurable on/off per notification type
- [ ] View daily time record (DTR) per period
- [ ] View full time log history with face snapshot thumbnails
- [ ] Submit leave request (with leave balance shown)
- [ ] View leave request history + statuses
- [ ] Submit overtime request
- [ ] View overtime request history + statuses
- [ ] Web-based time-in/time-out — employee clocks in from browser; triggers geolocation check and face snapshot capture *(depends on Phase 4B verification setup)*
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

## Phase 9: Security Hardening
> To be run as a dedicated audit pass before any public/production launch. Covers secrets management, API surface, RLS completeness, and supply-chain hygiene.

- [ ] **Secrets audit** — verify zero hardcoded credentials in tracked files; all keys loaded exclusively from environment variables (`os.environ`) or `st.secrets`; `.env` permanently in `.gitignore` and confirmed not tracked
- [ ] **Frontend credential exposure** — audit all `streamlit.components.v1.html()` and `_stc.html()` injections; ensure no Supabase URLs, anon keys, or tokens ever appear in rendered HTML/JS; CDN script loads (`tsparticles`, etc.) pinned to exact SRI-hashed versions
- [ ] **RLS completeness audit** — run `EXPLAIN` + policy review on every table; confirm no table has accidental permissive `SELECT` for `public` role; verify `service_role` key is never used client-side
- [ ] **Session security** — review `sid` token in URL query params (visible in browser history); consider httpOnly cookie alternative; add session expiry + inactivity timeout (currently 45-min TTL via `@st.cache_resource(ttl=2700)`)
- [ ] **Input sanitization** — audit all `st.text_input` values passed to `.eq()`, `.ilike()` Supabase calls; confirm supabase-py parameterizes queries (no raw SQL f-string injection)
- [ ] **File upload security** — DTR snapshots: validate MIME type + size server-side before Storage upload; reject non-image files; confirm bucket policy is `private` (no anonymous reads)
- [ ] **PDF/report security** — confirm generated PDFs are served directly to the requesting user and not cached in a public path; add company_id assertion before fetching payroll data for PDF generation
- [ ] **Dependency pinning** — pin all `requirements.txt` to exact versions with hashes (`pip-compile --generate-hashes`); add Dependabot or manual quarterly review for CVEs
- [ ] **Error message hardening** — ensure no raw Python tracebacks or database errors are shown to end users; wrap all DB calls in try/except with user-friendly messages
- [ ] **HTTPS enforcement** — document that production deployment must run behind TLS (Nginx + Certbot, Railway, or Cloudflare Tunnel); never run production on plain HTTP
- [ ] **Rate limiting on login** — add server-side attempt counter (e.g., 5 failed logins → 15-min lockout) stored in Supabase or `st.cache_resource` dict to prevent brute-force attacks
- [ ] **Penetration test** — run OWASP ZAP scan on the ngrok/production URL; fix any HIGH/CRITICAL findings before go-live
- [ ] **Shannon Lite** — autonomous white box AI pentester (GitHub: search "shannon lite autonomous pentester"); run against production URL with source code access for deeper OWASP coverage beyond ZAP; white box mode allows it to trace auth flows, RLS logic, and injection paths through actual code paths

---

## Feature Dependency Map

```
Phase 1 (Payroll Core)
  └── Phase 2 (UX + Visibility)
        └── Phase 3 (Core HR)
              ├── 3A Holidays ──────────────── → Phase 5C (Night diff + OT multipliers)
              ├── 3B Employee Info ──────────── → 3E Exit Workflow
              ├── 3C Leave Foundation ──────── → Phase 4C (Leave requests)
              ├── 3D User Roles ────────────── → Phase 4C (2-level approvals)
              └── 3E Exit & Offboarding ─────── → Phase 5B (Final pay / backpay)
                    └── Phase 4 (Attendance)
                          ├── 4A Scheduling ── → 4B DTR
                          ├── 4B DTR ──────── → 4C Workflows + Phase 5
                          │     └── Web Geofencing + Face Snapshot
                          └── 4C Workflows ── → Phase 6 Portal
                                └── Phase 5 (Advanced Payroll)
                                      ├── 5B Special Runs (13th Month, Backpay)
                                      ├── 5C Night Diff + Flexible Transactions
                                      └── 5D Bank Disbursement
                                            └── Phase 6 (Portal Expansion)
                                                  ├── Time-in/out + Notifications
                                                  └── Phase 7 (BI)
                                                        └── Phase 8 (Scale)
                                                              └── Phase 9 (Security Hardening)
```
