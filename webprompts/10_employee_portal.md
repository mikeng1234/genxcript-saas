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

PAGE: EMPLOYEE SELF-SERVICE PORTAL

Build an Employee Self-Service Portal page for "GenXcript Payroll".

Different sidebar (narrower, employee-only nav, no admin items):
  - Top: employee avatar circle (colored initials "IT"), "Iris Tan" bold, "MDC-009 · Marketing" gray caption.
  - Nav items (pill active state): My Dashboard (active) | My Payslips | My Attendance |
    My Leaves & OT | My Documents | Preferences.
  - Bottom: "Sign Out" ghost pill button.

Top nav: same glassmorphism style but simpler — just logo + employee name + avatar.

Main content — "My Dashboard":
  Editorial header:
    - "MY PORTAL" label small uppercase #005bc1
    - "Good morning, Iris." 3rem extrabold
    - "MDC-009 · Marketing Associate · Regular" gray subtitle

  Top row — 3 metric cards:
    - White card: "Next Payslip" — date "Mar 31, 2026" bold, "₱18,420 net pay" large,
      "View Payslip" blue ghost pill button.
    - Green card (#89fa9b bg): "Vacation Leave" — "12 days" 3rem extrabold, "remaining",
      "3 used this year" small below.
    - Amber card (#fbbc05 bg): "OT This Month" — "4.5 hrs" 3rem extrabold, "approved".

  Center card — "Time & Attendance" (white, radius 2rem, ambient shadow, centered content):
    - Current time large "08:42 AM" + date "Friday, March 20, 2026" below.
    - Status pill: "Clocked Out" gray rounded-full.
    - "Clock In" gradient large pill button (full width ish, prominent).
    - Below button: two small checks — camera icon "Take photo" + location pin "Location verified".
    - "Today's Log" section: small rows showing punch history (e.g., "Yesterday: IN 8:01 AM / OUT 5:03 PM").

  Bottom row — 2 cards:
    - "My Leave Requests" (white, radius 2rem):
      List of recent requests — each row: leave type pill (VL/SL/CL), dates, status pill
      (Pending=gray, Approved=green, Rejected=red).
      "File New Leave" blue ghost button bottom.
    - "My OT Requests" (white, radius 2rem):
      Same list structure for overtime requests.
      "File OT Request" blue ghost button bottom.
