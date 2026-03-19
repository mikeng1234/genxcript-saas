"""
Unit tests for Philippine payroll computations.

Uses known scenarios to verify SSS, PhilHealth, Pag-IBIG, and BIR
withholding tax calculations against 2025 government rates.

All amounts in centavos.
"""

import pytest

from backend.payroll import (
    compute_sss,
    compute_philhealth,
    compute_pagibig,
    compute_withholding_tax,
    compute_payroll,
    DEFAULT_SSS_RATES,
    DEFAULT_PHILHEALTH_RATES,
    DEFAULT_PAGIBIG_RATES,
    DEFAULT_TAX_BRACKETS,
)


# ============================================================
# SSS Tests
# ============================================================

class TestSSS:
    """SSS contribution tests — SSS Circular No. 2024-006 (effective January 2025).

    Employee Total = 5% of clamped MSC (Regular SS + MPF, same rate).
    Employer Total = 10% of clamped MSC + EC (₱10 if MSC < ₱15k, ₱30 if MSC ≥ ₱15k).
    """

    def test_minimum_salary(self):
        """Salary below MSC min (₱5,000) — clamped to floor, EC = ₱10."""
        ee, er = compute_sss(300_000)  # ₱3,000
        # MSC clamped to ₱5,000; EC = ₱10 (MSC < ₱15,000)
        assert ee == 25_000    # 5%  × ₱5,000 = ₱250
        assert er == 51_000    # 10% × ₱5,000 + ₱10 EC = ₱510

    def test_exact_minimum_msc(self):
        """Salary exactly at MSC min (₱5,000), EC = ₱10."""
        ee, er = compute_sss(500_000)
        assert ee == 25_000    # ₱250
        assert er == 51_000    # ₱510

    def test_mid_range_salary(self):
        """₱15,000 salary — EC jumps to ₱30 (MSC ≥ ₱15,000)."""
        ee, er = compute_sss(1_500_000)
        assert ee == 75_000    # 5%  × ₱15,000 = ₱750
        assert er == 153_000   # 10% × ₱15,000 + ₱30 EC = ₱1,530

    def test_just_below_ec_threshold(self):
        """₱14,000 salary — EC still ₱10 (MSC < ₱15,000)."""
        ee, er = compute_sss(1_400_000)
        assert ee == 70_000    # 5%  × ₱14,000 = ₱700
        assert er == 141_000   # 10% × ₱14,000 + ₱10 EC = ₱1,410

    def test_salary_25000(self):
        """₱25,000 salary — typical SME employee, EC = ₱30."""
        ee, er = compute_sss(2_500_000)
        assert ee == 125_000   # 5%  × ₱25,000 = ₱1,250
        assert er == 253_000   # 10% × ₱25,000 + ₱30 EC = ₱2,530

    def test_maximum_msc(self):
        """Salary at MSC max (₱35,000), EC = ₱30."""
        ee, er = compute_sss(3_500_000)
        assert ee == 175_000   # 5%  × ₱35,000 = ₱1,750
        assert er == 353_000   # 10% × ₱35,000 + ₱30 EC = ₱3,530

    def test_salary_above_maximum_msc(self):
        """Salary above MSC max — capped at ₱35,000, EC = ₱30."""
        ee, er = compute_sss(5_000_000)  # ₱50,000
        assert ee == 175_000   # capped at ₱35,000 MSC
        assert er == 353_000   # ₱3,500 + ₱30 EC = ₱3,530


# ============================================================
# PhilHealth Tests
# ============================================================

class TestPhilHealth:
    """PhilHealth contribution tests (2025: 5% total, 2.5% each side)."""

    def test_below_floor(self):
        """Salary below income floor (₱10,000) uses floor."""
        ee, er = compute_philhealth(500_000)  # ₱5,000
        # Clamped to ₱10,000
        assert ee == 25_000   # 2.5% of ₱10,000 = ₱250
        assert er == 25_000

    def test_at_floor(self):
        """Salary exactly at income floor (₱10,000)."""
        ee, er = compute_philhealth(1_000_000)
        assert ee == 25_000
        assert er == 25_000

    def test_mid_range(self):
        """₱25,000 salary."""
        ee, er = compute_philhealth(2_500_000)
        assert ee == 62_500    # 2.5% of ₱25,000 = ₱625
        assert er == 62_500

    def test_at_ceiling(self):
        """Salary at income ceiling (₱100,000)."""
        ee, er = compute_philhealth(10_000_000)
        assert ee == 250_000   # 2.5% of ₱100,000 = ₱2,500
        assert er == 250_000

    def test_above_ceiling(self):
        """Salary above ceiling uses ceiling."""
        ee, er = compute_philhealth(15_000_000)  # ₱150,000
        assert ee == 250_000   # capped at ceiling
        assert er == 250_000


# ============================================================
# Pag-IBIG Tests
# ============================================================

class TestPagIBIG:
    """Pag-IBIG contribution tests (Circular 460)."""

    def test_low_salary_rate(self):
        """Salary ≤ ₱1,500 gets 1% employee rate."""
        ee, er = compute_pagibig(150_000)  # ₱1,500
        assert ee == 1_500     # 1% of ₱1,500 = ₱15
        assert er == 3_000     # 2% of ₱1,500 = ₱30

    def test_below_low_threshold(self):
        """Salary below ₱1,500 — uses 1% rate."""
        ee, er = compute_pagibig(100_000)  # ₱1,000
        assert ee == 1_000     # 1% of ₱1,000 = ₱10
        assert er == 2_000     # 2% of ₱1,000 = ₱20

    def test_normal_rate(self):
        """Salary above ₱1,500 — uses 2% rate."""
        ee, er = compute_pagibig(800_000)  # ₱8,000
        assert ee == 16_000    # 2% of ₱8,000 = ₱160
        assert er == 16_000    # 2% of ₱8,000 = ₱160

    def test_at_max_fund_salary(self):
        """Salary at max fund salary (₱10,000)."""
        ee, er = compute_pagibig(1_000_000)
        assert ee == 20_000    # 2% of ₱10,000 = ₱200
        assert er == 20_000

    def test_above_max_fund_salary(self):
        """Salary above max fund salary — capped at ₱10,000."""
        ee, er = compute_pagibig(5_000_000)  # ₱50,000
        assert ee == 20_000    # capped: 2% of ₱10,000 = ₱200
        assert er == 20_000


# ============================================================
# BIR Withholding Tax Tests
# ============================================================

class TestWithholdingTax:
    """BIR monthly withholding tax (TRAIN Law brackets)."""

    def test_zero_income(self):
        """No taxable income = no tax."""
        assert compute_withholding_tax(0) == 0

    def test_negative_income(self):
        """Negative taxable income = no tax."""
        assert compute_withholding_tax(-100_000) == 0

    def test_below_first_bracket(self):
        """₱15,000 taxable — within 0% bracket (≤₱20,833)."""
        tax = compute_withholding_tax(1_500_000)
        assert tax == 0

    def test_exactly_at_first_bracket(self):
        """₱20,833 — upper edge of 0% bracket."""
        tax = compute_withholding_tax(2_083_300)
        assert tax == 0

    def test_second_bracket(self):
        """₱25,000 taxable — falls in 20% bracket.
        Tax = 20% of (₱25,000 - ₱20,833) = 20% of ₱4,167 = ₱833.40
        In centavos: 20% of 416_700 = 83_340
        """
        tax = compute_withholding_tax(2_500_000)
        assert tax == 83_340

    def test_third_bracket(self):
        """₱50,000 taxable — falls in 25% bracket.
        Tax = ₱2,500 + 25% of (₱50,000 - ₱33,333) = ₱2,500 + 25% of ₱16,667
             = ₱2,500 + ₱4,166.75 = ₱6,666.75
        In centavos: 250_000 + 25% of 1_666_700 = 250_000 + 416_675 = 666_675
        """
        tax = compute_withholding_tax(5_000_000)
        assert tax == 666_675

    def test_fourth_bracket(self):
        """₱100,000 taxable — falls in 30% bracket.
        Tax = ₱10,833 + 30% of (₱100,000 - ₱66,667) = ₱10,833 + 30% of ₱33,333
             = ₱10,833 + ₱9,999.90 = ₱20,832.90
        In centavos: 1_083_300 + 30% of 3_333_300 = 1_083_300 + 999_990 = 2_083_290
        """
        tax = compute_withholding_tax(10_000_000)
        assert tax == 2_083_290

    def test_minimum_wage_no_tax(self):
        """NCR minimum wage earner (₱610/day × 26 days = ₱15,860/month).
        After deductions, well below ₱20,833 threshold = no tax.
        """
        tax = compute_withholding_tax(1_586_000)
        assert tax == 0


# ============================================================
# Full Payroll Computation Tests
# ============================================================

class TestFullPayroll:
    """End-to-end payroll computation for realistic scenarios."""

    def test_minimum_wage_worker(self):
        """NCR minimum wage: ₱610/day × 26 days = ₱15,860/month.
        Should have minimal deductions and zero withholding tax.
        """
        result = compute_payroll(gross_pay=1_586_000)

        # SSS: MSC clamped to ₱15,860 (within range)
        # 5% of ₱15,860 = ₱793 = 79_300
        assert result.sss_employee == 79_300

        # PhilHealth: 2.5% of ₱15,860 = ₱396.50 = 39_650
        assert result.philhealth_employee == 39_650

        # Pag-IBIG: 2% of ₱10,000 (capped) = ₱200
        assert result.pagibig_employee == 20_000

        # Taxable = ₱15,860 - ₱793 - ₱396.50 - ₱200 = ₱14,470.50
        assert result.taxable_income == 1_447_050

        # Below ₱20,833 = 0 tax
        assert result.withholding_tax == 0

        # Net = gross - SSS_ee - PH_ee - PI_ee - WHT
        expected_net = 1_586_000 - 79_300 - 39_650 - 20_000 - 0
        assert result.net_pay == expected_net

    def test_typical_sme_employee_25k(self):
        """₱25,000/month — common SME salary.
        Should have moderate deductions and some withholding tax.
        """
        result = compute_payroll(gross_pay=2_500_000)

        # SSS: 5% of ₱25,000 = ₱1,250 (employee); 10% × ₱25,000 + ₱30 EC = ₱2,530 (employer)
        assert result.sss_employee == 125_000
        assert result.sss_employer == 253_000

        # PhilHealth: 2.5% of ₱25,000 = ₱625
        assert result.philhealth_employee == 62_500
        assert result.philhealth_employer == 62_500

        # Pag-IBIG: 2% of ₱10,000 (capped) = ₱200
        assert result.pagibig_employee == 20_000
        assert result.pagibig_employer == 20_000

        # Taxable = ₱25,000 - ₱1,250 - ₱625 - ₱200 = ₱22,925
        assert result.taxable_income == 2_292_500

        # ₱22,925 is in 2nd bracket (₱20,833–₱33,332)
        # Tax = 20% of (₱22,925 - ₱20,833) = 20% of ₱2,092 = ₱418.40
        expected_tax = int(round(2_292_500 - 2_083_300) * 0.20)
        # = int(round(209_200 * 0.20)) = int(round(41_840)) = 41_840
        assert result.withholding_tax == 41_840

        # Net = 2,500,000 - 125,000 - 62,500 - 20,000 - 41,840 = 2,250,660
        assert result.net_pay == 2_250_660

    def test_employee_35k_with_allowances(self):
        """₱35,000/month with ₱5,000 non-taxable meal/rice allowance.
        Gross is ₱35,000 but only ₱30,000 is taxable base.
        """
        result = compute_payroll(
            gross_pay=3_500_000,
            nontaxable_allowances=500_000,
        )

        # Contributions based on taxable gross (₱30,000)
        # SSS: 5% of ₱30,000 = ₱1,500 (employee); 10% × ₱30,000 + ₱30 EC = ₱3,030 (employer)
        assert result.sss_employee == 150_000
        assert result.sss_employer == 303_000

        # PhilHealth: 2.5% of ₱30,000 = ₱750
        assert result.philhealth_employee == 75_000

        # Pag-IBIG: 2% of ₱10,000 (capped) = ₱200
        assert result.pagibig_employee == 20_000

        # Taxable = ₱30,000 - ₱1,500 - ₱750 - ₱200 = ₱27,550
        assert result.taxable_income == 2_755_000

        # ₱27,550 is in 2nd bracket
        # Tax = 20% of (₱27,550 - ₱20,833) = 20% of ₱6,717 = ₱1,343.40
        expected_tax = int(round((2_755_000 - 2_083_300) * 0.20))
        assert result.withholding_tax == expected_tax

        # Net = ₱35,000 - SSS_ee - PH_ee - PI_ee - WHT
        expected_net = 3_500_000 - 150_000 - 75_000 - 20_000 - expected_tax
        assert result.net_pay == expected_net

    def test_high_salary_50k(self):
        """₱50,000/month — manager level."""
        result = compute_payroll(gross_pay=5_000_000)

        # SSS: MSC capped at ₱35,000. 5% = ₱1,750 (employee); 10% × ₱35,000 + ₱30 EC = ₱3,530 (employer)
        assert result.sss_employee == 175_000
        assert result.sss_employer == 353_000

        # PhilHealth: 2.5% of ₱50,000 = ₱1,250
        assert result.philhealth_employee == 125_000

        # Pag-IBIG: capped at ₱200
        assert result.pagibig_employee == 20_000

        # Taxable = ₱50,000 - ₱1,750 - ₱1,250 - ₱200 = ₱46,800
        assert result.taxable_income == 4_680_000

        # ₱46,800 is in 3rd bracket (₱33,333–₱66,666)
        # Tax = ₱2,500 + 25% of (₱46,800 - ₱33,333) = ₱2,500 + 25% of ₱13,467
        #      = ₱2,500 + ₱3,366.75 = ₱5,866.75
        expected_tax = 250_000 + int(round((4_680_000 - 3_333_300) * 0.25))
        assert result.withholding_tax == expected_tax

    def test_very_low_salary(self):
        """₱5,000/month — part-time or very low wage."""
        result = compute_payroll(gross_pay=500_000)

        # SSS: MSC floor ₱5,000. 5% = ₱250
        assert result.sss_employee == 25_000

        # PhilHealth: floor ₱10,000. 2.5% = ₱250
        assert result.philhealth_employee == 25_000

        # Pag-IBIG: 2% of ₱5,000 = ₱100
        assert result.pagibig_employee == 10_000

        # Zero tax (well below threshold)
        assert result.withholding_tax == 0

        # Net = 500,000 - 25,000 - 25,000 - 10,000 = 440,000
        assert result.net_pay == 440_000

    def test_net_pay_always_positive_for_normal_salaries(self):
        """Verify net pay doesn't go negative for any normal salary range."""
        for salary_pesos in range(5_000, 100_001, 5_000):
            salary_centavos = salary_pesos * 100
            result = compute_payroll(gross_pay=salary_centavos)
            assert result.net_pay > 0, (
                f"Net pay went negative for ₱{salary_pesos:,} salary"
            )

    def test_total_deductions_breakdown(self):
        """Verify total_mandatory_deductions = SSS_ee + PH_ee + PI_ee + WHT."""
        result = compute_payroll(gross_pay=3_000_000)  # ₱30,000
        expected_total = (
            result.sss_employee
            + result.philhealth_employee
            + result.pagibig_employee
            + result.withholding_tax
        )
        assert result.total_mandatory_deductions == expected_total

    def test_net_pay_formula(self):
        """Verify net_pay = gross_pay - total_mandatory_deductions."""
        result = compute_payroll(gross_pay=2_000_000)  # ₱20,000
        assert result.net_pay == result.gross_pay - result.total_mandatory_deductions
