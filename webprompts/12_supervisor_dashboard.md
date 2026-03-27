Design System: "Tactile Sanctuary" — High-End Editorial Minimalism
Font: Plus Jakarta Sans (weights 300–800). Use it for everything.
Theme: Light mode only.
Colors:
  - Primary: #005bc1 | Primary light: #3d89ff
  - Surface (page bg): #f8f9fa
  - Card (white): #ffffff
  - Surface low: #f1f4f5
  - Surface container: #ebeef0
  - Amber accent: #fbbc05 (for highlight cards)
  - Green accent: #89fa9b (for success states)
  - Text primary: #2d3335 (never pure black)
  - Text secondary: #5a6062
  - Error: #a83836

Rules:
  - NO 1px borders anywhere. Separate sections using background color shifts only.
  - Card radius: 2rem. Pill/button radius: 9999px.
  - Shadow (ambient only): 0px 20px 40px rgba(45,51,53,0.06)
  - Primary CTA: gradient fill linear-gradient(135deg, #005bc1 0%, #3d89ff 100%), white text, pill shape.
  - Navigation header: glassmorphism — rgba(255,255,255,0.7) + backdrop-filter blur(20px), fixed top.
  - Left sidebar: 240px, white/slate-50 bg, pill-shaped active nav item in blue-50 with #005bc1 text.
  - Page bg is #f8f9fa. Cards sit on top as white (#ffffff) rounded tiles.
  - Output: full HTML file using Tailwind CSS CDN + Material Symbols Outlined icons.

---

PAGE: SUPERVISOR TEAM DASHBOARD (ADP Manager Tool — Philippine Market)

Build a supervisor/manager dashboard for "GeNXcript Payroll" — a Philippine payroll SaaS. This is what a team supervisor (not admin) sees after login. They manage 5–15 direct/indirect reports. They cannot see company-wide financial data — only their team. Inspired by ADP's Manager Tool adapted for Philippine labor law.

Include fixed glassmorphism top nav: logo "GeNXcript" left, right side: role badge pill "Supervisor" in purple (#7c3aed bg, white text, 9999px radius), user name "Victoria Garcia", avatar circle.

Left sidebar (240px, fixed):
  - "GeNXcript" brand bold blue top, "Supervisor Portal" caption gray below.
  - Nav items (pill shape, full width): Team Dashboard (active, blue-50 bg), Attendance, Calendar, Preferences.
  - Only 4 items — supervisors have limited page access.
  - Icons from Material Symbols for each item.

Main content (margin-left 240px, padding 3rem):

  Section 1 — Editorial header:
    - "Good morning, Victoria." in 1.2rem semibold #2d3335.
    - Subtitle: "You have **5 team member(s)** reporting to you." in #5a6062, bold the number.
    - Right side: "March 26, 2026" bold + "11:53 AM" smaller below.

  Section 2 — Bento grid (CSS grid, 3 columns equal, gap 1.5rem):
    Row 1 (3 cards, equal height ~180px):

      Card 1: "YOUR TEAM" (white card, 2rem radius, ambient shadow).
        - "YOUR TEAM" label small uppercase tracking-widest #005bc1.
        - 5 team member mini rows: each has a 24px circle avatar (initials, blue-100 bg, blue-600 text), name bold 11px, position gray 9px. Show 5, then "+2 more" in gray if overflow.
        - Compact vertical list, no extra padding.

      Card 2: Amber accent card (#fbbc05 bg, 2rem radius).
        - Big number "5" in 3rem black extrabold top.
        - "Team Members" bold black below.
        - "Direct & indirect reports" small rgba(0,0,0,0.55).
        - Hidden button: "View Attendance →" (wired via JS on card click).

      Card 3: "PENDING APPROVALS" (white card, 2rem radius).
        - "PENDING APPROVALS" label + yellow pill badge "3" top-right.
        - 2 rows:
          Row 1: 🏖 emoji in amber-100 circle, "2 Leave Requests", "Awaiting your approval" gray.
          Row 2: ⏰ emoji in violet-100 circle, "1 OT Request", "Awaiting your approval" gray.
        - If zero pending: show ✅ centered + "All Clear" + "No pending requests" gray.

    Right sidebar column (1/4 width): sits beside row 1 on larger screens.
      - "Reminders" card: green-bordered, checkmark icon, "No Pending Approvals" or pending count.
      - "Alerts" card: green-bordered "ALL CLEAR" or deadline warnings.

  Section 3 — Tab bar (5 tabs, pill-shaped, horizontal scroll on mobile):
    🕐 Timekeeping | 🏖 Leave & Benefits | 💰 Statutory (Read-only) | 📁 Team Records | 🔜 Coming Soon

  Tab 1: "🕐 Timekeeping" — Two-column layout:
    Left column:
      "DTR Exceptions" heading (14px bold) + "Last 3 workdays" gray caption.
      List of exception cards (white, thin border, 10px radius, 6px margin-bottom):
        Each: Employee name (12px bold) + date (10px gray) left, issue pills right.
        Issue pills: "No Time In" (red-100 bg, red-800 text), "Late 23min" (amber-100 bg, amber-800 text),
        "NSD 2.5h" (pink-100 bg, pink-800 text). Font 9px bold, 9999px radius.
        Show 6–8 entries. If none: green success card "✅ No DTR Exceptions — All team members have complete logs."

      Below: "Holiday Pay Validator" heading + "Last 30 days" caption.
      Cards showing employees who worked on holidays:
        Name + hours left, pill badge right: "REGULAR 200%" (red-100/red-800) or "SPECIAL 130%" (amber-100/amber-800).
        Subtitle: holiday name + date.

    Right column:
      "OT Authorization" heading.
      If pending: "⚠ 3 PENDING APPROVAL" amber text.
      Pending OT cards (amber-50 bg, amber-200 border):
        Name (12px bold) + hours (amber-600 bold) right.
        Date + time range below (10px gray).
        Reason italic 10px gray.
      Below pending: "RECENT" label gray, then approved/rejected OT cards:
        Compact rows: name + date + hours, status pill (green "APPROVED" or red "REJECTED").

  Tab 2: "🏖 Leave & Benefits" — Two-column [3:2] layout:
    Left (wider):
      "Team Leave Balances" heading.
      Grid table: columns "Employee | VL | SL | CL".
      Header row: 10px uppercase gray.
      Data rows (white bg, thin border, 8px radius):
        Name left, then for each leave type: big remaining number (green if >3, amber if 1-3, red if 0)
        + "/total" in small gray. E.g., "12/15" means 12 remaining of 15.
      Show all team members.

      Below: "Special Leaves (Statutory)" heading.
      Cards for Maternity (105d) / Paternity (7d) / Solo Parent (7d):
        Name + leave type label + status pill (approved/pending/rejected).
        Date range below.

    Right (narrower):
      "Pending Leave Requests" heading.
      Cards (amber-50 bg, amber-200 border):
        Name + leave type pill (VL=blue, SL=pink, CL=indigo) with days count.
        Date range + reason italic.
      If none: green "✅ No Pending Leaves" card.

  Tab 3: "💰 Statutory (Read-only)" — Full width:
    Caption: "SHOWING DATA FROM: 2026-03-01 → 2026-03-15" + status pill "FINALIZED".

    4 summary metric cards in a row (white, 12px radius, centered):
      "SSS Total" #2563eb | "PhilHealth Total" #059669 | "Pag-IBIG Total" #d97706 | "Withholding Tax" #dc2626.
      Each: label 10px uppercase gray, value 18px extrabold in agency color.

    Below: Detail grid table. Columns: "Employee | SSS (EE/ER) | PhilHealth | Pag-IBIG | WHT".
    Header: 9px uppercase gray. Data rows: white bg, thin border, 8px radius.
    SSS shows EE amount in blue + "/ER amount" in gray. Others are totals.
    WHT in red. All values in ₱ format.

  Tab 4: "📁 Team Records" — Full width:
    "Digital 201 File — Team Directory" heading + subtitle "Employment records, government IDs, and contact information for your direct & indirect reports."

    Employee record cards (white, 12px radius, 14px padding, 6px margin-bottom):
      Left: 36px circle avatar (initials, blue-100/blue-600).
      Right of avatar:
        Row 1: Name (13px bold) + employee_no (9px gray) + employment type pill (REGULAR=green, PROBATIONARY=amber, CONTRACTUAL=blue).
        Row 2: Position • Department • Hired 2024-06-01 (11px gray).
        Row 3: Government ID dots — filled circle (●) in agency color if present, empty (○) in gray if missing.
        Labels: "● SSS" blue, "● PH" green, "● PI" amber, "● TIN" red. 9px font.

  Tab 5: "🔜 Coming Soon" — Full width:
    "Upcoming Features" heading + "These modules are on the development roadmap and will be available in future updates."

    3-column grid of placeholder cards (dashed border #cbd5e1, bg gradient slate-50→slate-100, 16px radius, center-aligned, opacity 0.75, min-height 160px):

    Card 1: ⚖ icon 28px, "Disciplinary Action Hub" 13px bold slate-600,
      "DOLE Due Process compliance — Notice to Explain, Two-Notice Rule workflow, hearing records." 10px slate-400.
      Bottom pill: "IN DEVELOPMENT • Phase 6B-1" (slate-200 bg, slate-500 text, 9px bold).

    Card 2: 🏦 "Loan Amortization View" — SSS/Pag-IBIG salary loan tracking. "Phase 5A".

    Card 3: 📋 "BIR 2316 Digital Sign-off" — Annual tax certificate acknowledgment. "Phase 6B-2".

    Card 4: 🏥 "HMO & Group Insurance" — Team enrollment, dependents, MBL coverage. "Phase 6B-3 (Optional)".

    Card 5: 📅 "Probation & Regularization" — 5th-month eval alerts, regularization workflow. "Phase 6B-4 (Optional)".

    Card 6: 📈 "Transfer & Promotion" — Salary grade history, promotion letters. "Phase 6B-5".

    Card 7: 🕐 "OT Type Distinction" — Regular/Rest Day/Holiday OT categorization. "Phase 5E".

---

IMPORTANT DESIGN NOTES:
  - This is a SUPERVISOR view — no company-wide financial data visible (no Gross Pay, Net Pay, Employer Cost cards).
  - The supervisor can only see their team's data (5-15 employees who report to them).
  - Statutory tab is explicitly "Read-only" — no edit buttons or forms.
  - Coming Soon cards use dashed borders and reduced opacity to clearly signal "not yet available."
  - The tab bar should feel like a native app — smooth transition between tabs.
  - Use emoji icons for tabs (not Material Symbols) for consistency with the existing codebase.
  - All monetary values use Philippine Peso (₱) symbol.
  - Government agency abbreviations: SSS, PhilHealth, Pag-IBIG, BIR.
