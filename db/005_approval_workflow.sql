-- ============================================================
-- 005: Payroll Approval Workflow
-- Adds review/approval step before finalization.
-- Status flow: draft → reviewed → finalized → paid
-- ============================================================

-- Add reviewer tracking columns
ALTER TABLE pay_periods
    ADD COLUMN reviewed_by TEXT,
    ADD COLUMN reviewed_at TIMESTAMPTZ;

-- Update status check constraint to include 'reviewed'
ALTER TABLE pay_periods
    DROP CONSTRAINT IF EXISTS pay_periods_status_check;

ALTER TABLE pay_periods
    ADD CONSTRAINT pay_periods_status_check
    CHECK (status IN ('draft', 'reviewed', 'finalized', 'paid'));
