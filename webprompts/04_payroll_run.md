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

PAGE: PAYROLL RUN

Build a Payroll Run page for "GenXcript Payroll" (Philippine payroll SaaS).

Same top nav + sidebar. "Payroll Run" active in sidebar.

Main content:
  Editorial page title: "Payroll Run"
  Subtitle: "Mar 16–31, 2026 · Semi-monthly"

  Status bar (white card, radius 2rem, horizontal flex):
    "Period: Mar 16–31, 2026" | Status pill "DRAFT" (gray rounded-full) |
    "11 employees" | "Submit for Review" blue outline pill button right |
    "Finalize" gradient pill button right.

  Employee accordion list — for each employee an expandable card
  (white, radius 1.5rem, ambient shadow, margin-bottom 0.75rem):
    Collapsed state (visible always):
      Employee avatar + name bold left | "₱28,450 gross" right | status dot green.
      Chevron icon to expand.
    Expanded state (3-column earnings layout inside card, bg #f8f9fa, radius 1rem, padding 1.5rem):
      Left column "Earnings":
        - Basic Pay: ₱25,000
        - Overtime Pay: ₱1,200
        - Night Differential: ₱350
        - Allowances: ₱500
        Each row: label #5a6062 left, amount bold #2d3335 right.
        Total row: "Gross Earnings" bold, amount bold #005bc1, slight top spacing.
      Center column "Deductions":
        - SSS: ₱1,350
        - PhilHealth: ₱625
        - Pag-IBIG: ₱200
        - Withholding Tax: ₱2,100
        - Absent Deduction: ₱0
        Total deductions in #a83836.
      Right column "Summary" (centered):
        - "Gross Pay" label small gray, amount 2rem bold #005bc1
        - "Deductions" label, amount #a83836
        - "NET PAY" label uppercase, amount 2.5rem extrabold gradient text (#005bc1 to #3d89ff)
        - "DTR Insights" amber pill (expandable): shows NSD Hrs, OT Hrs from attendance data.

  Show 4 employees (2 collapsed, 1 expanded, 1 collapsed).

  Bottom totals strip (white card, radius 2rem, 3 columns):
    "Total Gross: ₱284,500" | "Total Deductions: ₱48,200" | "Net Payroll: ₱236,300" (bold blue)
    + "Download All Payslips" gradient button right.
