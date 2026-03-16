-- ============================================================
-- Migration 009: Company-Specific Custom Holidays
-- ============================================================
-- Extends the holidays table to support company-specific entries
-- alongside the national holidays that are shared across all companies.
--
-- company_id IS NULL  → national/proclamation holiday (read-only for all)
-- company_id IS SET   → company-added custom holiday (local govt, anniversary, etc.)
-- ============================================================

-- Add company_id column (nullable — NULL = national holiday)
ALTER TABLE holidays
  ADD COLUMN IF NOT EXISTS company_id UUID REFERENCES companies(id) ON DELETE CASCADE;

-- Drop the old unique constraint that only considered date + name
ALTER TABLE holidays
  DROP CONSTRAINT IF EXISTS holidays_holiday_date_name_key;

-- New unique constraint: same date + name is fine across different companies,
-- but a single company can't add the same named holiday on the same date twice.
ALTER TABLE holidays
  ADD CONSTRAINT holidays_date_name_company_key
  UNIQUE (holiday_date, name, company_id);

-- ============================================================
-- RLS remains open (dev policy covers all operations).
-- Production-ready policies would scope SELECT to:
--   company_id IS NULL OR company_id = auth_company_id()
-- and INSERT/UPDATE/DELETE to:
--   company_id = auth_company_id() (cannot touch national holidays)
-- ============================================================
