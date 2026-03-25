-- Add optional "require break clock" toggle to schedule profiles
-- When TRUE, employees on this shift must use Start Break / End Break in the portal
-- When FALSE (default), the scheduled break is implied (deducted automatically)
ALTER TABLE public.schedules ADD COLUMN IF NOT EXISTS require_break_clock BOOLEAN DEFAULT FALSE;
