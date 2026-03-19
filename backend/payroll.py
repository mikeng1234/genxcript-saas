"""
Core payroll computation module for Philippine SME payroll.

All monetary values are in CENTAVOS (integer).
₱1,500.00 = 150_000 centavos.

This module is pure computation — no database calls, no side effects.
Pass rates as arguments so we never hardcode them.
"""

from dataclasses import dataclass


# ============================================================
# Data structures
# ============================================================

@dataclass
class SSSRates:
    """SSS contribution rate parameters."""
    employee_rate: float    # 0.05
    employer_rate: float    # 0.10
    msc_min: int            # minimum Monthly Salary Credit (centavos)
    msc_max: int            # maximum Monthly Salary Credit (centavos)
    ec_low: int             # Employees' Compensation low bracket (centavos)   = 1_000 (₱10)
    ec_high: int            # Employees' Compensation high bracket (centavos)  = 3_000 (₱30)
    ec_threshold: int       # MSC at which EC switches to high (centavos)      = 1_500_000 (₱15,000)


@dataclass
class PhilHealthRates:
    """PhilHealth contribution rate parameters."""
    employee_rate: float    # 0.025
    employer_rate: float    # 0.025
    income_floor: int       # centavos
    income_ceiling: int     # centavos


@dataclass
class PagIBIGRates:
    """Pag-IBIG contribution rate parameters."""
    employee_rate_normal: float  # 0.02
    employee_rate_low: float     # 0.01
    low_salary_threshold: int    # centavos (₱1,500 = 150_000)
    employer_rate: float         # 0.02
    max_fund_salary: int         # centavos (₱10,000 = 1_000_000)


@dataclass
class TaxBracket:
    """A single BIR withholding tax bracket."""
    min_amount: int     # centavos
    max_amount: int     # centavos or None for the last bracket
    base_tax: int       # centavos
    rate: float         # e.g. 0.20
    over: int           # centavos — "of excess over"


@dataclass
class PayrollResult:
    """Complete payroll computation result for one employee."""
    gross_pay: int

    # Government contributions — employee share
    sss_employee: int
    philhealth_employee: int
    pagibig_employee: int

    # Government contributions — employer share
    sss_employer: int
    philhealth_employer: int
    pagibig_employer: int

    # Tax
    taxable_income: int
    withholding_tax: int

    # Totals
    total_mandatory_deductions: int
    net_pay: int


# ============================================================
# Default 2025 rates (used when DB is not available, e.g. tests)
# ============================================================

DEFAULT_SSS_RATES = SSSRates(
    employee_rate=0.05,
    employer_rate=0.10,
    msc_min=500_000,       # ₱5,000
    msc_max=3_500_000,     # ₱35,000
    ec_low=1_000,          # ₱10  — MSC < ₱15,000
    ec_high=3_000,         # ₱30  — MSC ≥ ₱15,000
    ec_threshold=1_500_000,# ₱15,000 (SSS Circular 2024-006)
)

DEFAULT_PHILHEALTH_RATES = PhilHealthRates(
    employee_rate=0.025,
    employer_rate=0.025,
    income_floor=1_000_000,    # ₱10,000
    income_ceiling=10_000_000, # ₱100,000
)

DEFAULT_PAGIBIG_RATES = PagIBIGRates(
    employee_rate_normal=0.02,
    employee_rate_low=0.01,
    low_salary_threshold=150_000,  # ₱1,500
    employer_rate=0.02,
    max_fund_salary=1_000_000,     # ₱10,000
)

DEFAULT_TAX_BRACKETS = [
    TaxBracket(min_amount=0,          max_amount=2_083_300,  base_tax=0,          rate=0.00, over=0),
    TaxBracket(min_amount=2_083_300,  max_amount=3_333_200,  base_tax=0,          rate=0.20, over=2_083_300),
    TaxBracket(min_amount=3_333_300,  max_amount=6_666_600,  base_tax=250_000,    rate=0.25, over=3_333_300),
    TaxBracket(min_amount=6_666_700,  max_amount=16_666_600, base_tax=1_083_300,  rate=0.30, over=6_666_700),
    TaxBracket(min_amount=16_666_700, max_amount=66_666_600, base_tax=4_083_300,  rate=0.32, over=16_666_700),
    TaxBracket(min_amount=66_666_700, max_amount=None,       base_tax=20_083_300, rate=0.35, over=66_666_700),
]


# ============================================================
# SSS Computation
# ============================================================

def compute_sss(monthly_salary: int, rates: SSSRates = DEFAULT_SSS_RATES) -> tuple[int, int]:
    """
    Compute SSS contributions (employee share, employer share).

    Per SSS Circular No. 2024-006 (effective January 2025):
    - Employee Total = 5% of MSC (Regular SS + MPF portions, same rate)
    - Employer Total = 10% of MSC (Regular SS + MPF) + EC
      EC = ₱10 if MSC < ₱15,000, else ₱30 (Employees' Compensation Fund)

    The MSC is clamped between msc_min (₱5,000) and msc_max (₱35,000).

    Returns:
        (employee_total, employer_total) in centavos.
        employer_total already includes the EC amount.
    """
    # Clamp salary to MSC range
    msc = max(rates.msc_min, min(monthly_salary, rates.msc_max))

    employee = int(round(msc * rates.employee_rate))
    employer_ss = int(round(msc * rates.employer_rate))
    ec = rates.ec_high if msc >= rates.ec_threshold else rates.ec_low
    employer = employer_ss + ec

    return employee, employer


# ============================================================
# PhilHealth Computation
# ============================================================

def compute_philhealth(monthly_salary: int, rates: PhilHealthRates = DEFAULT_PHILHEALTH_RATES) -> tuple[int, int]:
    """
    Compute PhilHealth contributions (employee share, employer share).

    The salary is clamped between the income floor and ceiling.
    Each side pays 2.5% of the clamped salary.

    Returns:
        (employee_share, employer_share) in centavos.
    """
    # Clamp salary to floor/ceiling
    clamped = max(rates.income_floor, min(monthly_salary, rates.income_ceiling))

    employee = int(round(clamped * rates.employee_rate))
    employer = int(round(clamped * rates.employer_rate))

    return employee, employer


# ============================================================
# Pag-IBIG Computation
# ============================================================

def compute_pagibig(monthly_salary: int, rates: PagIBIGRates = DEFAULT_PAGIBIG_RATES) -> tuple[int, int]:
    """
    Compute Pag-IBIG contributions (employee share, employer share).

    Employee rate is 1% if salary ≤ ₱1,500, otherwise 2%.
    Employer always pays 2%.
    Both are computed on salary capped at max_fund_salary (₱10,000).

    Returns:
        (employee_share, employer_share) in centavos.
    """
    # Cap salary at max fund salary for contribution computation
    capped = min(monthly_salary, rates.max_fund_salary)

    # Determine employee rate based on salary threshold
    if monthly_salary <= rates.low_salary_threshold:
        ee_rate = rates.employee_rate_low
    else:
        ee_rate = rates.employee_rate_normal

    employee = int(round(capped * ee_rate))
    employer = int(round(capped * rates.employer_rate))

    return employee, employer


# ============================================================
# BIR Withholding Tax Computation
# ============================================================

def compute_withholding_tax(
    taxable_income: int,
    brackets: list[TaxBracket] = DEFAULT_TAX_BRACKETS,
) -> int:
    """
    Compute monthly BIR withholding tax using TRAIN Law brackets.

    taxable_income: monthly taxable income in centavos
                    (gross - SSS_ee - PhilHealth_ee - PagIBIG_ee - nontaxable benefits)

    Returns:
        Withholding tax amount in centavos.
    """
    if taxable_income <= 0:
        return 0

    for bracket in brackets:
        in_bracket = (
            taxable_income >= bracket.min_amount
            and (bracket.max_amount is None or taxable_income <= bracket.max_amount)
        )
        if in_bracket:
            excess = taxable_income - bracket.over
            tax = bracket.base_tax + int(round(excess * bracket.rate))
            return max(tax, 0)

    # Should not reach here if brackets are properly defined
    return 0


# ============================================================
# Full Payroll Computation
# ============================================================

def compute_payroll(
    gross_pay: int,
    nontaxable_allowances: int = 0,
    sss_rates: SSSRates = DEFAULT_SSS_RATES,
    philhealth_rates: PhilHealthRates = DEFAULT_PHILHEALTH_RATES,
    pagibig_rates: PagIBIGRates = DEFAULT_PAGIBIG_RATES,
    tax_brackets: list[TaxBracket] = DEFAULT_TAX_BRACKETS,
) -> PayrollResult:
    """
    Compute complete payroll for one employee for one pay period.

    Args:
        gross_pay: Total gross pay for the period (centavos).
        nontaxable_allowances: Non-taxable portion of gross (centavos).
                               Already included in gross_pay but excluded from tax.
        sss_rates: SSS rate parameters.
        philhealth_rates: PhilHealth rate parameters.
        pagibig_rates: Pag-IBIG rate parameters.
        tax_brackets: BIR monthly withholding tax brackets.

    Returns:
        PayrollResult with all computed values.
    """
    # Government contributions (based on gross pay minus nontaxable)
    taxable_gross = gross_pay - nontaxable_allowances

    sss_ee, sss_er = compute_sss(taxable_gross, sss_rates)
    ph_ee, ph_er = compute_philhealth(taxable_gross, philhealth_rates)
    pi_ee, pi_er = compute_pagibig(taxable_gross, pagibig_rates)

    # Taxable income = gross - nontaxable allowances - mandatory employee contributions
    taxable_income = taxable_gross - sss_ee - ph_ee - pi_ee

    # Withholding tax
    wht = compute_withholding_tax(taxable_income, tax_brackets)

    # Total mandatory deductions (employee side only)
    total_mandatory = sss_ee + ph_ee + pi_ee + wht

    # Net pay
    net_pay = gross_pay - total_mandatory

    return PayrollResult(
        gross_pay=gross_pay,
        sss_employee=sss_ee,
        philhealth_employee=ph_ee,
        pagibig_employee=pi_ee,
        sss_employer=sss_er,
        philhealth_employer=ph_er,
        pagibig_employer=pi_er,
        taxable_income=taxable_income,
        withholding_tax=wht,
        total_mandatory_deductions=total_mandatory,
        net_pay=net_pay,
    )
