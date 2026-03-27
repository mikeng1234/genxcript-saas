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

PAGE: WORKFORCE ANALYTICS

Build a Workforce Analytics page for "GeNXcript Payroll".

Same top nav + sidebar. "Workforce Analytics" active.

4 pill-shaped tab switcher: "OT Analytics" | "Late Monitoring" | "Undertime" | "Break Monitoring"

Tab 1 — OT Analytics (shown by default):
  - Editorial header: "Workforce Analytics". Date range filter pill right side.
  - Top row: 3 metric cards (white, radius 2rem, ambient shadow):
    "Total OT Hours: 284 hrs" | "Total OT Cost: ₱42,600" | "Top Dept: Operations"
  - OT Heatmap card (white, full width, radius 2rem, ambient shadow):
    Title "Overtime Heatmap" + legend (0h white → 8h+ deep blue) top-right.
    Grid: employee names as rows (left), Mon–Sun as columns.
    Each cell: colored square — white=0h, light blue=1-2h, mid blue=3-4h, deep #005bc1=5h+.
    Cell shows hour number centered. Current day column slightly highlighted.
  - "Top OT Contributors" table card (white, radius 2rem) below:
    Rank # | Employee | Department | Shift | Total OT Hrs | OT Pay
    Rank 1 row highlighted with subtle blue-50 bg.

Tab 2 — Late Monitoring:
  - Ranked list: top 5 late employees as cards (white, radius 1.5rem).
    Each: rank number large bold left, avatar + name, "14 incidents" pill amber,
    total minutes, trend arrow (up=worsening red, down=improving green).
  - Below: "3-Month Calendar" for selected employee (white card, radius 2rem).
    Each late day = amber bubble, sized by minutes late (larger = later).
    Rest days = gray dot. Present on-time = green dot.

Tab 3 — Undertime: Same layout as Late Monitoring but data is undertime minutes.

Tab 4 — Break Monitoring:
  - White card table (radius 2rem): Employee | Scheduled Break | Avg Actual Break |
    Overbreak (min) | Portal Days tracked.
  - Rows where Overbreak > 15 min: amber-tinted row bg (#fbbc05 at 10% opacity).
  - Summary: "Avg overbreak: 8 min" metric card amber top-right.
