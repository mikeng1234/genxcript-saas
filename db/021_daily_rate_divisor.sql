-- ============================================================
-- Migration 021: daily_rate_divisor on companies
-- Determines how monthly salary is divided to get the daily rate.
-- Common values:
--   26 = standard (DOLE default, 5-day workweek)
--   22 = actual working days average (no pay on rest days + holidays)
--   30 = calendar days (rare, used by some companies for uniformity)
-- ============================================================

ALTER TABLE companies
  ADD COLUMN IF NOT EXISTS daily_rate_divisor INTEGER NOT NULL DEFAULT 26
    CHECK (daily_rate_divisor BETWEEN 1 AND 31);

COMMENT ON COLUMN companies.daily_rate_divisor IS
  'Divisor used for computing daily rate from monthly salary. '
  'Affects absent deductions. Typical values: 22, 26, 30. Default 26 per DOLE.';
