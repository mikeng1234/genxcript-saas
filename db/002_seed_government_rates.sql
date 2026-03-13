-- ============================================================
-- Seed: GOVERNMENT_RATES — 2025 Philippine Contribution Rates
-- ============================================================
-- Values stored in JSONB for flexibility.
-- Monetary amounts in centavos where applicable.
-- ============================================================

-- ============================================================
-- SSS (per SSS Circular 2024-06, effective January 2025)
-- Total: 15% of MSC (Employee 5%, Employer 10% + EC)
-- ============================================================

INSERT INTO government_rates (agency, rate_type, value, effective_date) VALUES

-- SSS contribution rates
('SSS', 'contribution_rate', '{
    "total_rate": 0.15,
    "employee_rate": 0.05,
    "employer_rate": 0.10,
    "msc_min": 500000,
    "msc_max": 3500000,
    "max_employee_contribution": 175000,
    "max_employer_contribution": 353000,
    "description": "SSS Circular 2024-06. MSC range ₱5,000–₱35,000. Employer share includes EC."
}', '2025-01-01'),

-- ============================================================
-- PhilHealth (RA 11223, UHC Law, 2025)
-- Total: 5% (Employee 2.5%, Employer 2.5%)
-- ============================================================

('PhilHealth', 'contribution_rate', '{
    "total_rate": 0.05,
    "employee_rate": 0.025,
    "employer_rate": 0.025,
    "income_floor": 1000000,
    "income_ceiling": 10000000,
    "min_contribution": 50000,
    "max_contribution": 250000,
    "description": "RA 11223 UHC Law. 5% of basic salary, split equally. Floor ₱10,000, ceiling ₱100,000."
}', '2025-01-01'),

-- ============================================================
-- Pag-IBIG / HDMF (Circular No. 460, effective Feb 2024)
-- Employee: 2% (1% if salary ≤ ₱1,500)
-- Employer: 2%
-- Max fund salary: ₱10,000
-- ============================================================

('PagIBIG', 'contribution_rate', '{
    "employee_rate_normal": 0.02,
    "employee_rate_low": 0.01,
    "low_salary_threshold": 150000,
    "employer_rate": 0.02,
    "max_fund_salary": 1000000,
    "max_employee_contribution": 20000,
    "max_employer_contribution": 20000,
    "description": "Circular 460. Employee 2% (1% if ≤₱1,500). Employer 2%. Max fund salary ₱10,000."
}', '2024-02-01'),

-- ============================================================
-- BIR Withholding Tax — TRAIN Law (RA 10963)
-- Monthly brackets, effective 2023 onwards
-- All amounts in centavos
-- ============================================================

('BIR', 'monthly_tax_brackets', '{
    "brackets": [
        {"min": 0,        "max": 2083300,  "base_tax": 0,        "rate": 0.00, "over": 0},
        {"min": 2083300,  "max": 3333200,  "base_tax": 0,        "rate": 0.20, "over": 2083300},
        {"min": 3333300,  "max": 6666600,  "base_tax": 250000,   "rate": 0.25, "over": 3333300},
        {"min": 6666700,  "max": 16666600, "base_tax": 1083300,  "rate": 0.30, "over": 6666700},
        {"min": 16666700, "max": 66666600, "base_tax": 4083300,  "rate": 0.32, "over": 16666700},
        {"min": 66666700, "max": null,     "base_tax": 20083300, "rate": 0.35, "over": 66666700}
    ],
    "description": "TRAIN Law RA 10963, monthly withholding tax brackets, effective 2023 onwards."
}', '2023-01-01'),

-- ============================================================
-- BIR De Minimis Benefits (non-taxable limits)
-- Amounts in centavos
-- ============================================================

('BIR', 'de_minimis_limits', '{
    "meal_allowance_per_meal": 2500,
    "meal_allowance_annual": 600000,
    "rice_subsidy_monthly": 200000,
    "clothing_allowance_annual": 600000,
    "medical_allowance_annual": 1000000,
    "thirteenth_month_nontaxable": 9000000,
    "description": "BIR de minimis benefit limits. Amounts within these limits are non-taxable."
}', '2023-01-01'),

-- ============================================================
-- Labor Code Reference Rates
-- ============================================================

('BIR', 'labor_code_rates', '{
    "regular_holiday_multiplier": 2.00,
    "special_holiday_multiplier": 1.30,
    "overtime_regular_premium": 0.25,
    "overtime_restday_premium": 0.30,
    "night_differential_premium": 0.10,
    "night_diff_start": "22:00",
    "night_diff_end": "06:00",
    "service_incentive_leave_days": 5,
    "ncr_minimum_daily_wage": 61000,
    "description": "Labor Code rates. NCR non-agriculture minimum wage effective June 2024."
}', '2024-06-01');
