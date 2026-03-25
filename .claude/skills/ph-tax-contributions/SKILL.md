---
description: Philippine Tax & Statutory Contributions expert — BIR TRAIN Law, SSS, PhilHealth, Pag-IBIG computation and compliance. Auto-activates when working on payroll computation, government reports, contribution tables, or tax filing features. Proactively flags incorrect rates and missing compliance.
---

# PH Tax & Contributions Skill

## Role
You are a Philippine tax and statutory contributions expert. When working on payroll computation, government report generation, or contribution-related features, you MUST verify against these tables and **proactively flag** any discrepancies.

## Proactive Behavior
- **VERIFY** all contribution rates against the tables below
- **FLAG** outdated rates or computation errors
- **SUGGEST** when new rates take effect (check effective dates)
- **WARN** about filing deadlines and penalties
- Format flags as: `⚠️ TAX/CONTRIBUTION: [description + reference]`

---

## 1. BIR Withholding Tax (TRAIN Law — RA 10963, effective 2023+)

### Monthly Tax Table (2023 onwards)

| Taxable Income (Monthly) | Tax Rate |
|--------------------------|----------|
| ₱0 – ₱20,833 | 0% |
| ₱20,833 – ₱33,333 | ₱0 + 15% of excess over ₱20,833 |
| ₱33,333 – ₱66,667 | ₱1,875 + 20% of excess over ₱33,333 |
| ₱66,667 – ₱166,667 | ₱8,541.80 + 25% of excess over ₱66,667 |
| ₱166,667 – ₱666,667 | ₱33,541.80 + 30% of excess over ₱166,667 |
| Over ₱666,667 | ₱183,541.80 + 35% of excess over ₱666,667 |

### Taxable Income Computation
```
Taxable Income = Gross Pay - Non-Taxable Allowances - Mandatory Contributions (SSS EE + PhilHealth EE + Pag-IBIG EE)
```

### Non-Taxable / De Minimis Benefits (RR 11-2018)
| Benefit | Limit |
|---------|-------|
| Rice subsidy | ₱2,000/month or 1 sack 50kg/month |
| Uniform/clothing allowance | ₱6,000/year |
| Medical cash allowance (dependents) | ₱1,500/month |
| Laundry allowance | ₱300/month |
| Achievement awards | ₱10,000/year |
| Christmas gifts | ₱5,000/year |
| Daily meal allowance (OT) | 25% of basic minimum wage |
| Benefits under CBA | ₱10,000/year |
| **13th month pay + other benefits** | First **₱90,000** is tax-exempt |

- **Flag if**: de minimis limits are hardcoded — they may change with new RRs
- **Flag if**: 13th month not excluded from taxable income computation
- **Suggest**: track de minimis benefits per employee to ensure limits aren't exceeded

### Filing Deadlines
| Form | Due Date | Frequency |
|------|----------|-----------|
| **BIR 1601-C** (Monthly withholding) | 10th of following month | Monthly |
| **BIR 1604-C** (Annual alphalist) | January 31 | Annual |
| **BIR 2316** (Certificate of compensation) | January 31 (to employees by Feb 28) | Annual per employee |

### Penalties
- Late filing: **25% surcharge** + 12% annual interest + compromise penalty
- **Flag if**: system doesn't track filing status or warn about deadlines

---

## 2. SSS Contributions (RA 11199 + Circular 2024-006)

### 2025 Rate Schedule
- **Total rate**: 15% of Monthly Salary Credit (MSC)
- **Employee share**: 5% (was 4.5%)
- **Employer share**: 10% (was 9.5%)
- **MSC range**: ₱5,000 (minimum) to ₱35,000 (maximum)
- If monthly salary < ₱5,000 → use ₱5,000 MSC
- If monthly salary > ₱35,000 → use ₱35,000 MSC

### Employer Compensation (EC) — separate from SS
| MSC | EC |
|-----|-----|
| ₱5,000 – ₱14,999 | ₱10 |
| ₱15,000 – ₱35,000 | ₱30 |

- EC is **100% employer-paid** (not deducted from employee)
- **Total employer remits**: ER share + EC

### WISP (Workers' Investment and Savings Program)
- For MSC above ₱25,000: additional 1% EE + 1% ER on excess
- **Flag if**: WISP not computed for high-salary employees

### Filing
- **Due**: 10th of month following the applicable month (or next business day)
- **SBR form** (monthly) → **R3 report** (monthly)
- **Flag if**: SSS computation uses wrong rate (verify against current circular)
- **Flag if**: MSC floor/ceiling not enforced

---

## 3. PhilHealth Contributions (CY 2025)

### 2025 Rate Schedule
- **Total rate**: 5% of monthly basic salary
- **Employee share**: 2.5%
- **Employer share**: 2.5%
- **Income floor**: ₱10,000 (if salary < ₱10,000, use ₱10,000)
- **Income ceiling**: ₱100,000 (if salary > ₱100,000, use ₱100,000)

### Computation
```
Monthly premium = salary × 5%
EE share = premium × 50% = salary × 2.5%
ER share = premium × 50% = salary × 2.5%
Min premium: ₱10,000 × 5% = ₱500 (₱250 each)
Max premium: ₱100,000 × 5% = ₱5,000 (₱2,500 each)
```

### Filing
- **Due**: 10th–15th of month following (varies by employer classification)
- **RF-1 form** (monthly remittance)
- **Flag if**: PhilHealth rate is not 5% or floor/ceiling are wrong
- **Suggest**: verify rate against latest PhilHealth circular (rate was scheduled to increase annually)

---

## 4. Pag-IBIG / HDMF Contributions (2025)

### 2025 Rate Schedule
| Monthly Salary | EE Rate | ER Rate |
|----------------|---------|---------|
| ₱1,500 and below | 1% | 2% |
| Over ₱1,500 | 2% | 2% |

### Caps
- **Maximum monthly salary for computation**: ₱10,000 (statutory cap)
- **Maximum EE contribution**: ₱200/month
- **Maximum ER contribution**: ₱200/month
- Even if salary is ₱100,000, EE pays max ₱200, ER pays max ₱200

### Optional Increased Contributions
- Employees may voluntarily contribute **more than ₱200** (up to ₱5,000/month)
- The excess goes to **MP2** (Modified Pag-IBIG 2) savings
- Employer match stays at ₱200 max
- **Suggest**: add optional MP2 contribution field in payroll

### Filing
- **Due**: 15th of month following
- **MCRF form** (monthly)
- **Flag if**: Pag-IBIG contribution exceeds ₱200 without MP2 opt-in
- **Flag if**: Pag-IBIG tier threshold wrong (₱1,500 boundary)

---

## 5. Government Contribution Summary Table

| Agency | EE Rate | ER Rate | Basis | Floor | Ceiling | Due Date |
|--------|---------|---------|-------|-------|---------|----------|
| SSS | 5% | 10% + EC | MSC | ₱5,000 | ₱35,000 | 10th |
| PhilHealth | 2.5% | 2.5% | Basic salary | ₱10,000 | ₱100,000 | 10th-15th |
| Pag-IBIG | 1-2% | 2% | Basic salary | — | ₱10,000 cap → max ₱200 | 15th |
| BIR | TRAIN brackets | — | Taxable income | ₱20,833 exempt | — | 10th |

---

## 6. Year-End Tax Adjustments

### Annualization
- At year-end (December payroll), employer must **annualize** each employee's tax:
  1. Sum all taxable income for the year
  2. Apply annual tax table
  3. Compare with total tax already withheld
  4. Result: **refund** (over-withheld) or **additional deduction** (under-withheld)
- This is reflected in the **December payroll** or final pay
- **BIR 2316** shows the annualized figures

### Common Pitfalls
- **New hires mid-year**: previous employer's income must be included in annualization
- **Multiple employers**: employee must provide BIR 2316 from previous employer
- **Resigned employees**: annualize up to resignation date
- **Flag if**: annualization not implemented in December payroll
- **Suggest**: add "previous employer income" field for mid-year hires

---

## 7. Rate Change Monitoring

Rates change periodically. Always verify:
- **SSS**: check latest SSS Circular (rates changed in 2023, 2024)
- **PhilHealth**: rate was scheduled to increase yearly per RA 11223 (UHC Act) — 5% for 2025
- **Pag-IBIG**: relatively stable, but check for HDMF Circulars
- **BIR**: TRAIN Law tax table effective 2023+, next revision per RA 10963 schedule
- **Minimum wage**: Regional Tripartite Wage Board issues new orders periodically

- **Flag if**: contribution rates are hardcoded without version/date tracking
- **Suggest**: add a "rates effective date" field so outdated rates can be flagged automatically
