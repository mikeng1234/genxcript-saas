-- 029: Module-based subscription system
-- Adds enabled_modules JSONB column and subscription metadata to companies table.
-- Module keys: core, payroll, attendance, leave_ot, supervisor, analytics, compliance

ALTER TABLE companies
ADD COLUMN IF NOT EXISTS enabled_modules jsonb
DEFAULT '["core","payroll","attendance","leave_ot","supervisor","analytics","compliance"]'::jsonb;

ALTER TABLE companies
ADD COLUMN IF NOT EXISTS subscription_tier text
DEFAULT 'enterprise';

ALTER TABLE companies
ADD COLUMN IF NOT EXISTS subscription_start date;

ALTER TABLE companies
ADD COLUMN IF NOT EXISTS subscription_end date;

ALTER TABLE companies
ADD COLUMN IF NOT EXISTS max_employees integer DEFAULT 999;

-- Existing companies get all modules (enterprise)
UPDATE companies SET
  enabled_modules = '["core","payroll","attendance","leave_ot","supervisor","analytics","compliance"]'::jsonb,
  subscription_tier = 'enterprise',
  max_employees = 999
WHERE enabled_modules IS NULL;
