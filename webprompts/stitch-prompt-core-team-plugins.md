# GeNXcript Payroll — Plugin Architecture: Core Team Alignment (Stitch Prompt)

## INSTRUCTION

Generate a complete, single-file, self-contained HTML page (HTML + CSS + JS inline) that serves as an **internal team alignment document** explaining the GeNXcript Payroll plugin/module architecture to 4 core stakeholders.

This is NOT for clients or investors. This is an **internal strategy document** — direct, honest, with real numbers and real tradeoffs. Think of it as a multi-perspective interactive wiki page for the leadership team.

The page has **4 tabs at the top**, each tailored to a specific stakeholder role. All tabs share a persistent module reference bar. Switching tabs smoothly transitions content with no page reload.

The output must be a single HTML file. No external dependencies except Google Fonts. Fully responsive. All CSS and JS inline within the HTML file.

---

## GLOBAL DESIGN SYSTEM

### Colors
```
--bg: #f8fafc                /* Page background — light, professional */
--surface: #ffffff           /* Card surfaces */
--primary: #005bc1           /* GeNXcript Blue — headers, active tab, links */
--primary-dark: #003d82      /* Hover states */
--primary-light: #e8f0fe     /* Light blue backgrounds */
--text: #191c1d              /* Primary text */
--text-secondary: #727784    /* Secondary/muted text */
--border: #e2e8f0            /* Card borders, dividers */
--module-core: #10b981       /* 🟢 Core */
--module-payroll: #3b82f6    /* 🔵 Payroll Engine */
--module-time: #f59e0b       /* 🟡 Time & Attendance */
--module-leave: #f97316      /* 🟠 Leave & OT */
--module-supervisor: #ef4444 /* 🔴 Supervisor Portal */
--module-analytics: #8b5cf6  /* 🟣 Analytics & Insights */
--module-compliance: #374151 /* ⚫ Compliance+ */
```

### Typography
- Font: `'Plus Jakarta Sans', sans-serif` — import from Google Fonts: `https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap`
- Also load `'JetBrains Mono'` for code blocks and metric displays: `https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&display=swap`
- Page title: 800 weight, 2rem
- Section headings: 700 weight, 1.5rem
- Subsection headings: 600 weight, 1.125rem
- Body text: 400 weight, 0.9375rem, line-height 1.7
- Code blocks: 'JetBrains Mono', 0.85rem, background #1e293b, color #e2e8f0, rounded corners, padding 1.25rem
- Metric numbers: 'JetBrains Mono', 700 weight

### Layout
- Max content width: 1200px, centered
- Card style: white background, 1px solid var(--border), border-radius 12px, padding 1.5rem, subtle box-shadow (0 1px 3px rgba(0,0,0,0.06))
- Grid layouts: CSS Grid with gap 1.25rem
- Tab bar: sticky at top, z-index 100, white background with bottom border

### Interactions
- Tab switching: smooth fade transition (opacity + translateY), no page reload
- All animations: CSS transitions, 0.3s ease
- Scroll-triggered fade-in: elements animate in with IntersectionObserver (translateY 20px → 0, opacity 0 → 1)
- Hover effects on cards: subtle lift (translateY -2px) and shadow increase
- Print styles: `@media print` — show all tabs stacked, hide interactive controls, page-break-before on each tab section

---

## PAGE STRUCTURE

### Header
- Top bar with "GeNXcript Payroll" brand text in var(--primary) blue, 700 weight
- Subtitle: "Plugin Architecture — Core Team Alignment" in var(--text-secondary)
- Small "INTERNAL" badge — red background (#fef2f2), red text (#dc2626), uppercase, 0.75rem, border-radius 4px
- Date: "March 2026" right-aligned

### Tab Navigation
Sticky tab bar directly below header. 4 tabs, horizontally arranged:

1. **🎯 Product** — accent color: var(--primary)
2. **🔧 Engineering** — accent color: #059669 (green)
3. **💰 Sales** — accent color: #d97706 (amber)
4. **📊 Finance** — accent color: #7c3aed (purple)

Active tab has:
- Bottom border (3px) in its accent color
- Bold text in accent color
- Slight background tint

Inactive tabs: var(--text-secondary), no bottom border, hover shows light background

Clicking a tab smoothly fades out current content and fades in new content. Use CSS classes toggled by JS — no framework needed.

### Persistent Module Reference Bar
A horizontal bar **below the tabs and above the tab content**, always visible regardless of which tab is active. It shows all 7 modules as small colored pill/chip elements:

```
🟢 Core  🔵 Payroll  🟡 Time  🟠 Leave/OT  🔴 Supervisor  🟣 Analytics  ⚫ Compliance+
```

Each pill is clickable. When clicked:
- The pill gets a "selected" ring/glow effect
- Across ALL tab content, anything related to that module gets visually highlighted (a brief pulse animation or background highlight)
- Clicking again deselects

This creates cross-tab module linking — the PM can click "Payroll" and see it highlighted in the CTO's file mapping, the Sales tier cards, and the Finance revenue attribution simultaneously.

---

## TAB 1: 🎯 PRODUCT — Feature Scope & Roadmap

### Section 1.1: Module Map
A visual diagram showing all 7 plugin groups as colored blocks/cards arranged in a logical layout. Use CSS Grid.

**Layout**: Core block at center/top (largest), with the 6 other modules arranged around it showing dependency lines (CSS pseudo-elements or SVG lines).

Each module block contains:
- Module name and color dot
- List of features within that module
- A small "required by" indicator showing which modules depend on it

Module contents:

**🟢 CORE (Always Included)**
- Company Setup
- Employee Management
- Authentication & RBAC
- Employee Portal (Self-Service)
- Preferences & Settings

**🔵 PAYROLL ENGINE**
- Payroll Run & Computation
- Gov't Contributions Auto-calc (SSS, PhilHealth, Pag-IBIG, BIR Withholding Tax)
- Payslip Generation (PDF)
- Gov't Reports (SSS R3, PhilHealth RF-1, Pag-IBIG MCRF, BIR 1601-C)
- 13th Month Pay Computation

**🟡 TIME & ATTENDANCE**
- DTR Management (Daily Time Records)
- Shift Schedules & Assignment
- DTR Corrections (with approval workflow)
- Geolocation Clock-in (GPS radius verification)
- Night Shift Differential (auto NSD calculation)

**🟠 LEAVE & OT MANAGEMENT**
- Leave Requests & Approvals
- Leave Balances (entitlement templates, accrual)
- Overtime Requests & Approvals
- Special Leaves (Solo Parent, Maternity, Paternity, VAWC)

**🔴 SUPERVISOR PORTAL**
- Team Dashboard (bento grid layout)
- Team Payroll View (read-only)
- Team 201 Cards
- Approval Workflows (leave, OT, DTR corrections)

**🟣 ANALYTICS & INSIGHTS**
- Payroll Comparison (period-over-period)
- OT Heatmap (department × week)
- Lateness & Undertime Monitoring
- Break Monitoring
- Dashboard Analytics Widgets

**⚫ COMPLIANCE+**
- BIR 2316 (Annual Income Tax Return)
- BIR 1604-C + Alphalist (Annual Info Return)
- Audit Trail (full action logging with user, timestamp, before/after)
- Holiday Management (regional, special non-working)

### Section 1.2: User Journey Map
A horizontal timeline/funnel showing how a typical client progresses:

```
Month 1-3: STARTER           Month 4-8: ESSENTIAL          Month 9+: PROFESSIONAL
┌─────────────────┐          ┌─────────────────────┐        ┌──────────────────────────┐
│ Core only        │ ──────▶ │ + Payroll Engine      │ ────▶ │ + Time & Leave/OT         │
│ Employee setup   │          │ Automate computation  │        │ Full workforce management  │
│ Basic portal     │          │ Gov't compliance      │        │ Supervisor visibility      │
└─────────────────┘          └─────────────────────┘        └──────────────────────────┘
```

Below the funnel, show a stat callout:
- "Land and expand model: Average module adoption goes from **2.3 at signup** to **4.7 by month 12**"
- Visualize this as a small animated bar that grows from 2.3 to 4.7 on scroll

### Section 1.3: Feature Dependencies
A clean dependency table/diagram showing which modules REQUIRE other modules:

| Module | Requires | Enhanced by |
|--------|----------|-------------|
| Core | — (always on) | — |
| Payroll Engine | Core | Time (auto-DTR pull), Leave/OT (auto deductions) |
| Time & Attendance | Core | Payroll (auto DTR → payroll) |
| Leave & OT | Core | Payroll (auto deductions), Time (auto undertime) |
| Supervisor Portal | Core | Payroll (team pay view), Leave/OT (approvals) |
| Analytics | Core + Payroll | Time (attendance analytics), Leave/OT (leave analytics) |
| Compliance+ | Core + Payroll | All (richer audit trail, more reports) |

Style this as a visual flow rather than a plain table — use colored connection lines between module pills.

### Section 1.4: Competitive Feature Matrix
A comparison table with checkmarks, partial marks, and X marks:

| Feature | GeNXcript | Sprout Solutions | PayrollHero | GreatDay HR | Manual Excel |
|---------|-----------|-----------------|-------------|-------------|-------------|
| Modular pricing | ✅ | ❌ All-or-nothing | ❌ | ❌ | N/A |
| PH Gov't auto-calc | ✅ | ✅ | ✅ | ⚠️ Partial | ❌ Manual |
| Gov't report gen | ✅ | ✅ | ⚠️ | ⚠️ | ❌ |
| Supervisor portal | ✅ | ⚠️ Basic | ❌ | ⚠️ | ❌ |
| GPS clock-in | ✅ | ✅ | ✅ | ✅ | ❌ |
| Night diff auto | ✅ | ⚠️ | ✅ | ❌ | ❌ |
| 13th month auto | ✅ | ✅ | ✅ | ⚠️ | ❌ Manual |
| Modern UI | ✅ | ⚠️ Dated | ⚠️ | ⚠️ | N/A |
| Audit trail | ✅ | ⚠️ | ❌ | ❌ | ❌ |
| Self-service portal | ✅ | ✅ | ⚠️ | ✅ | ❌ |
| Offline-capable | 🔜 Planned | ❌ | ✅ | ❌ | ✅ |

Use ✅ = green checkmark, ⚠️ = yellow partial, ❌ = red X, 🔜 = blue planned. Style as actual colored icons, not emoji.

Highlight GeNXcript column with a light blue background. Add a row at the bottom: "Starting price" showing ₱2,999/mo vs competitors.

### Section 1.5: Module Completion Status
Show each module with a labeled progress bar:

- 🟢 Core: 95% — "Authentication, employee management, portal — all solid"
- 🔵 Payroll Engine: 90% — "Computation engine complete, report templates need QA"
- 🟡 Time & Attendance: 85% — "DTR + shifts done, geolocation needs field testing"
- 🟠 Leave & OT: 80% — "Core flows done, special leave types need edge case handling"
- 🔴 Supervisor Portal: 75% — "Dashboard live, team payroll view needs permissions polish"
- 🟣 Analytics: 70% — "OT heatmap + payroll comparison done, more dashboards planned"
- ⚫ Compliance+: 60% — "BIR 2316 done, 1604-C in progress, audit trail logging active"

Progress bars should be colored with the module's color. Animate the fill on scroll. Show the percentage number at the right end of each bar.

Below the progress bars, add a summary: "Overall platform completion: **~80%** — Core product is shippable, advanced modules in active development"

---

## TAB 2: 🔧 ENGINEERING — Architecture & Implementation

### Section 2.1: Feature Flag System
Show a code block with the module gating approach:

```python
# companies table — JSONB column
# Default for new companies: ["core"]
# Default for existing companies (migration): all modules enabled

enabled_modules: ["core", "payroll", "attendance", "leave_ot", "supervisor", "analytics", "compliance"]

# Utility function — called in sidebar rendering + page guards
def has_module(module: str) -> bool:
    """Check if current company has a specific module enabled."""
    company = get_current_company()
    return module in company.get("enabled_modules", ["core"])

# Usage in Streamlit sidebar:
if has_module("payroll"):
    st.sidebar.page_link("pages/_payroll_run.py", label="Payroll Run")

# Usage in page render (top of each page file):
if not has_module("attendance"):
    show_upgrade_prompt("Time & Attendance", "Essential")
    st.stop()
```

Style the code block with dark background (#1e293b), syntax-highlighted (color keywords, strings, comments differently). Use JetBrains Mono font.

Below the code block, add a callout box:
> **Key decision**: Module gating is UI-level only. We do NOT restrict at the database or API level. If a company disables a module, their data remains intact — they just can't access the UI. This simplifies implementation and means re-enabling a module instantly restores all historical data.

### Section 2.2: Code Architecture — File Mapping
A two-column layout. Left column: module name with color indicator. Right column: file list.

Style as a tree/directory view:

```
genxcript-saas/
├── main.py                          ← 🟢 Core (app entry, sidebar, auth routing)
├── auth.py                          ← 🟢 Core (login, session, RBAC)
├── pages/
│   ├── _company_setup.py            ← 🟢 Core + ⚫ Compliance (holidays section)
│   ├── _employees.py                ← 🟢 Core + 🟠 Leave/OT (leave/OT tabs)
│   ├── _employee_portal.py          ← 🟢 Core (self-service)
│   ├── _preferences.py              ← 🟢 Core (settings)
│   ├── _payroll_run.py              ← 🔵 Payroll + ⚫ Compliance (gov't reports)
│   ├── _payroll_comparison.py       ← 🔵 Payroll + 🟣 Analytics
│   ├── _dtr.py                      ← 🟡 Time & Attendance
│   ├── _dashboard.py                ← 🔴 Supervisor + 🟣 Analytics
│   └── _ot_heatmap.py               ← 🟣 Analytics
```

Use colored dots/badges next to each module tag. The file tree should use monospace font and have subtle connecting lines.

Add a note: "Some files serve multiple modules (e.g., `_payroll_run.py` handles both Payroll computation and Compliance report generation). The feature flag checks happen within the file to show/hide relevant sections."

### Section 2.3: Database Schema by Module
Show tables grouped by module in a visual schema diagram. Use colored header bars matching module colors.

**🟢 Core Tables**
- `companies` — id, name, settings, **enabled_modules** (JSONB), created_at
- `employees` — id, company_id, first_name, last_name, position, department, status
- `employee_profiles` — id, employee_id, sss_no, philhealth_no, pagibig_no, tin, bank_info
- `user_company_access` — id, user_id, company_id, role (admin/supervisor/employee)
- `shifts` — id, company_id, name, start_time, end_time, break_minutes

**🔵 Payroll Engine Tables**
- `pay_periods` — id, company_id, start_date, end_date, status (draft/processing/finalized)
- `payroll_entries` — id, pay_period_id, employee_id, gross, deductions (JSONB), net, computed_at
- `sss_rates` — effective_date, salary_bracket, employee_share, employer_share
- `philhealth_rates` — effective_date, premium_rate, salary_floor, salary_ceiling
- `pagibig_rates` — effective_date, employee_rate, employer_rate
- `tax_rates` — effective_date, bracket_min, bracket_max, fixed_tax, rate_over

**🟡 Time & Attendance Tables**
- `time_logs` — id, employee_id, clock_in, clock_out, source (manual/gps/biometric), location_data (JSONB)

**🟠 Leave & OT Tables**
- `leave_requests` — id, employee_id, leave_type, start_date, end_date, status, approved_by
- `leave_balances` — id, employee_id, leave_type, year, entitled, used, remaining
- `ot_requests` — id, employee_id, date, hours, reason, status, approved_by
- `leave_entitlement_templates` — id, company_id, name, leave_types (JSONB)

**⚫ Compliance+ Tables**
- `audit_logs` — id, company_id, user_id, action, entity_type, entity_id, before (JSONB), after (JSONB), timestamp
- `holidays` — id, company_id, name, date, type (regular/special/regional), is_nationwide

Show each group as a card with the module color as the top border. Inside each card, list tables with their key columns. Use monospace font for table/column names.

### Section 2.4: Module Gating Strategy
A three-layer diagram showing where gating happens:

```
Layer 1: SIDEBAR NAVIGATION
├── Hide page links for disabled modules
├── Check: has_module() in main.py sidebar builder
└── Effect: User never sees the nav item

Layer 2: PAGE RENDER GUARD
├── Top of each page file: if not has_module(), show upgrade prompt
├── Upgrade prompt shows: module name, features they'd get, CTA to contact admin
└── Effect: Even if URL is accessed directly, content is blocked

Layer 3: DATABASE / API
├── NO restriction at this level
├── Data remains intact when module is disabled
├── Re-enabling module = instant access restoration
└── Reason: Simplicity + data preservation + faster module switching
```

Style as a layered/stacked diagram with each layer as a card, getting slightly narrower (like a pyramid or funnel).

### Section 2.5: Migration Plan
A step-by-step migration card:

1. **Add column**: `ALTER TABLE companies ADD COLUMN enabled_modules JSONB DEFAULT '["core"]';`
2. **Backfill existing**: `UPDATE companies SET enabled_modules = '["core","payroll","attendance","leave_ot","supervisor","analytics","compliance"]';` — All existing companies get all modules (no disruption)
3. **Add has_module() utility**: Single function in a shared utils module
4. **Gate sidebar**: Wrap each page_link in has_module() check (low-risk, high-impact)
5. **Gate pages**: Add module guard to top of each page file
6. **Add upgrade prompts**: Design the "upgrade to unlock" component
7. **Admin panel**: Add module toggle to company settings (admin only)

Show as a numbered timeline with each step as a card. Estimate effort next to each: "~30 min", "~1 hour", "~2 hours", etc. Total estimated implementation: **~2 days** for a developer.

### Section 2.6: Technical Considerations
Three info cards side by side:

**Caching**
- Module-aware cache invalidation
- Don't preload payroll data if payroll module is disabled
- Cache `enabled_modules` per session (refresh on company settings change)
- Impact: Reduced memory for Starter-tier companies

**Performance**
- JSONB `enabled_modules` check: <1ms (in-memory after first load)
- No additional DB queries — module flags loaded with company record
- Sidebar render: adds ~5ms for 7 module checks (negligible)
- Page guard: single boolean check, no performance impact

**Scalability**
- Multi-tenant isolation already in place (all queries filtered by company_id)
- Module flags are per-company, stored in company record
- No cross-tenant module interference
- Adding new modules: just add a string to the enum, create the page, add sidebar check
- Future: module versioning (e.g., "analytics_v2") for gradual rollouts

---

## TAB 3: 💰 SALES — Pricing, Upsells, Objections

### Section 3.1: Pricing Tiers
Show 4 pricing cards side by side (responsive: stack on mobile). The "Professional" card should be visually elevated with a "MOST POPULAR" badge and a subtle border glow.

**STARTER — ₱2,999/mo**
- Up to 20 employees
- Modules: Core only
- Target: Small businesses currently using manual payroll
- "Get organized first, automate later"
- CTA-style bottom: "Entry point"

**ESSENTIAL — ₱5,999/mo**
- Up to 50 employees
- Modules: Core + Payroll Engine
- Target: SMEs doing in-house payroll computation
- "Automate payroll, stay compliant"
- CTA-style bottom: "Most common starting tier"

**PROFESSIONAL — ₱9,999/mo** ⭐
- Up to 100 employees
- Modules: Core + Payroll + Time & Attendance + Leave/OT
- Target: Companies with shift workers, field staff
- "Full workforce management"
- CTA-style bottom: "Best value"
- MOST POPULAR badge, elevated card with shadow

**ENTERPRISE — ₱14,999/mo**
- Unlimited employees
- Modules: All 7 modules
- Target: Full-featured, multi-department companies
- "Complete platform with analytics & compliance"
- CTA-style bottom: "Full platform"

Below the cards, a note: **Per-employee add-on**: ₱50-100/head/month after tier employee threshold. Example: Essential tier with 65 employees = ₱5,999 + (15 × ₱75) = ₱7,124/mo.

### Section 3.2: Revenue Calculator
An interactive widget with sliders and auto-calculated results.

**Inputs** (range sliders with number display):
- Starter clients: 0-200 (default: 10)
- Essential clients: 0-200 (default: 25)
- Professional clients: 0-200 (default: 40)
- Enterprise clients: 0-100 (default: 15)

**Outputs** (update in real-time as sliders move):
- Monthly Recurring Revenue (MRR): calculated sum
- Annual Recurring Revenue (ARR): MRR × 12
- Average ARPU: MRR / total clients
- Blended margin: weighted average

Show a highlighted callout that updates: "**[X] total clients = ₱[MRR]/mo = ₱[ARR]/year**"

Example default: "90 clients = ₱649,860/mo = ₱7.8M/year"

Use large, bold numbers for the outputs. JetBrains Mono font for the currency figures.

### Section 3.3: Upsell Playbook
A decision tree / flowchart showing trigger events for tier upgrades. Style as a vertical flow with colored connectors.

**Starter → Essential**
- Trigger: "Client asks about automating payroll computation"
- Trigger: "Client mentions BIR/SSS filing headaches"
- Talk track: "You're manually computing for [X] employees — that's [Y] hours/month. Essential automates this completely."

**Essential → Professional**
- Trigger: "Client hires shift workers or field staff"
- Trigger: "Client asks about tracking attendance or leave"
- Talk track: "Your team is growing. Pro gives you real-time attendance, automated leave tracking, and OT management."

**Professional → Enterprise**
- Trigger: "Supervisors want team visibility"
- Trigger: "Management asks for analytics or reports"
- Talk track: "Your supervisors need their own dashboard. Enterprise gives them team oversight plus analytics for data-driven decisions."

**Any Tier → Compliance+ Add-on**
- Trigger: "BIR filing season approaching (January-April)"
- Trigger: "Client mentions audit concerns"
- Talk track: "Filing season is coming. Compliance+ auto-generates your BIR 2316, 1604-C, and Alphalist. Plus full audit trail for peace of mind."

### Section 3.4: Objection Handling Cards
5 flip cards in a grid. Front shows the objection, back shows the response. Click/tap to flip (CSS 3D transform).

**Card 1 — Front**: "It's too expensive"
**Card 1 — Back**: "A payroll clerk costs ₱15-25K/month. Our Pro tier at ₱9,999 handles everything they do — plus compliance, reporting, and zero errors. You're saving ₱5-15K/month minimum, and that scales as you grow."

**Card 2 — Front**: "We already use Excel"
**Card 2 — Back**: "Excel payroll has a 12-18% error rate per study. One wrong SSS computation can mean penalties. Plus, you're spending 8-12 hours per pay period on manual work. GeNXcript does it in minutes with government-verified rates."

**Card 3 — Front**: "We use Sprout / PayrollHero already"
**Card 3 — Back**: "Great — you understand the value of payroll software. With us, you only pay for what you use. No ₱15K/mo minimum for features you don't need. Plus, our modular approach means you can start small and add modules as you grow. No vendor lock-in."

**Card 4 — Front**: "We only need payroll, nothing else"
**Card 4 — Back**: "Perfect — our Essential tier is exactly that. ₱5,999/mo for payroll computation + government compliance. When you're ready for attendance or leave tracking, just flip a switch. Your data's already there."

**Card 5 — Front**: "Can we try it first?"
**Card 5 — Back**: "Absolutely. 30-day free trial on any tier, no credit card required. We'll even help you set up your first payroll run. Most clients see the value within the first pay cycle."

### Section 3.5: Client Persona Profiles
4 persona cards in a 2×2 grid. Each card has:
- Persona avatar (CSS-generated initials circle)
- Company name, employee count, industry
- Pain points (bulleted)
- Recommended tier with reasoning
- Estimated monthly spend

**Persona 1: Maria's Café**
- 15 employees, food & beverage
- Pain: Manual timekeeping on paper, late salary payments, no payslips
- Recommended: Starter (₱2,999/mo)
- "Start with Core to digitize employee records. Upgrade to Essential when ready to automate payroll."

**Persona 2: TechStartup Inc.**
- 45 employees, IT/software
- Pain: Excel payroll taking 2 days per cycle, SSS/BIR computation errors, no employee self-service
- Recommended: Essential (₱5,999/mo)
- "Payroll automation is their immediate need. Will likely upgrade to Pro within 6 months as they scale."

**Persona 3: ManufacturePH Corp**
- 120 employees, manufacturing
- Pain: Shift scheduling chaos, OT disputes, no attendance tracking, supervisor needs team view
- Recommended: Professional (₱9,999/mo + ₱1,500 overage = ₱11,499/mo)
- "Shift workers + OT management is the core need. Supervisor portal is a natural add-on."

**Persona 4: BPO Solutions Group**
- 300 employees, business process outsourcing
- Pain: Need analytics for workforce optimization, BIR compliance for large headcount, night differential tracking
- Recommended: Enterprise (₱14,999/mo + per-head overage)
- "Full platform. Analytics for NSD monitoring, compliance for large-scale BIR filing, supervisor portal for team leads."

### Section 3.6: Competitive Pricing Comparison
A table comparing per-employee monthly cost across platforms:

| | GeNXcript | Sprout Solutions | PayrollHero | GreatDay HR | Manual (Clerk) |
|---|---|---|---|---|---|
| 20 employees | ₱150/head | ₱200-300/head | ₱250/head | ₱175/head | ₱750-1,250/head |
| 50 employees | ₱120/head | ₱180-250/head | ₱200/head | ₱150/head | ₱400-600/head |
| 100 employees | ₱100/head | ₱150-200/head | ₱175/head | ₱130/head | ₱250-350/head |
| 200 employees | ₱75/head | ₱120-180/head | ₱150/head | ₱110/head | ₱150-200/head |
| Modular pricing | ✅ Yes | ❌ No | ❌ No | ❌ No | N/A |
| Free trial | 30 days | 14 days | Demo only | 14 days | N/A |

Highlight the GeNXcript column. Add a footnote: "GeNXcript per-head cost decreases as company size increases. Competitors charge flat per-head regardless of tier."

---

## TAB 4: 📊 FINANCE — Revenue Model & Projections

### Section 4.1: Unit Economics Dashboard
6 metric cards in a 3×2 grid. Each card has a large number (animated counter on scroll), label, and context line.

- **ARPU**: ₱7,000-15,000/mo per company — "Blended across tiers, weighted toward Essential/Pro"
- **CAC**: ₱15,000 — "Digital marketing + demo calls + onboarding"
- **LTV**: ₱504,000 — "36-month avg retention × ₱14,000 avg ARPU"
- **LTV:CAC**: 33.6x — "Industry benchmark: 3x+ is healthy. We're 10x above that."
- **Gross Margin**: 85%+ — "Cloud SaaS, minimal COGS (Supabase + compute)"
- **Payback Period**: 1.1 months — "CAC recovered in first billing cycle"

Add a subtle green "healthy" indicator on cards where our metric beats industry benchmark. Use animated number counters that roll up when the section scrolls into view.

Below the metrics, add: **Monthly churn target: <3%** — "Each module adds switching cost. Average module count of 4.7 means high stickiness."

### Section 4.2: Revenue Waterfall
A horizontal stacked bar or waterfall chart (CSS-only) showing revenue composition:

- Base subscription: **80%** of revenue — "Monthly SaaS fees across all tiers"
- Per-employee overage: **12%** — "Companies exceeding tier employee limits"
- Onboarding/training: **5%** — "₱25-50K one-time fees for setup assistance"
- Custom development: **3%** — "Bespoke report templates, integrations"

Show as colored horizontal bars with labels and percentages. Use module-like colors (blues and grays for a professional look).

### Section 4.3: 3-Year Financial Model
A CSS-drawn bar chart with 3 grouped bars per year, plus a line overlay for cumulative profit.

**Year 1**
- Clients: 50
- ARR: ₱4.2M
- Costs: ₱6.2M
- Net: -₱2M (investment phase)
- Bar color: red-tinted

**Year 2**
- Clients: 200
- ARR: ₱16.8M
- Costs: ₱14M
- Net: +₱2.8M (breakeven + margin)
- Bar color: yellow-tinted

**Year 3**
- Clients: 500
- ARR: ₱42M
- Costs: ₱27M
- Net: +₱15M (profitable scale)
- Bar color: green-tinted

Show a line connecting the net figures across years, clearly showing the hockey stick from loss to profit. Add annotations at key inflection points.

### Section 4.4: Module Revenue Attribution
A CSS-only donut/ring chart showing which modules drive upgrade revenue:

- 🔵 Payroll Engine: 40% — "Primary reason companies upgrade from Starter"
- 🟡 Time & Attendance: 25% — "Second most requested feature"
- 🟣 Analytics & Insights: 15% — "Enterprise differentiator"
- 🔴 Supervisor Portal: 10% — "Key for companies with team leads"
- ⚫ Compliance+: 10% — "Seasonal driver (BIR filing)"

Show as a donut chart with colored segments. Legend on the right side. Each segment should have a hover tooltip showing the detail.

### Section 4.5: Cost Structure
A CSS pie chart or horizontal bar breakdown:

- Development: **45%** — "2-3 full-time developers, contractor support"
- Sales & Marketing: **25%** — "Digital ads, content, demo team"
- Operations: **12%** — "Support, onboarding, admin"
- Cloud Infrastructure: **8%** — "Supabase, hosting, CDN, monitoring"
- Reserve: **10%** — "Buffer for unexpected costs, opportunity fund"

### Section 4.6: Break-even Analysis
A CSS line chart showing two lines:
- **Cumulative Revenue** (blue, rising curve)
- **Cumulative Costs** (red, rising but slower)

The lines cross at approximately **month 18** / **~150 clients**. Mark this intersection with a highlighted dot and annotation: "Break-even: Month 18, ~150 clients"

Add context below: "Conservative estimate assuming 10-12 new clients/month by month 12. Accelerates with referral program and partnership channels."

### Section 4.7: Pricing Sensitivity
A simple comparison showing impact of ±20% pricing adjustment:

| Scenario | Avg Price | Year 3 Clients (est.) | Year 3 ARR | Impact |
|---|---|---|---|---|
| -20% pricing | ₱6,400/mo | 600 (+20% volume) | ₱46M | Higher volume, thinner margin |
| Current pricing | ₱8,000/mo | 500 | ₱42M | Balanced |
| +20% pricing | ₱9,600/mo | 400 (-20% volume) | ₱38.4M | Lower volume, higher per-client value |

Add insight: "Current pricing is the sweet spot. Lower pricing attracts price-sensitive clients with higher churn. Higher pricing reduces volume without proportional margin improvement."

### Section 4.8: Investment Requirements
A structured breakdown:

**Seed Round: ₱5-10M** (18 months runway)

Use of funds (visual horizontal bars):
- Product Development: 50% (₱2.5-5M) — "Complete remaining modules, QA, security hardening"
- Sales & Marketing: 25% (₱1.25-2.5M) — "Client acquisition, brand awareness, demo team"
- Operations: 15% (₱0.75-1.5M) — "Support team, onboarding, office"
- Legal & Compliance: 5% (₱0.25-0.5M) — "BIR registration, data privacy, contracts"
- Reserve: 5% (₱0.25-0.5M) — "Contingency"

**Path to profitability**: Self-sustaining by month 18 with 150+ clients. Seed round provides runway through break-even. No Series A needed if growth targets hit.

---

## FOOTER

A simple footer across all tabs:

```
GeNXcript Payroll — Internal Team Document — March 2026
Confidential — Do not distribute outside the core team
```

Style: centered, var(--text-secondary), small font, top border.

---

## TECHNICAL IMPLEMENTATION NOTES

### JavaScript Requirements
1. **Tab switching**: Toggle `.active` class on tab buttons and content panels. Use CSS transitions for fade effect (opacity 0→1, transform translateY(10px)→0 over 0.3s).
2. **Module highlight linking**: Click handler on module pills that adds `.highlighted` class to all elements with a matching `data-module` attribute across ALL tab panels.
3. **Revenue calculator**: Event listeners on range inputs, real-time DOM update for calculated fields. Format numbers with peso sign and commas.
4. **Flip cards**: Click toggles `.flipped` class. CSS handles the 3D rotation (rotateY 180deg) with backface-visibility hidden.
5. **Animated counters**: IntersectionObserver triggers countUp animation (increment from 0 to target over 1.5s using requestAnimationFrame).
6. **Scroll animations**: IntersectionObserver on `.animate-in` elements, add `.visible` class when 20% in viewport.
7. **Print styles**: `@media print` shows all tab content stacked, removes interactive elements, forces black text on white.

### CSS Charts (No Libraries)
All charts must be pure CSS — no Chart.js, no SVG libraries, no canvas.
- **Progress bars**: `div` with percentage width, colored background, border-radius
- **Donut chart**: `conic-gradient()` on a circular div with a white center circle overlay
- **Bar charts**: Flexbox or Grid with `div` bars, height set by CSS custom properties
- **Line charts**: SVG polyline with CSS styling (inline SVG is acceptable)
- **Pie chart**: `conic-gradient()` on a circular div

### Responsive Breakpoints
- Desktop: >1024px — full layout, side-by-side cards
- Tablet: 768-1024px — 2-column grids become single column where needed
- Mobile: <768px — single column, stacked cards, tabs become scrollable horizontal

### Accessibility
- Tab navigation keyboard accessible (arrow keys to switch tabs)
- Flip cards: also toggle on Enter/Space key
- Color is never the only indicator — always paired with text labels
- Focus visible outlines on interactive elements
