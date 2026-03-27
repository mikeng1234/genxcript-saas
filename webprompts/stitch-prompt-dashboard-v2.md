# Stitch Prompt — GeNXcript Payroll Dashboard v2

> **Goal**: Generate a single-page HTML dashboard mockup for the GeNXcript Payroll SaaS admin dashboard. This replaces the current bento layout with a data-dense, multi-panel grid inspired by the reference image. The output will be adapted into Streamlit `st.markdown(unsafe_allow_html=True)` components.

---

## 🎨 Brand & Design System

### Colors (STRICT — do not deviate)
| Token | Hex | Usage |
|-------|-----|-------|
| Primary Blue | `#005bc1` | CTAs, active bars, links, accents |
| Dark Text | `#191c1d` | Headlines, card titles, primary text |
| Secondary Text | `#727784` | Subtitles, descriptions |
| Muted Text | `#9ca3af` | Timestamps, tertiary info |
| Yellow Accent | `#febf0d` | Highlight chips, warning badges |
| Success Green | `#10b981` | Positive trends, success status |
| Error Red | `#93000a` | Negative trends, overdue, reject |
| Card Background | `#ffffff` | All card surfaces |
| Page Background | `#f4f5f7` | Body/canvas behind cards |
| Border / Divider | `#e5e7eb` | Subtle card borders, table row dividers |
| Light Blue BG | `#dbeafe` | Badge backgrounds, icon containers |
| Light Green BG | `#d1fae5` | Success badge backgrounds |
| Light Yellow BG | `#fef3c7` | Warning badge backgrounds |
| Light Purple BG | `#ede9fe` | Analytics accent backgrounds |

### Typography
- **Font Family**: `'Plus Jakarta Sans', 'Inter', system-ui, -apple-system, sans-serif`
- **Headline numbers**: 36–44px, weight 800–900, letter-spacing: -2px
- **Card titles**: 10–11px, weight 700, uppercase, letter-spacing: 0.15em, color `#9ca3af`
- **Body text**: 12–13px, weight 500–600
- **Small labels**: 9–10px, weight 600–700

### Card Style
- `border-radius: 16px`
- `padding: 24px`
- `box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.03)`
- On hover: `translateY(-2px)`, shadow intensifies to `0 8px 28px rgba(0,0,0,0.10)`
- Smooth transition: `0.18s cubic-bezier(.34,1.56,.64,1)`

---

## 📐 Layout Grid (6 panels, 2 rows)

```
┌─────────────────────┬──────────────────────┬─────────────────────┐
│   Payroll Overview   │   Recent Payroll     │   Attendance Rate   │
│   (KPI-style card)   │   (Employee list)    │   (Bar chart)       │
│   ~33% width         │   ~33% width         │   ~33% width        │
├─────────────────────┼──────────────────────┼─────────────────────┤
│   Workforce          │   Attendance Detail  │   Pending Requests  │
│   Breakdown          │   (Table w/ search)  │   (Leave/OT list)   │
│   (Donut chart)      │   ~42% width         │   ~25% width        │
│   ~25% width         │                      │                     │
└─────────────────────┴──────────────────────┴─────────────────────┘
```

### Row gap: 16px. Column gap: 16px. All cards same height within each row.

---

## 📊 Panel 1 — Payroll Overview (Top-Left)

**Purpose**: High-level payroll KPI card — replaces "Upcoming Milestone".

### Content:
- **Header**: "PAYROLL OVERVIEW" (uppercase label, `#9ca3af`, 10px, letter-spacing 0.15em)
- **Headline number**: Total Gross Pay for latest period, e.g. `₱383,127.84`
  - Font: 32px, weight 900, color `#191c1d`
  - Currency symbol `₱` slightly smaller (24px)
- **Trend badge**: Inline pill showing period-over-period change
  - Green up arrow + `3.2%` if positive (background `#d1fae5`, text `#059669`)
  - Red down arrow if negative (background `#fee2e2`, text `#93000a`)
  - Gray `— flat` if unchanged
- **Subtitle**: Period range, e.g. "2026-04-01 → 2026-04-30" in `#9ca3af` 10px
- **Mini sparkline chart** (bottom half of card):
  - 6 data points (last 6 pay periods)
  - Line chart with area fill — `#005bc1` line, `rgba(0,91,193,0.08)` fill
  - X-axis labels: abbreviated month names (e.g. "Oct", "Nov", "Dec", "Jan", "Feb", "Mar")
  - Y-axis hidden (implicit from line height)
  - Dots on data points, active/latest dot larger + blue
  - Include small annotation at latest point showing the value
- **Bottom stat row** (3 mini stats in a row beneath the chart):
  - "Net Pay: ₱___" | "Employer Cost: ₱___" | "Headcount: __"
  - Font: 10px, weight 600, `#727784`

### Interactions:
- Entire card is clickable → opens payroll detail modal
- Hover: subtle lift + shadow

---

## 📊 Panel 2 — Recent Payroll (Top-Center)

**Purpose**: Latest pay run employee breakdown — shows top 5–7 paid employees.

### Content:
- **Header row**: "RECENT PAYROLL" label + small circular icon (blue, `#005bc1` background, white peso sign)
- **Employee list** (vertical stack, max 5–7 rows, scrollable if more):
  - Each row:
    - **Avatar**: 32px circle with initials (blue `#dbeafe` background, `#005bc1` text) or photo
    - **Name**: 12px, weight 700, `#191c1d` — e.g. "Michelle Martin"
    - **Date**: Below name, 10px, `#9ca3af` — e.g. "March 28, 2026"
    - **Amount**: Right-aligned, 13px, weight 800, `#191c1d` — e.g. "₱3,200"
    - **Status pill**: Right-aligned below amount
      - `Success` → green pill (`#d1fae5` bg, `#059669` text)
      - `Pending` → yellow pill (`#fef3c7` bg, `#d97706` text)
      - `Delay` → red pill (`#fee2e2` bg, `#93000a` text)
- **Row dividers**: 1px `#f3f4f6` between each row (not on last)

### Interactions:
- Click any employee row → navigate to payslip detail
- Hover row: background shifts to `#f8f9fa`

---

## 📊 Panel 3 — Attendance Rate (Top-Right)

**Purpose**: Monthly attendance percentage with historical bar chart.

### Content:
- **Header row**: "ATTENDANCE RATE" label + dropdown/pill showing "Monthly" filter
- **Headline**: Large percentage, e.g. `98%`
  - Font: 44px, weight 900, `#191c1d`
- **Trend line**: Below headline
  - Green text: "▲ 12% better than last month" (or red if worse)
  - Font: 11px, weight 600
- **Bar chart** (main visual, fills remaining card space):
  - 6–12 bars (one per month)
  - Bar color: gradient — `#10b981` (base) to `#059669` (top) for current month; `#e5e7eb` for past months
  - Active/current month bar: `#10b981` solid
  - X-axis: month abbreviations ("Apr", "May", "Jun", etc.)
  - Y-axis: percentage (hidden, implied by bar heights relative to 100%)
  - Bar border-radius: `4px 4px 0 0`
  - Bar gap: 8px
  - On hover each bar: tooltip showing "Month: XX%"

### Data source:
- Computed from `time_logs` table: (days_present / working_days) × 100 per month
- If attendance module not enabled, show placeholder "Enable Attendance module"

---

## 📊 Panel 4 — Workforce Breakdown (Bottom-Left)

**Purpose**: Donut chart showing workforce demographics.

### Content:
- **Header**: "TOTAL EMPLOYEES" label
- **Donut chart** (center of card):
  - Outer ring thickness: ~20px
  - Center shows: large number (e.g. `14`) + "Employees" subtitle below
  - Segments by **department** (not age), color-coded:
    - Engineering: `#005bc1`
    - Operations: `#10b981`
    - Marketing: `#f59e0b`
    - HR: `#8b5cf6`
    - Finance: `#ef4444`
    - Other: `#9ca3af`
  - Smooth segment transitions
- **Legend** (below or beside donut):
  - Colored dot + department name + percentage, stacked vertically
  - Font: 11px, weight 600
  - Layout: 2-column grid if space allows

### Interactions:
- Hover segment: slight scale + tooltip with count
- Click: could filter other panels by department (future)

---

## 📊 Panel 5 — Attendance Detail (Bottom-Center)

**Purpose**: Tabular daily attendance log with search/filter.

### Content:
- **Header row**: "ATTENDANCE DETAIL" label + 🔗 expand icon (top-right)
- **Toolbar** (below header):
  - Search input: rounded, `#f4f5f7` background, magnifying glass icon, placeholder "Search..."
  - Filter button: icon + "Filter" text, subtle outline
  - Sort By button: icon + "Sort By" text, subtle outline
- **Table** (fills card):
  - Columns: Employee | Check In | Check Out | Status
  - **Employee column**:
    - Small avatar (24px) + colored ID badge (e.g. `#EMP-12467` in matching department color) + Name (12px, weight 700)
  - **Check In / Check Out**: `07:02:01` format, monospace-ish, 12px, `#191c1d`
  - **Status column**: Pill badge
    - `Present` / `Attend` → green (`#d1fae5` bg, `#059669` text)
    - `Late` → red (`#fee2e2` bg, `#93000a` text)
    - `Absent` → gray (`#f3f4f6` bg, `#6b7280` text)
  - Row height: ~44px, alternating row background: transparent / `#fafbfc`
  - Max 6–7 visible rows, scrollable overflow
  - Row hover: `#f0f4ff` highlight

### Data source:
- From `time_logs` table (today's entries)
- Employee names from `employees` table

---

## 📊 Panel 6 — Pending Requests (Bottom-Right)

**Purpose**: Leave and OT requests awaiting approval.

### Content:
- **Header**: "PENDING REQUESTS" label + count badge (e.g. `5` in blue circle)
- **Tab pills** (optional): "Leave" | "Overtime" toggle
- **Request list** (vertical stack):
  - Each row:
    - **Avatar**: 36px circle with initials or photo
    - **Name**: 12px, weight 700, `#191c1d`
    - **Role/Position**: 10px, `#9ca3af`, below name
    - **Action buttons** (right-aligned):
      - ✓ Approve: 28px circle, `#10b981` background, white checkmark
      - ✗ Reject: 28px circle, `#fee2e2` background, `#93000a` × icon
  - Row dividers: same as Recent Payroll
- **Empty state**: If no pending requests, show:
  - Checkmark icon + "All caught up! No pending requests."
  - Muted green text, centered

### Interactions:
- Approve/Reject buttons: on click, shows brief toast confirmation
- Hover buttons: slight scale (1.1) + shadow

---

## 🖥️ Page Header (Above Grid)

### Left side:
- **Page title**: "Dashboard" — 28px, weight 800, `#191c1d`
- **Greeting**: "Good morning, {FirstName}." — 16px, weight 600, `#191c1d`
- **Subtitle**: "Everything is ready for your next pay cycle." — 13px, `#727784`

### Right side:
- **Date**: "March 28, 2026" — 14px, weight 700, `#191c1d`
- **Time**: "9:41 AM" — 12px, `#727784`

---

## 🔧 Technical Requirements

1. **Single HTML file** — all CSS inline or in `<style>` block, no external dependencies
2. **Charts**: Use pure SVG or CSS for all charts (sparkline, bars, donut). No Chart.js/D3 — must be copyable into Streamlit `unsafe_allow_html`
3. **Responsive**: Cards should use CSS Grid (`grid-template-columns`) that collapses gracefully
4. **Font**: Load `Plus Jakarta Sans` from Google Fonts: `<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">`
5. **Icons**: Use Material Design Icons CDN or inline SVGs
6. **Animations**:
   - Cards fade-in + slide-up on load (staggered 80ms)
   - Numbers count-up animation on load
   - Bar chart bars grow upward on load
   - Donut chart segments animate clockwise on load
7. **Hover states**: All cards have lift + shadow on hover as specified in card style above
8. **Dark mode NOT required** — light theme only
9. **Sample data**: Use realistic Philippine payroll data:
   - Currency: Philippine Peso (₱)
   - Names: Filipino names (e.g., Ana Reyes, Carlos Santos, Maria Cruz)
   - Amounts: ₱15,000–₱45,000 range per employee
   - Dates: March 2026
   - Departments: Engineering, Operations, Marketing, HR, Finance

---

## 📋 Sample Data to Use

### Recent Payroll (Panel 2):
| Employee | Amount | Status |
|----------|--------|--------|
| Ana Reyes | ₱42,500 | Success |
| Carlos Santos | ₱38,200 | Success |
| Maria Cruz | ₱35,800 | Pending |
| Jose Garcia | ₱28,400 | Success |
| Carla Diaz | ₱22,100 | Delay |

### Attendance (Panel 5):
| Employee | Check In | Check Out | Status |
|----------|----------|-----------|--------|
| Ana Reyes | 08:02:34 | 17:05:12 | Present |
| Carlos Santos | 08:45:22 | 00:00:00 | Late |
| Maria Cruz | 07:58:01 | 17:02:45 | Present |
| Jose Garcia | 09:12:44 | 00:00:00 | Late |
| Carla Diaz | 08:00:15 | 17:30:22 | Present |

### Workforce by Department (Panel 4):
| Department | Count | Percentage |
|------------|-------|------------|
| Engineering | 5 | 36% |
| Operations | 3 | 21% |
| Marketing | 2 | 14% |
| HR | 2 | 14% |
| Finance | 2 | 14% |

### Pending Requests (Panel 6):
| Employee | Type | Position |
|----------|------|----------|
| Maria Cruz | Leave | Marketing Officer |
| Jose Garcia | Overtime | Engineer |
| Ana Reyes | Leave | Lead Designer |

---

## ✅ Output Checklist

- [ ] All 6 panels rendered in the grid layout
- [ ] Sparkline chart in Payroll Overview (pure SVG)
- [ ] Bar chart in Attendance Rate (pure CSS or SVG)
- [ ] Donut chart in Workforce Breakdown (pure SVG)
- [ ] Search + Filter toolbar in Attendance Detail
- [ ] Approve/Reject buttons in Pending Requests
- [ ] All colors match the brand palette exactly
- [ ] Hover states on all cards
- [ ] Entrance animations (fade-in, count-up, chart grow)
- [ ] Filipino sample data with ₱ currency
- [ ] Plus Jakarta Sans font loaded
- [ ] No external JS libraries (pure HTML/CSS/SVG/vanilla JS)
