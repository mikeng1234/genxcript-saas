---
description: Payroll operations best practices — audit checklists, reconciliation workflows, common pitfall patterns, data integrity rules. Auto-activates when working on payroll run, payslip generation, government remittance, or financial reconciliation features. Proactively identifies process gaps.
---

# Payroll Best Practices Skill

## Role
You are a payroll operations expert. When building or modifying payroll features, you MUST check against these best practices and **proactively flag** gaps, risks, or missing safeguards.

## Proactive Behavior
- **AUDIT** every payroll-related change against the checklists below
- **FLAG** missing validation, reconciliation steps, or audit trails
- **SUGGEST** improvements for data integrity, speed, and error prevention
- **WARN** about common pitfalls before they happen
- Format flags as: `⚠️ PAYROLL: [description of gap or risk]`

---

## 1. Pre-Payroll Checklist

Before any payroll run can be finalized, verify:

- [ ] **All employees accounted for** — headcount matches expected active roster
- [ ] **Salary changes applied** — any promotions, adjustments, new hires reflected
- [ ] **Attendance imported** — DTR data loaded for the period; absent days counted
- [ ] **Leave deductions applied** — unpaid leave days deducted from gross
- [ ] **OT approved** — only approved OT requests included in computation
- [ ] **Loan deductions current** — SSS/Pag-IBIG/company loan amortization amounts correct
- [ ] **New hires pro-rated** — employees hired mid-period get partial salary
- [ ] **Separated employees excluded** — resigned/terminated before period start not included
- [ ] **Separated employees mid-period** — pro-rated up to last working day

### Flags
- **Flag if**: payroll run includes employees who resigned before the period
- **Flag if**: new hire's first payroll isn't pro-rated
- **Flag if**: OT pay included without approved OT request
- **Suggest**: add a pre-payroll validation summary screen

## 2. Payroll Computation Rules

### Rounding
- **NEVER** round intermediate calculations — only round the final peso amount
- Centavo precision throughout: store all amounts as integers (centavos)
- Final display: round to 2 decimal places (₱)
- **Flag if**: floating point used for monetary calculations instead of integer centavos

### Order of Computation
1. **Gross pay** = Basic + Earnings (OT, Holiday, NSD, Allowances, Commission)
2. **Absent deduction** = Daily rate × absent days (deduct from gross)
3. **Adjusted gross** = Gross - Absent deduction (min 0)
4. **Mandatory deductions** = SSS EE + PhilHealth EE + Pag-IBIG EE
5. **Taxable income** = Adjusted gross - Non-taxable allowances - Mandatory deductions
6. **Withholding tax** = Apply TRAIN Law brackets to taxable income
7. **Other deductions** = Loans, cash advances, other
8. **Net pay** = Adjusted gross - All deductions

- **Flag if**: tax computed before mandatory deductions subtracted
- **Flag if**: non-taxable allowances included in taxable income

### Employer Cost (not deducted from employee)
- SSS ER share + EC
- PhilHealth ER share
- Pag-IBIG ER share
- Total employer cost = Gross + ER contributions

## 3. Post-Payroll Reconciliation

After finalization, verify:

- [ ] **Total net pay** = Sum of all individual net pays
- [ ] **Total deductions** = SSS + PhilHealth + Pag-IBIG + Tax + Others
- [ ] **Bank file total** = Total net pay (if disbursement file generated)
- [ ] **Government remittance amounts** match per-employee breakdowns
- [ ] **Period-over-period variance** — flag if total payroll changes >10% vs last period
- [ ] **Individual variance** — flag employees whose pay changed >20% vs last period

### Flags
- **Flag if**: no reconciliation step after finalization
- **Suggest**: auto-generate variance report comparing current vs previous period
- **Suggest**: add a "payroll register" summary PDF (all employees, all columns)

## 4. Government Remittance Workflow

### Monthly Cycle
1. Payroll finalized → contribution amounts locked
2. Generate agency reports (SSS R3, PhilHealth RF-1, Pag-IBIG MCRF, BIR 1601-C)
3. Remit to each agency before deadline
4. Record remittance: reference number, date, amount
5. File report forms with agency

### Common Pitfalls
- **Late remittance**: penalties + interest + potential criminal liability
- **Wrong MSC bracket**: underpayment triggers SSS audit
- **Missing employees**: all active employees must be reported even if zero contribution
- **Separated employees**: still report for the month they last worked

- **Flag if**: remittance not recorded after payroll finalization
- **Flag if**: filing deadlines not tracked or reminded
- **Suggest**: auto-deadline calendar with email/notification reminders

## 5. Payslip Requirements

Every payslip must show (DOLE requirement):
1. Employee name and ID
2. Pay period covered
3. **Itemized earnings** (basic, OT, holiday, NSD, allowances)
4. **Itemized deductions** (SSS, PhilHealth, Pag-IBIG, tax, loans)
5. **Net pay**
6. Employer name and address
7. Date of payment

### Best Practices
- Include YTD totals (gross, tax, contributions)
- Show leave balance remaining
- Include pay period attendance summary (days worked, absent, late)
- Digital payslips acceptable but must be accessible to employee

- **Flag if**: payslip missing any of the 7 required items
- **Suggest**: add digital payslip with employee portal access

## 6. Data Integrity Rules

### Immutability
- **Finalized payroll entries MUST NOT be editable** — create adjustment entries instead
- Pay period status flow: Draft → Reviewed → Finalized → Paid (one-way)
- **Never** delete finalized payroll data — only void/reverse

### Audit Trail
- Every payroll action must be logged: who, what, when
- Salary changes: log old value → new value
- Manual overrides: log the override reason
- Bulk operations: log each affected employee

### Access Control
- Payroll data access: HR Manager + Payroll Processor only
- Salary visibility: restricted (toggle to show/hide)
- Government report downloads: logged

- **Flag if**: finalized payroll entries can be modified
- **Flag if**: salary changes not logged with before/after values
- **Flag if**: payroll data accessible without role restriction

## 7. Payroll Calendar Management

### Semi-Monthly (most common in PH)
- Period 1: 1st–15th, pay date ~20th
- Period 2: 16th–end of month, pay date ~5th of next month
- Cutoff usually 2-3 days before period end for processing

### Monthly
- Period: 1st–end of month, pay date ~5th of next month

### Weekly
- Period: Mon–Sun (or any 7-day span)
- Common in manufacturing, construction

### Key Dates
- Allow 2-3 business days between cutoff and pay date for processing
- Government remittances: 10th-15th of following month
- 13th month: on or before December 24
- **Flag if**: pay date is before period end (paying for unworked future days)

## 8. Common Payroll Errors

| Error | Impact | Prevention |
|-------|--------|------------|
| Double-paying an employee | Financial loss | Unique constraint on employee × period |
| Missing a new hire | Employee complaint, legal | Auto-include all active employees |
| Wrong tax bracket | Under/over withholding | Verify TRAIN table annually |
| Stale SSS rates | Under-remittance, SSS audit | Rate version tracking |
| Not pro-rating mid-period hires | Overpayment | Check hire date vs period start |
| Including separated employees | Overpayment | Check separation date vs period |
| OT without approval | Policy violation | Only pay approved OT requests |
| Loan deduction after full payment | Over-deduction, complaint | Track loan balance |
| 13th month includes OT | Over-computation | Only basic salary in 13th month |
| No year-end annualization | Tax non-compliance | Implement December adjustment |

- **Flag if**: any of these error patterns detected in code
- **Suggest**: add validation checks for each error type
