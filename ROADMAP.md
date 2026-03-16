# GenXcript Payroll — Product Roadmap

## Phase 1: MVP (Current)
- [x] Database schema + government rates seed
- [x] Core payroll computation engine (SSS, PhilHealth, Pag-IBIG, BIR)
- [x] Employee Master File (CRUD)
- [x] Payroll Run (earnings input, auto-compute, finalize)
- [x] Payslip Generation (PDF export)
- [x] Dashboard (KPIs, remittance summary, deadlines)
- [x] Company Setup
- [x] Government Report Generation (SSS R3, PhilHealth RF-1, Pag-IBIG MCRF, BIR 1601-C)
- [x] Auth / Multi-tenant Login (Supabase Auth)

## Phase 2: Enhancements
- [x] Employee onboarding checklist — track if gov IDs (SSS, PhilHealth, Pag-IBIG, BIR TIN) are complete; many SMEs onboard employees without all numbers ready
- [x] Payroll approval workflow — add a "Reviewed by" field before finalize; useful when the boss wants to sign off before releasing pay
- [x] Payroll comparison — show period-over-period changes (new hires, salary adjustments, OT spikes) so employers can spot anomalies
- [x] Calendar view — visual timeline of pay periods, government deadlines, and Philippine holidays (~20 holidays/year affect holiday pay computation)
- [x] Employee self-service portal — let employees view their own payslips via login (requires Supabase Auth with employee-level roles)
- [x] Philippine holiday calendar table — auto-adjust remittance deadlines that fall on weekends/holidays to the next business day
- [x] Dashboard charts — payroll cost trend (line), deductions breakdown (pie), headcount over time (bar)
- [ ] PWA cache — offline-capable for areas with unstable internet

## Phase 4: Visibility Layer (ADP-Style Business Intelligence)
> Research date: 2026-03-15. Source: ADP "Fiscal Control Center" 10-point framework adapted for PH SMEs.

### Phase 4A — After 10 paying customers
- [x] **OT Heat Maps** — visualize which days/managers drive overtime spikes
- [ ] **Budget vs Actual Variance** — upload annual labor budget, show red/green status vs actual spend
- [ ] **Owner's Digest PDF** — scheduled Monday morning 1-page PDF: top 5 fiscal risks from prior week

### Phase 4B — After 50 paying customers (Premium Tier)
- [ ] **Real-Time Burn Rate** — Basic Pay + OT + Night Diff + Employer Statutories aggregated live
- [ ] **Cost Center Tagging** — tag every peso to department/project; Sales Support vs Direct Sales comparison
- [ ] **Geographic Cost Comparison** — multi-site SMEs (NCR HQ vs Laguna factory) cost efficiency
- [ ] **Turnover Cost Analytics** — fiscal impact of exits: retraining cost + productivity loss
- [ ] **Absenteeism Productivity Loss** — quantify unplanned leave cost to bottom line
- [ ] **Ghost Employee & Fraud Detection** — AI audit: flag duplicate clock-ins from same IP/device
- [ ] **Headcount Velocity** — hiring speed vs exits; ensures recruitment keeps pace with growth

---

## Phase 3: Scale
- [ ] React frontend (replace Streamlit for production)
- [ ] Electron desktop app (if demanded by clients)
- [x] BIR Form 2316 (annual certificate per employee)
- [x] BIR Form 1604-C (annual alphalist, due Jan 31)
- [x] Multi-company management (admin can switch between companies)
- [x] Audit trail (log who changed what and when)
