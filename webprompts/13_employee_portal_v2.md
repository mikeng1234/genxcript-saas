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
  - Page bg is #f8f9fa. Cards sit on top as white (#ffffff) rounded tiles.
  - Output: full HTML file using Tailwind CSS CDN + Material Symbols Outlined icons.

---

PAGE: EMPLOYEE SELF-SERVICE PORTAL (Full Redesign — 7 Tabs)

Build a comprehensive Employee Self-Service Portal for "GeNXcript Payroll" — a Philippine payroll SaaS.
This is what employees see after logging in. It is NOT the admin view. Design it to feel like a personal
finance / HR app (think: GCash meets ADP employee portal).

No sidebar — this is a single-page portal with tab navigation (similar to a mobile app).

Top bar (fixed glassmorphism):
  Left: GeNXcript logo.
  Center: Company name "Black Cat Studios".
  Right: Employee avatar circle (48px, photo or initials "VG" in blue-100/blue-700),
    "Victoria Garcia" name, "PTC-028 · Marketing" caption below.

---

## TAB BAR (7 tabs, horizontal, pill-shaped active state)
Dashboard | My Profile | My Payslips | My Time & Leave | My Documents | People | Preferences

---

## TAB 1: Dashboard (Home)
The employee's personal homepage — quick access to everything important.

Section 1 — Greeting header:
  - "Good morning, Victoria." 1.5rem semibold.
  - "PTC-028 · Marketing Associate · Regular" subtitle in gray.
  - Right side: current date + time.

Section 2 — 3-column bento cards:
  Card 1 (white, shadow-soft): "Next Payslip"
    - "UPCOMING" label small uppercase blue.
    - Date "Mar 31, 2026" in 1.5rem bold.
    - "₱18,420.00" net pay amount bold green.
    - Bottom: "View Payslip →" blue text link.

  Card 2 (green #89fa9b bg): "Leave Balance"
    - Big number "12" in 3rem extrabold black.
    - "Vacation days remaining" below.
    - Small: "3 used this year" in darker green.

  Card 3 (amber #fbbc05 bg): "OT This Month"
    - "4.5" in 3rem extrabold black.
    - "Hours approved" below.
    - Small: "2 requests pending" in dark amber.

Section 3 — Clock In/Out Widget (centered, prominent):
  White card, shadow-soft, max-width ~480px, centered:
    - Current time "08:42 AM" in 2.5rem extrabold.
    - Date "Friday, March 20, 2026" smaller gray.
    - Status pill: "Clocked Out" (gray-200 bg, gray-600 text, 9999px radius)
      OR "Clocked In at 8:01 AM" (green-100 bg, green-700 text).
    - "CLOCK IN" — large gradient pill button (full width, 56px height, bold 14px).
      When clocked in, shows "CLOCK OUT" button (red gradient).
    - Below button row: 📷 "Take Snapshot" + 📍 "Location: Office HQ (24m)" small gray.
    - Divider line.
    - "Today's Log" section: compact rows:
      "IN: 8:01 AM · OUT: — · Break: 12:00–1:00 PM"
    - "Yesterday" collapsed section: "IN: 7:58 AM · OUT: 5:03 PM · 8.08h worked"

Section 4 — 2-column bottom cards:
  Left: "Recent Leave Requests" (white, shadow-soft):
    3 rows — each: leave type pill (VL=blue-100/blue-700, SL=pink-100/pink-700, CL=indigo-100/indigo-700),
    date range, days count, status pill (Pending=amber, Approved=green, Rejected=red).
    Bottom: "File New Leave" gradient pill button.

  Right: "Recent OT Requests" (white, shadow-soft):
    3 rows — each: date, time range, hours, reason (truncated), status pill.
    Bottom: "File OT Request" gradient pill button.

---

## TAB 2: My Profile
Personal information editor — the employee's digital 201 file.

2-column layout:

Left column (wider):
  Card 1: "Personal Information" (white, shadow-soft):
    - Photo upload circle (80px) top-left.
    - Full name, date of birth, sex, civil status, nationality, religion.
    - All fields editable with text inputs / dropdowns.
    - "Save Changes" gradient pill button.

  Card 2: "Contact Information":
    - Mobile, home phone, work phone, personal email.
    - Facebook, LinkedIn links.

  Card 3: "Present Address":
    - Street, barangay, city, province, zip code fields.

  Card 4: "Permanent Address":
    - Checkbox "Same as present address" — if checked, fields disabled.
    - Same address fields.

Right column (narrower):
  Card: "Employment Details" (read-only, surface-low bg):
    - Employee No: PTC-028
    - Position: Marketing Associate
    - Department: Marketing
    - Employment Type: Regular (green pill)
    - Date Hired: 2024-06-01
    - Supervisor: Maria Santos
    - Schedule: Standard 8-5 (Mon-Fri)

  Card: "Government IDs" (read-only):
    - SSS: 34-1234567-8 (dot indicator green if present)
    - PhilHealth: 01-234567890-1
    - Pag-IBIG: 1234-5678-9012
    - BIR TIN: 123-456-789-000

  Card: "Emergency Contact":
    - Name, relationship, phone, address.

  Card: "Education":
    - Degree, school, year graduated.

---

## TAB 3: My Payslips
Payslip viewing and PDF download.

Top: Period selector dropdown + "Download PDF" gradient pill button.

Payslip card (white, shadow-soft, full width):
  Header: "Payslip — March 1-15, 2026" bold + "Payment Date: Mar 20, 2026" right.

  3-column summary bar (colored accent cards):
    "Gross Pay ₱25,000.00" (blue accent) | "Deductions ₱6,580.00" (red accent) | "Net Pay ₱18,420.00" (green accent, larger font).

  2-column detail below:
    Left: "EARNINGS" table
      - Basic Pay: ₱25,000.00
      - Overtime: ₱0.00
      - Night Differential: ₱0.00
      - Holiday Pay: ₱0.00
      - Allowances (Non-Tax): ₱0.00
      - **Gross Pay: ₱25,000.00** (bold row, blue bg)

    Right: "DEDUCTIONS" table
      - SSS (EE): ₱1,125.00
      - PhilHealth (EE): ₱625.00
      - Pag-IBIG (EE): ₱200.00
      - Withholding Tax: ₱4,630.00
      - SSS Loan: ₱0.00
      - Other Deductions: ₱0.00
      - **Total Deductions: ₱6,580.00** (bold row, red bg)

  Bottom: "NET PAY" large green banner — "₱18,420.00" in 2rem bold.

Below: "Payslip History" — compact table with columns: Period | Gross | Deductions | Net | Status | Action (Download PDF icon).

---

## TAB 4: My Time & Leave
Time tracking, leave requests, OT requests, and DTR corrections — all in sub-tabs.

Sub-tab bar (inside the main tab): Leave Requests | OT Requests | Special Leaves | DTR Corrections

**Sub-tab: Leave Requests**
  "File New Leave" gradient pill button top-right.
  Table/card list: Leave Type | Dates | Days | Reason | Status | Filed Date.
  Each row shows status pill. Pending rows show a "Cancel" ghost button.

**Sub-tab: OT Requests**
  "File OT Request" gradient pill button top-right.
  Table/card list: Date | Time Range | Hours | Reason | Status.

**Sub-tab: Special Leaves**
  Info panel: "Special leaves per Philippine law" with icons for each:
    - 🤱 Maternity Leave (RA 11210) — 105 days
    - 👨‍👧 Paternity Leave (RA 8187) — 7 days
    - 👩‍👧 Solo Parent Leave (RA 8972) — 7 days
  "File Special Leave" button if eligible.
  List of filed special leaves with status.

**Sub-tab: DTR Corrections**
  "Submit Correction" gradient pill button top-right.
  Table: Date | Original In/Out | Requested In/Out | Reason | Status.

---

## TAB 5: My Documents
Document downloads — payslips, certificates, tax forms.

Grid of downloadable document cards (white, shadow-soft, 2rem radius):

  Card 1: "BIR 2316" — Annual tax certificate.
    Icon: 📄. Year selector dropdown. "Download PDF" button.

  Card 2: "Certificate of Employment" — For bank loans, visa applications.
    Icon: 📋. "Generate COE" button.

  Card 3: "Payslip Archive" — All payslips for the year.
    Icon: 💰. Year selector. "Download All" button.

  Card 4: "Attendance Certification" — Coming Soon (dashed border, opacity 0.6).
    Icon: 🕐. "For bank loans and visa applications."

---

## TAB 6: People
Employee directory and org chart for the company.

Two views (toggle buttons): "Directory" | "Org Chart"

**Directory view:**
  Search bar (rounded-full, #ebeef0 bg, search icon).
  Grid of employee cards (3 columns, white, shadow-soft):
    - Avatar circle (48px, initials or photo).
    - Name bold, position gray, department pill.
    - Email + phone below (if shared).
    - Click opens detail card (not a full page — just an expanded view).

**Org Chart view:**
  Interactive D3 org chart (tree layout):
    - Nodes: avatar circle + name + position.
    - Color-coded by department.
    - Zoom + pan controls.
    - Search bar to find and highlight a person.

---

## TAB 7: Preferences
Personal display settings.

White card, shadow-soft:
  - Theme toggle (if available).
  - Date format selector (MM/DD/YYYY, DD/MM/YYYY, YYYY-MM-DD).
  - Notification preferences (email on payslip available, leave approved, etc.) — toggle switches.
  - "Save Preferences" gradient pill button.

---

IMPORTANT DESIGN NOTES:
  - This is an EMPLOYEE portal — no admin functions, no other employee data editing.
  - The clock-in widget is the centerpiece of the Dashboard — make it prominent and app-like.
  - All monetary values in Philippine Peso (₱).
  - Leave types use PH abbreviations: VL (Vacation), SL (Sick), CL (Calamity).
  - Government IDs: SSS, PhilHealth, Pag-IBIG, BIR TIN.
  - The portal should feel modern and personal — like a fintech app, not enterprise HR software.
  - Mobile-responsive design is important (employees access from phones).
  - No sidebar — use tab navigation. Tabs should scroll horizontally on mobile.
