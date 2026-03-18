-- ============================================================
-- Migration 019: Holiday Observed/Adjusted Date
-- ============================================================
-- Adds an optional observed_date column to the holidays table.
-- When set, this overrides holiday_date for DTR/payroll purposes
-- (e.g., a Monday holiday moved to Friday to extend a weekend).
--
-- Run once in Supabase SQL Editor AFTER 018_company_hr_policy.sql.
-- ============================================================

ALTER TABLE holidays
  ADD COLUMN IF NOT EXISTS observed_date DATE;

COMMENT ON COLUMN holidays.observed_date IS
  'When set, this date is used instead of holiday_date for DTR and payroll '
  'computations. Allows holidays that fall on weekends to be observed on '
  'a nearby weekday, or government-declared holiday adjustments.';
