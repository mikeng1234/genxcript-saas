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
- [ ] Employee self-service portal — let employees view their own payslips via login (requires Supabase Auth with employee-level roles)
- [x] Philippine holiday calendar table — auto-adjust remittance deadlines that fall on weekends/holidays to the next business day
- [x] Dashboard charts — payroll cost trend (line), deductions breakdown (pie), headcount over time (bar)
- [ ] PWA cache — offline-capable for areas with unstable internet

## Phase 3: Scale
- [ ] React frontend (replace Streamlit for production)
- [ ] Electron desktop app (if demanded by clients)
- [ ] BIR Form 2316 (annual certificate per employee)
- [ ] BIR Form 1604-C (annual alphalist, due Jan 31)
- [ ] Multi-company management (admin can switch between companies)
- [ ] Audit trail (log who changed what and when)
