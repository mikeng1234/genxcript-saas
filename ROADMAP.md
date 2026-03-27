# GeNXcript Payroll — Product Roadmap

> Last updated: 2026-03-28
> Strategy: Payroll-first → HR Compliance → Attendance → Advanced Payroll → Portal → BI → Scale
> Each phase unlocks the next. Features within a phase are ordered by dependency.

---

## Phase UI: Material 3 Design System ("Tactile Sanctuary") 🎨 In Progress
> Upgrading the entire UI to Google Material 3 design language. Reference designs generated via Google Stitch AI and stored in `fromstitch/` (11 HTML files). Prompts stored in `webprompts/` (11 files with shared design system header).
> **Beelink note:** Pull latest, check `fromstitch/` (01_login.html – 11_preferences.html) and `app/static/` (logos). Run `streamlit run app/main.py` to see current state.

- [x] **Phase A — Global CSS Foundation** — `app/styles.py`: "tactile" theme with full Material 3 token set (`--gxp-*` CSS variables); Plus Jakarta Sans + Material Symbols Outlined fonts; pill buttons, pill inputs, pill tabs, ambient card shadows, rounded modals; `DEFAULT_THEME = "tactile"`
- [x] **Phase B — Sidebar Redesign** — Material Symbols Outlined icons replacing MDI; `injectFonts()` loads fonts directly into `window.parent.document.head`; light-theme fallback colors; pill-shaped active/hover nav items; brand section with "Payroll Solutions" subtitle; `[server] enableStaticServing = true` in config.toml
- [x] **Phase C — Login Page** — `GeNXcript_Dark.png` logo in `app/static/` replacing plain text; static file serving via Streamlit; ambient shadow on logo
- [x] **Topbar** — Fixed top bar injected via JS: company name (left) + user chip + Preferences + My Account + Sign Out (right); `My Account` and `Sign Out` removed from sidebar footer (still hidden in DOM for `clickNav()` routing); 48px content push-down
- [x] **Bug fixes** — Checkbox highlight (Emotion class whitelist); Edit employee 2-click (render-level redirect); Activate/Deactivate on_click pattern (data refresh without dialog close); Print 201 blob URL + immediate state clear; salary hidden by default with toggle; search bar repositioned
- [x] **Phase D — Dashboard** — M3 bento hero grid: Next Pay Date hero, Active Employees accent card, Payroll Expenditure mini-bar chart, Recent Activity feed, Quick Actions row; existing KPI/alerts/remittance panels retained below
- [x] **Phase E — Employees** — Table replaced with 3-column M3 card grid: initials avatar (8-color palette), department pill, name/position/emp no, salary toggle, employment type badge, SSS/PH/PI/TIN gov ID dots; editorial heading; all action buttons retained
- [x] **Phase F — Payroll Run** — M3 redesign: 3-column grid summary (Earnings / Deductions / Employer), accent Net Pay, danger-colored tax + absent rows, improved employee mini-header with avatar + inline badge + Net Pay; filter bar repositioned; emoji tab labels
- [x] **Phase G — Attendance** — Editorial heading; 3 MTD KPI cards (attendance rate / late incidents / NSD hours); status pills upgraded to Material Symbols FILL icons + rounded-full M3 style; daily entry table: avatar+name col, shift pill, colored late/UT/OT values; corrections: M3 card layout with Original→Requested comparison box
- [x] **UX: Login button loading** — Animated dot-dot-dot loading state on Sign In button via JS (disables button, cycles "Signing in." text); logo.jpeg as full left-column background; overflow:hidden to prevent scroll
- [ ] **UX: Default company shortcut** — Add "Set as Default" button on company selection in sidebar; swipe-reveal style matching reminder/alert card pattern; default company auto-selected on login
- [x] **Phase H — Workforce Analytics** — M3 metric cards; Spotfire-style linked charts: department bar → employee bar → bubble calendar with cross-highlighting and opacity control; sidebar renamed from "OT Analytics"
- [x] **Phase I — Government Reports** — Basic Salary column added to all 4 preview tables (SSS R3, PhilHealth RF-1, Pag-IBIG MCRF, BIR 1601-C)
- [x] **Phase J — Calendar** — CSS Grid calendar (7-col, rounded cells, hover scale); two-column layout [7,3] with Upcoming Events sidebar (countdown badges, colored left borders per type); M3 legend; holiday table in collapsible expander
- [x] **Phase K — Company Setup** — d3-org-chart (bumbeishvili) with search + pulse; Leaflet.js maps for office locations with geofence circles; reports_to hierarchy (migration 025); email/phone on org chart nodes; photo support; department employee count fix
- [x] **Employee Photo Upload** — migration 026 (photo_url); Supabase "employee-photos" bucket; auto-compress 200px JPEG; displayed in employee cards + org chart + edit dialog
- [x] **Employee Portal UX** — custom topbar; checkbox highlight fix; permanent address redesign; People Search with org chart; Leaflet clock-in map (pulsing dot + geofence + Inside/Outside badge)
- [x] **Dashboard Performance** — N+1 → batch query; @st.cache_data(ttl=120); skeleton shimmer loading; counting number animations; card entrance animations (fade-in + staggered slide-up)
- [x] **Dashboard v2 Redesign** — 6-panel bento grid (Payroll Overview with dept-stacked bars + Recent Payroll + Mini Calendar + Donut Workforce + Attendance Detail + Pending Requests); [3,1] outer layout with Reminders/Alerts sidebar; clickable cards with navigation + expanded Payroll Overview dialog; SVG donut with on-ring labels; pure HTML mini calendar; per-row JS height equalizer
- [x] **GeNXcript Branding** — renamed GenXcript → GeNXcript across 66 files; topbar badge with individually colored letters
- [x] **RLS Hardening** — user_preferences + audit_logs RLS enabled (migrations 023, 024)
- [x] **Employee Cards Redesign** — compact single-row cards with swipe-right-to-reveal action buttons (Edit/Print/Deactivate); department grouping with headers; photo integration from Supabase Storage; `on_click` callbacks for instant dialog open (no stale data flash); skeleton loading on edit dialog
- [x] **Dashboard Stat Cards** — swipe-up-to-reveal action buttons (matching employee card pattern); counting number animations; skeleton shimmer loading; company switch data refresh fix
- [x] **Dashboard Mini Calendar** — event date coloring (green for paydays, red for holidays); upcoming events sidebar
- [x] **Payroll Processing Redesign** — employee cards with photo avatars grouped by department; 4-column grid; popup dialog for earnings computation (replaces expand/collapse); collapsible filter bar matching employee directory pattern
- [x] **Gross Pay Composition** — fixed to show percentages instead of peso amounts in Payroll History analytics
- [x] **Systematic Caching** — `@st.cache_data` with `_cid` keying across all pages (~35 cached functions); `on_click` callback pattern for buttons to prevent stale dialog rendering
- [x] **7 Custom Skills** — PH Labor Law, PH Tax & Contributions, Payroll Best Practices, Code Quality, Security & Privacy Auditor, Supabase Patterns, GitHub Workflow

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

### 3D — Company Policy Extraction *(prerequisite for correct payroll configuration)*
- [ ] **Mind Joggler Presentation** — interactive questionnaire / guided wizard that walks a new client through every company policy the system needs: pay frequency, daily rate divisor, OT rules, leave entitlements, holiday pay policy, break rules, NSD policy, 13th month computation method, loan deduction rules, government contribution employer share policy, cut-off dates, probationary period, separation pay rules; outputs a structured policy document that seeds Company Setup

### 3E — User Roles & Access Control ✅ Mostly Complete
- [x] Role definitions — Admin, HR Manager, Payroll Officer, Supervisor, Employee; 5-role model with PAGE_ACCESS + PAGE_READONLY maps *(migration 028)*
- [x] Role-based page access — navigation filtered by role; read-only guards on mutation controls; access guard in page dispatch *(auth.py, main.py)*
- [x] Supervisor assignment — `reports_to` hierarchy with recursive `get_supervisor_tree()` SQL function; team-scoped dashboard + attendance *(migration 025, 028)*
- [x] Role selector in user management UI — Company Setup "Users & Roles" tab: change role, invite user, remove user with audit logging *(company_setup.py)*
- [x] RLS policy updates — 12+ policies updated for new roles *(migration 028)*
- [x] Role badge in topbar — color-coded pill showing current role next to user name *(main.py)*
- [x] Supervisor Team Dashboard — team-scoped bento grid (team overview, member count, pending approvals); financial data hidden *(dashboard.py)*
- [ ] **Supervisor Dashboard v2** — ADP-style manager tool: DTR exceptions, holiday pay validator, OT authorization, statutory overview, leave tracker, 201 file access; "Coming Soon" cards for Loans, Disciplinary, HMO *(in progress)*

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
- [ ] Archive request flow — if client needs a photo older than 30 days, they contact their IT → IT contacts GeNXcript → retrieve from `archives/dtr-snapshots/YYYY-QN/`
- [ ] **Future (when client has a dedicated PC):** auto-sync archive folder to client's local NAS or PC after each quarter via robocopy / rclone; client retains their own cold copy; no reliance on GeNXcript retrieval
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

### 5E — OT Type Distinction *(prerequisite for accurate OT pay computation)*
- [ ] **OT type field on overtime_requests** — `ot_type` column: `regular`, `rest_day`, `holiday`; dropdown in portal OT request form
- [ ] **OT rate multipliers** — Regular OT 125%, Rest Day OT 130%, Holiday OT per DOLE rate table (Regular Holiday 200%/260%, SNWH 130%/169%)
- [ ] **Payroll integration** — OT auto-fill in payroll run uses correct multiplier per OT type
- [ ] **Supervisor OT authorization** — supervisor dashboard shows OT type in approval view

### 5F — Piece Work / Output-Based Pay
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

## Phase 6B: HR Compliance & Employee Relations
> Modules for Philippine labor law compliance beyond payroll. Unlocks full digital 201 file and supervisor management capabilities.

### 6B-1 — Disciplinary Action Hub *(DOLE Due Process Compliance)*
- [ ] **Disciplinary actions table** — `disciplinary_actions` with type (verbal warning, written warning, suspension, termination), dates, status
- [ ] **Notice to Explain (NTE)** — template-driven NTE generation with offense details, employee response field, response deadline
- [ ] **Notice of Decision** — decision template with findings, penalty, effectivity date
- [ ] **Two-Notice Rule workflow** — enforces DOLE-mandated NTE → hearing → Decision sequence; prevents illegal dismissal claims
- [ ] **Supervisor view** — supervisors can initiate NTE for their team; HR/Admin review and finalize
- [ ] **Audit trail** — full history of all disciplinary actions per employee, linked to 201 file

### 6B-2 — BIR 2316 Digital Sign-off *(optional)*
- [ ] **Acknowledgment tracking** — record that employee received and acknowledged their annual BIR 2316 certificate
- [ ] **Manager dashboard** — view which team members have/haven't acknowledged their 2316
- [ ] **Portal integration** — employee signs off via portal; timestamp recorded

### 6B-3 — HMO & Group Insurance Portal *(optional)*
- [ ] **HMO plans table** — plan name, provider, coverage limits (MBL), premium tiers
- [ ] **Employee HMO enrollment** — assigned plan, dependents list, coverage start/end dates
- [ ] **Dependent management** — add/remove dependents with relationship, DOB, coverage status
- [ ] **Supervisor view** — read-only team HMO enrollment status

### 6B-4 — Probation Tracker & Regularization *(optional)*
- [ ] **Probation tracking** — auto-compute probation end date from hire date + company probationary months setting
- [ ] **5th-month evaluation alert** — dashboard reminder 30 days before regularization deadline
- [ ] **Regularization workflow** — supervisor submits evaluation → HR approves → auto-update employment_type to "regular"
- [ ] **Failed regularization** — termination workflow with DOLE-compliant notice period

### 6B-5 — Internal Transfer & Promotion Workflow
- [ ] **Salary grade history** — table tracking salary changes with effective date, reason (promotion/merit/adjustment), old/new values
- [ ] **Promotion letter generator** — template-driven PDF with new position, salary, effectivity date
- [ ] **Contract addendum** — auto-generated addendum reflecting changes to employment terms
- [ ] **Supervisor recommendation** — supervisor can recommend promotion; HR/Admin approves

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

## Phase 8: Demo Simulator Script ("Day-by-Day HR Playback")
> A scripted simulation tool that replays realistic HR operations day-by-day, populating a company from scratch. Useful for demos, testing, and training. The script drives the actual UI/API — not raw SQL — so it validates the full user flow.

### Data Roster (pre-built database)
- [ ] **Name pool** — 70 unique Filipino names (first + last), randomized but deterministic per run
- [ ] **Salary bands** — 15 salary levels (₱12k–₱120k monthly) mapped to position tiers
- [ ] **Shift profiles** — 3 shifts (Warehouse 7–4, Standard 8–5, Executive 9–6)
- [ ] **Department list** — 5 departments (Operations, Sales, Finance, Admin, Executive)
- [ ] **Position library** — 30 unique positions with org-ladder rank (CEO → VP → Manager → Supervisor → Staff)
- [ ] **Gov ID templates** — SSS/PhilHealth/Pag-IBIG/TIN number patterns per employee

### Phase A — Hiring Phase (Days 1–35)
> HR hires one employee per day, filling the org chart from the top down.
- [ ] Day 1: Create company profile + settings (pay frequency, daily rate divisor, etc.)
- [ ] Day 2–6: Hire Executive tier (GM, 3 VPs, Executive Assistant)
- [ ] Day 7–11: Hire Department Managers (Operations Mgr, Area Sales Mgr, Finance Mgr, Admin & HR Mgr, + 1 Supervisor)
- [ ] Day 12–20: Hire Supervisors and Senior Staff (Warehouse Supervisor, Logistics Supervisor, Sales Supervisors, Senior Accountant, Account Executives)
- [ ] Day 21–35: Hire Rank & File (Warehouse Staff, Drivers, Sales Reps, Clerks, Cashier, Receptionist, IT Support)
- [ ] Each day: pick from roster → fill employee form → assign department/position/salary/schedule/leave template/gov IDs

### Phase B — Attendance & DTR Phase (Days 36–65)
> Simulate 30 days of clock-ins/outs with realistic patterns.
- [ ] Generate time logs per employee per day (varying late arrivals, early departures, absences, OT)
- [ ] Inject break records (some employees with overbreak)
- [ ] Add NSD hours for warehouse shift employees
- [ ] File 3–5 leave requests (VL/SL) + approve them
- [ ] File 2–3 OT requests + approve them
- [ ] Submit 1–2 DTR correction requests + approve/reject

### Phase C — First Payroll Phase (Days 66–70)
> Run the first full payroll cycle.
- [ ] Create pay period (semi-monthly or monthly based on company setting)
- [ ] Compute & Save each employee (earnings, deductions, DTR suggestions auto-applied)
- [ ] Submit for Review → Approve & Finalize
- [ ] Generate payslips (PDF)
- [ ] Record government remittances (SSS, PhilHealth, Pag-IBIG, BIR)

### Phase D — Ongoing Operations (Days 71–100)
> Simulate normal HR operations over 1 month.
- [ ] 1 employee resignation (separation, deactivation)
- [ ] 1 new hire (probationary)
- [ ] 1 salary adjustment (promotion)
- [ ] Continue attendance logging
- [ ] Run 2nd payroll cycle
- [ ] Generate government reports (SSS R3, PhilHealth RF-1, Pag-IBIG MCRF, BIR 1601-C)

### Phase E — Year-End (Days 101–110)
> Year-end compliance.
- [ ] 13th Month Pay computation + DOLE compliance report
- [ ] BIR 2316 annual certificates
- [ ] BIR 1604-C alphalist
- [ ] Leave carry-over / cash conversion

### Simulator UI
- [ ] **"Next Day" button** — advances to the next scripted action, executes it, shows summary of what was done
- [ ] **"Previous Day" button** — undoes the last action (deletes the employee/record that was just created)
- [ ] **Day counter + progress bar** — "Day 14 of 110 — Hiring Phase (40%)"
- [ ] **Action log panel** — scrollable list of all actions taken so far
- [ ] **Phase indicator** — shows current phase (Hiring / Attendance / Payroll / Operations / Year-End)
- [ ] **Speed mode** — "Run All" button that fast-forwards through remaining days in current phase

---

## Phase 8B: Government Compliance Auditor Script
> An automated auditor that reads the generated government forms (PDF / data) and validates them against agency rules, rate tables, and computation logic. Catches errors before actual filing — acts as a virtual BIR / SSS / PhilHealth / Pag-IBIG examiner.

### Common Framework
- [ ] **Form reader** — parse generated PDFs (SSS R3, PhilHealth RF-1, Pag-IBIG MCRF, BIR 1601-C, BIR 2316, BIR 1604-C, DOLE 13th Month) via reportlab reverse-parse or direct data access from DB
- [ ] **Rate table loader** — load the current year's contribution tables (SSS Circular 2024-006, PhilHealth CY2025, HDMF 2025, BIR TRAIN Law brackets) as the source of truth
- [ ] **Audit result model** — per-employee and per-form findings: `PASS`, `WARNING`, `ERROR`, with field reference, expected vs actual values, and citation (e.g., "SSS Circular 2024-006 §3.1")
- [ ] **Audit report output** — summary dashboard (total checks / passed / warnings / errors), drill-down per agency, exportable PDF audit trail

### SSS Auditor
- [ ] **MSC bracket validation** — verify each employee's Monthly Salary Credit matches their basic salary per the 2025 MSC table (₱5,000–₱35,000 range, 44 brackets)
- [ ] **Contribution split** — confirm EE share (5%) and ER share (10%) computed correctly per MSC; total = 15%
- [ ] **EC contribution** — verify ₱10 if MSC ≤ ₱15,000, ₱30 if MSC > ₱15,000
- [ ] **R3 form totals** — cross-check sum of individual contributions matches the R3 summary row; verify employee count matches active headcount for the period
- [ ] **Late filing detection** — flag if remittance date is after the 10th of the following month

### PhilHealth Auditor
- [ ] **Premium rate** — verify 5% of basic salary (2.5% EE + 2.5% ER), floor ₱10,000, ceiling ₱100,000
- [ ] **RF-1 form validation** — cross-check individual premiums sum to form total; verify PhilHealth numbers match employee records
- [ ] **Minimum/maximum cap** — flag employees below floor (min premium ₱500) or above ceiling (max premium ₱5,000)

### Pag-IBIG (HDMF) Auditor
- [ ] **Tiered rate** — verify EE: 1% if basic ≤ ₱1,500, 2% if > ₱1,500; ER: always 2%; both capped at max ₱200
- [ ] **MCRF form validation** — cross-check individual contributions sum to form total; verify Pag-IBIG MID numbers
- [ ] **MP2 deduction check** — if employee has MP2 savings, verify separate line item and correct deduction

### BIR Auditor
- [ ] **Withholding tax bracket** — recompute each employee's withholding tax using TRAIN Law 6-bracket table; compare against payroll entry value; flag if difference > ₱1
- [ ] **1601-C monthly return** — verify sum of all employee withholding taxes matches form total; check correct BIR TIN format
- [ ] **2316 annual certificate** — verify YTD gross income = sum of all period basic pays; verify YTD tax withheld = sum of all period WHT; check 13th month + de minimis exemptions applied correctly
- [ ] **1604-C alphalist** — verify employee count matches; cross-check totals against sum of all 2316 certificates; flag missing TIN entries
- [ ] **Tax status validation** — verify employee tax status (S, ME, ME1, ME2, ME3, etc.) matches the personal exemption applied in computation

### DOLE Auditor
- [ ] **13th Month Pay** — recompute 1/12 of total basic salary per employee for the year; compare against DOLE compliance report values
- [ ] **Minimum wage compliance** — verify no employee's daily rate (basic / daily_rate_divisor) falls below the regional minimum wage for NCR/Palawan
- [ ] **OT/NSD premium rates** — verify OT at 125% and NSD at 10% were applied correctly in payroll entries vs DTR data

### Auditor UI
- [ ] **Run Audit button** — triggers full audit across all agencies for a selected pay period or year
- [ ] **Traffic light dashboard** — green/yellow/red per agency with counts
- [ ] **Drill-down table** — per-employee findings with expected vs actual columns
- [ ] **Fix suggestions** — actionable text for each ERROR (e.g., "Employee PTC-005: SSS contribution should be ₱2,250 (MSC ₱15,000) but recorded as ₱2,100. Difference: ₱150 underpayment.")
- [ ] **Export audit report** — PDF with company letterhead, audit date, auditor signature line, findings table

---

## Phase 9: Scale (Production)
> Only after product-market fit is confirmed. These are infra and platform decisions, not features.
> **Strategy:** Don't over-engineer infrastructure before you have paying clients. Current setup (Beelink + Cloudflare + Supabase free tier) handles first 20 clients at zero hosting cost. Every peso goes to development, not servers.

### 9A — Current Setup (1–20 clients) ✅ In Use
> Single Streamlit instance on Beelink Mini PC. All companies share one process. Data isolated via Supabase RLS + `_cid`-keyed `@st.cache_data`. Zero hosting cost.

- [x] **Beelink Mini PC** — always-on home server (I:\SaaS\PaySys)
- [x] **Cloudflare Quick Tunnel** — free HTTPS URL (`*.trycloudflare.com`), auto-restart via `start_all.bat`
- [x] **Discord webhook** — auto-posts new tunnel URL on restart
- [x] **Supabase free tier** — 500 MB DB, 1 GB storage, 50k monthly active users
- [x] **`@st.cache_data` everywhere** — ~35 cached functions, 2-10 min TTL, write invalidation
- [x] **Supervisor Portal team cache** — `_load_team_cache()` bulk-loads all subordinate employees + profiles in 2 queries (cached 2 min); eliminates ~12 redundant DB round-trips per page load across 5 tab sections; 201 dialog reads from cache (zero DB calls)
- [ ] **Cache optimization & DB query audit** — Profile all pages for N+1 queries and redundant DB calls; consolidate into bulk-cached loaders (same pattern as supervisor cache); target: <5 DB queries per page load for all roles; add `print()` timing to identify slowest queries; consider `@st.cache_resource` for DB connection pooling
- [ ] **Permanent domain** — buy a cheap domain ($2/yr `.xyz` or `.site`), add to Cloudflare, create named tunnel for fixed URL (e.g., `app.genxcript.xyz`)
- [ ] **Auto-start on boot** — shortcut in `shell:startup` folder pointing to `start_all.bat`
- [ ] **Windows sleep prevention** — `powercfg /change standby-timeout-ac 0`

### 9B — Small Scale (20–50 clients, ~6 months)
> Multiple Streamlit instances behind Nginx reverse proxy on a proper VPS. ~₱2,000/mo.

- [ ] **VPS migration** — DigitalOcean or AWS Lightsail (Singapore region, closest to PH): 2 vCPU, 4 GB RAM, ~$12-24/mo
- [ ] **Docker Compose** — containerize Streamlit app + Nginx; `docker-compose up -d` deploys everything
- [ ] **Multiple instances** — group 10-15 clients per Streamlit instance (port 8501, 8502, 8503...); Nginx routes by subdomain
- [ ] **Custom domain** — `genxcript.com` with subdomains: `client-a.genxcript.com`, `client-b.genxcript.com`
- [ ] **SSL via Certbot** — auto-renewing Let's Encrypt certificates for all subdomains
- [ ] **GitHub Actions CI/CD** — push to `master` → auto-deploy to VPS via SSH
- [ ] **Uptime monitoring** — free tier UptimeRobot or Healthchecks.io; alert on Discord if any instance goes down
- [ ] **Supabase Pro** — upgrade when approaching free tier limits (~$25/mo for 8 GB DB + 100 GB storage)
- [ ] **Daily DB backup** — `pg_dump` cron job → local + cloud storage (S3 or Backblaze B2)

### 9C — Medium Scale (50–100 clients, ~1 year)
> Start React frontend rebuild while keeping Streamlit running for existing clients. ~₱5,000/mo hosting.

- [ ] **React frontend** — replace Streamlit for production-grade UX (Next.js or Vite + React)
- [ ] **FastAPI backend** — REST API layer between React frontend and Supabase; enables mobile app later
- [ ] **API authentication** — JWT tokens via Supabase Auth; role-based access at API level
- [ ] **Mobile app** — React Native or Flutter for employee portal (clock-in, payslips, leave requests)
- [ ] **White-label support** — resellers can rebrand; company logo + colors loaded from DB
- [ ] **Parallel operation** — run Streamlit (existing clients) + React (new clients) simultaneously during migration

### 9D — Large Scale (100+ clients, ~2 years)
> Full SaaS architecture. ~₱15,000/mo+ hosting. Consider hiring DevOps.

- [ ] **Kubernetes (K8s)** or **Railway/Render auto-scaling** — containers scale up/down based on traffic
- [ ] **CDN for static assets** — Cloudflare or Vercel Edge; instant page loads worldwide
- [ ] **Read replicas** — Supabase read replicas for analytics queries (don't slow down transactional queries)
- [ ] **Per-seat pricing engine** — billing integration (Stripe or PayMongo for PH)
- [ ] **Electron desktop app** — if clients demand offline-first (sync when connected)
- [ ] **API layer (GraphQL)** — enables 3rd-party integrations (payroll banks, HRIS, BIR e-filing)
- [ ] **Record retention module** — 5–7 year archival per DOLE and BIR requirements; cold storage tier
- [ ] **SOC 2 / ISO 27001 prep** — if targeting enterprise clients or government contracts

### Infrastructure Cost Projection
| Phase | Clients | Monthly Cost | What You Get |
|-------|---------|-------------|-------------|
| **9A (Now)** | 1–20 | ₱0 | Beelink + free Cloudflare + free Supabase |
| **9B (~6 mo)** | 20–50 | ~₱2,000 | VPS + domain + Supabase Pro |
| **9C (~1 yr)** | 50–100 | ~₱5,000 | VPS cluster + React rebuild + mobile app |
| **9D (~2 yr)** | 100+ | ~₱15,000+ | K8s + CDN + read replicas + billing |

---

## Phase 10: Security Hardening
> To be run as a dedicated audit pass before any public/production launch. Covers secrets management, API surface, RLS completeness, and supply-chain hygiene.

- [ ] **Secrets audit** — verify zero hardcoded credentials in tracked files; all keys loaded exclusively from environment variables (`os.environ`) or `st.secrets`; `.env` permanently in `.gitignore` and confirmed not tracked
- [ ] **Frontend credential exposure** — audit all `streamlit.components.v1.html()` and `_stc.html()` injections; ensure no Supabase URLs, anon keys, or tokens ever appear in rendered HTML/JS; CDN script loads (`tsparticles`, etc.) pinned to exact SRI-hashed versions
- [ ] **RLS completeness audit** — run `EXPLAIN` + policy review on every table; confirm no table has accidental permissive `SELECT` for `public` role; verify `service_role` key is never used client-side
- [ ] **Session security** — review `sid` token in URL query params (visible in browser history); consider httpOnly cookie alternative; add session expiry + inactivity timeout (currently 45-min TTL via `@st.cache_resource(ttl=2700)`)
- [ ] **Input sanitization** — audit all `st.text_input` values passed to `.eq()`, `.ilike()` Supabase calls; confirm supabase-py parameterizes queries (no raw SQL f-string injection)
- [ ] **File upload security** — DTR snapshots: validate MIME type + size server-side before Storage upload; reject non-image files; confirm bucket policy is `private` (no anonymous reads)
- [ ] **PDF/report security** — confirm generated PDFs are served directly to the requesting user and not cached in a public path; add company_id assertion before fetching payroll data for PDF generation
- [ ] **Dependency pinning** — pin all `requirements.txt` to exact versions with hashes (`pip-compile --generate-hashes`); add Dependabot or manual quarterly review for CVEs
- [ ] **Error message hardening (2-tier)** — Two types of error display:
  - **User-facing (browser):** friendly error page ("Something went wrong. Please try again or contact your administrator.") with a reference code (e.g., `ERR-20260324-A3F2`) and a "Report Issue" button; no raw tracebacks, no stack traces, no database error details visible to users
  - **Developer-facing (server logs):** full Python traceback + Supabase error details written to `stderr` / structured log file with timestamp, user ID, company ID, page, and the reference code matching the user-facing message; use Python `logging` module with rotating file handler (`logs/genxcript.log`, 10MB max, 5 backups)
  - Wrap all page `render()` functions in a top-level try/except that catches any unhandled exception, logs the full traceback server-side, and shows the friendly error page client-side
  - Database errors (PGRST*, connection timeouts, JWT expired) get specific friendly messages ("Connection issue — please refresh") instead of generic "Something went wrong"
  - Form validation errors remain inline (red text under the field) — only unexpected/unhandled errors get the friendly error page treatment
- [ ] **HTTPS enforcement** — document that production deployment must run behind TLS (Nginx + Certbot, Railway, or Cloudflare Tunnel); never run production on plain HTTP
- [ ] **Rate limiting on login** — add server-side attempt counter (e.g., 5 failed logins → 15-min lockout) stored in Supabase or `st.cache_resource` dict to prevent brute-force attacks
- [ ] **Penetration test** — run OWASP ZAP scan on the ngrok/production URL; fix any HIGH/CRITICAL findings before go-live
- [ ] **Shannon Lite** — autonomous white box AI pentester (GitHub: search "shannon lite autonomous pentester"); run against production URL with source code access for deeper OWASP coverage beyond ZAP; white box mode allows it to trace auth flows, RLS logic, and injection paths through actual code paths

---

## Phase 11: QA & Test Guide
> Final quality gate before production. Systematic page-by-page testing + written test guide for ongoing regression testing.

### 11A — Test Guide Creation
> At the end of development, create a step-by-step test guide for every page. Each guide covers happy path, edge cases, error scenarios, and expected results.

- [ ] **Login Page** — valid/invalid credentials, employee vs admin login, password reset flow, "Remember me", rate limiting, wrong company
- [ ] **Dashboard** — skeleton loading, data accuracy (active employees, payroll figures, YTD), company switch refresh, bento card clicks, reminder/alert actions, calendar events
- [ ] **Employees** — CRUD (add/edit/deactivate), photo upload/remove, salary toggle, filter combinations, search, gov ID validation dots, 201 PDF print, portal invite, password reset
- [ ] **Employees > Leave & OT Approvals** — approve/reject flows, badge counts, history, cross-navigation from dashboard reminders
- [ ] **Employees > Leave Balances** — year selector, department filter, balance accuracy vs leave requests, carry-over
- [ ] **Employees > Special Leaves** — CRUD, approval flow
- [ ] **Payroll Run** — create period, compute & save (verify SSS/PH/PI/tax), DTR suggestions, absent deduction, batch save, submit for review, approve & finalize, status refresh
- [ ] **Payslips** — PDF generation, peso sign rendering, YTD totals, all deduction line items
- [ ] **Payroll Comparison** — period-over-period variance, new hires/exits detection
- [ ] **Attendance > Daily Entry** — inline time inputs, save all, late/UT/OT computation, shift column
- [ ] **Attendance > Summary** — selectable rows, day-by-day timeline, department filter, heatmap colors, overnight shift rendering
- [ ] **Attendance > Corrections** — submit/approve/reject, DTR recomputation
- [ ] **Workforce Analytics** — OT heatmap, Late Monitoring (Spotfire drill-down), Undertime (same), Break Monitoring, department→employee→calendar flow
- [ ] **Government Reports** — SSS R3, PhilHealth RF-1, Pag-IBIG MCRF, BIR 1601-C (salary column, totals, PDF download), BIR 2316, BIR 1604-C, DOLE 13th Month
- [ ] **Calendar** — month navigation, today button, pay period highlighting, holiday colors, deadline dots, upcoming events sidebar, holiday table
- [ ] **Company Setup > General** — company profile save, payroll policy, daily rate divisor
- [ ] **Company Setup > Leave Templates** — CRUD, carry-over policy, assignment
- [ ] **Company Setup > Holidays** — national read-only, custom CRUD, observed date, year selector
- [ ] **Company Setup > Schedules** — CRUD, overnight toggle, break clock toggle, working days
- [ ] **Company Setup > Locations** — Leaflet map, add/edit/delete GPS location, geofence radius
- [ ] **Company Setup > Organization** — department CRUD, hierarchy, org chart (d3-org-chart), search/pulse, employee count, reports_to
- [ ] **Company Setup > Activity Log** — search, action types, before/after diffs
- [ ] **Employee Portal > My Profile** — view/edit personal info, permanent address checkbox, photo
- [ ] **Employee Portal > My Payslips** — list, download PDF
- [ ] **Employee Portal > My Time & Leave** — clock in/out, break tracking, Leaflet map, leave/OT request filing, DTR history, correction request
- [ ] **Employee Portal > People Search** — org chart with search, pulse effect
- [ ] **Employee Portal > Preferences** — theme, display settings
- [ ] **Multi-company** — company switch, data isolation, cache refresh, sidebar updates

### 11B — Full Bug Sweep
> Pass through every page systematically, testing each item from the test guide. Document and fix all bugs found.

- [ ] **Pass 1 — Happy path** — walk through each page's primary workflow end-to-end
- [ ] **Pass 2 — Edge cases** — empty states, zero values, missing data, maximum lengths, special characters
- [ ] **Pass 3 — Error scenarios** — network timeout, invalid input, permission denied, expired session
- [ ] **Pass 4 — Cross-page flows** — dashboard → employees, reminders → approvals, alerts → gov reports, payroll → payslips
- [ ] **Pass 5 — Multi-tenant** — switch companies, verify data isolation, cache freshness
- [ ] **Pass 6 — Responsive/mobile** — test via Cloudflare tunnel on mobile browser
- [ ] **Pass 7 — Security red team** — run the 10 scenarios from Security & Privacy Auditor skill

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
                                                        └── Phase 8 (Demo Simulator + Gov Auditor)
                                                              └── Phase 9 (Scale)
                                                                    └── Phase 10 (Security Hardening)
                                                                          └── Phase 11 (QA & Test Guide)
```
