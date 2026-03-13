-- ============================================================
-- DEV SETUP: Run this in Supabase SQL Editor (Dashboard > SQL)
-- This combines schema + seed + dev-friendly RLS
-- ============================================================
-- Run 001_schema.sql first, then 002_seed_government_rates.sql,
-- then this file to open up RLS for development.
-- ============================================================

-- During development, allow all operations via anon key.
-- IMPORTANT: Replace these with proper policies before going to production!

-- Drop restrictive policies and add permissive dev policies
-- COMPANIES
DROP POLICY IF EXISTS companies_select ON companies;
DROP POLICY IF EXISTS companies_insert ON companies;
DROP POLICY IF EXISTS companies_update ON companies;
DROP POLICY IF EXISTS companies_delete ON companies;
CREATE POLICY dev_companies_all ON companies FOR ALL USING (true) WITH CHECK (true);

-- EMPLOYEES
DROP POLICY IF EXISTS employees_select ON employees;
DROP POLICY IF EXISTS employees_insert ON employees;
DROP POLICY IF EXISTS employees_update ON employees;
DROP POLICY IF EXISTS employees_delete ON employees;
CREATE POLICY dev_employees_all ON employees FOR ALL USING (true) WITH CHECK (true);

-- PAY_PERIODS
DROP POLICY IF EXISTS pay_periods_select ON pay_periods;
DROP POLICY IF EXISTS pay_periods_insert ON pay_periods;
DROP POLICY IF EXISTS pay_periods_update ON pay_periods;
DROP POLICY IF EXISTS pay_periods_delete ON pay_periods;
CREATE POLICY dev_pay_periods_all ON pay_periods FOR ALL USING (true) WITH CHECK (true);

-- PAYROLL_ENTRIES
DROP POLICY IF EXISTS payroll_entries_select ON payroll_entries;
DROP POLICY IF EXISTS payroll_entries_insert ON payroll_entries;
DROP POLICY IF EXISTS payroll_entries_update ON payroll_entries;
DROP POLICY IF EXISTS payroll_entries_delete ON payroll_entries;
CREATE POLICY dev_payroll_entries_all ON payroll_entries FOR ALL USING (true) WITH CHECK (true);

-- DEDUCTION_TYPES
DROP POLICY IF EXISTS deduction_types_select ON deduction_types;
DROP POLICY IF EXISTS deduction_types_insert ON deduction_types;
DROP POLICY IF EXISTS deduction_types_update ON deduction_types;
DROP POLICY IF EXISTS deduction_types_delete ON deduction_types;
CREATE POLICY dev_deduction_types_all ON deduction_types FOR ALL USING (true) WITH CHECK (true);

-- USER_COMPANY_ACCESS
DROP POLICY IF EXISTS uca_select ON user_company_access;
DROP POLICY IF EXISTS uca_insert ON user_company_access;
DROP POLICY IF EXISTS uca_delete ON user_company_access;
CREATE POLICY dev_uca_all ON user_company_access FOR ALL USING (true) WITH CHECK (true);

-- GOVERNMENT_RATES
DROP POLICY IF EXISTS gov_rates_select ON government_rates;
CREATE POLICY dev_gov_rates_all ON government_rates FOR ALL USING (true) WITH CHECK (true);

-- SYNC_QUEUE
CREATE POLICY dev_sync_queue_all ON sync_queue FOR ALL USING (true) WITH CHECK (true);
