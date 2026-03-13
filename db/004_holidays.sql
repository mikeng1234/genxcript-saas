-- ============================================================
-- Philippine Holidays Table
-- ============================================================
-- Stores regular holidays, special non-working days, and
-- special working days declared by the Philippine government.
-- Updated annually when the president signs the holiday proclamation.
-- ============================================================

CREATE TABLE IF NOT EXISTS holidays (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    holiday_date    DATE NOT NULL,
    name            TEXT NOT NULL,
    type            TEXT NOT NULL
                    CHECK (type IN ('regular', 'special_non_working', 'special_working')),
    year            INTEGER NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (holiday_date, name)
);

CREATE INDEX idx_holidays_date ON holidays (holiday_date);
CREATE INDEX idx_holidays_year ON holidays (year);

-- Enable RLS (dev policy: open access)
ALTER TABLE holidays ENABLE ROW LEVEL SECURITY;
CREATE POLICY dev_holidays_all ON holidays FOR ALL USING (true) WITH CHECK (true);

-- ============================================================
-- 2025 Philippine Holidays
-- (Based on Proclamation No. 727, s. 2024 and subsequent amendments)
-- ============================================================

INSERT INTO holidays (holiday_date, name, type, year) VALUES

-- Regular Holidays 2025
('2025-01-01', 'New Year''s Day', 'regular', 2025),
('2025-04-17', 'Maundy Thursday', 'regular', 2025),
('2025-04-18', 'Good Friday', 'regular', 2025),
('2025-04-09', 'Araw ng Kagitingan (Day of Valor)', 'regular', 2025),
('2025-05-01', 'Labor Day', 'regular', 2025),
('2025-06-12', 'Independence Day', 'regular', 2025),
('2025-08-25', 'National Heroes Day', 'regular', 2025),
('2025-11-30', 'Bonifacio Day', 'regular', 2025),
('2025-12-25', 'Christmas Day', 'regular', 2025),
('2025-12-30', 'Rizal Day', 'regular', 2025),
('2025-03-31', 'Eid''l Fitr (Feast of Ramadan)', 'regular', 2025),
('2025-06-07', 'Eid''l Adha (Feast of Sacrifice)', 'regular', 2025),

-- Special Non-Working Days 2025
('2025-01-29', 'Chinese New Year', 'special_non_working', 2025),
('2025-02-25', 'EDSA People Power Anniversary', 'special_non_working', 2025),
('2025-04-19', 'Black Saturday', 'special_non_working', 2025),
('2025-08-21', 'Ninoy Aquino Day', 'special_non_working', 2025),
('2025-11-01', 'All Saints'' Day', 'special_non_working', 2025),
('2025-12-08', 'Feast of the Immaculate Conception', 'special_non_working', 2025),
('2025-12-24', 'Christmas Eve', 'special_non_working', 2025),
('2025-12-31', 'Last Day of the Year', 'special_non_working', 2025),

-- ============================================================
-- 2026 Philippine Holidays (Projected — update when proclamation is issued)
-- Dates for moveable feasts (Easter, Eid) are estimates
-- ============================================================

-- Regular Holidays 2026
('2026-01-01', 'New Year''s Day', 'regular', 2026),
('2026-04-02', 'Maundy Thursday', 'regular', 2026),
('2026-04-03', 'Good Friday', 'regular', 2026),
('2026-04-09', 'Araw ng Kagitingan (Day of Valor)', 'regular', 2026),
('2026-05-01', 'Labor Day', 'regular', 2026),
('2026-06-12', 'Independence Day', 'regular', 2026),
('2026-08-31', 'National Heroes Day', 'regular', 2026),
('2026-11-30', 'Bonifacio Day', 'regular', 2026),
('2026-12-25', 'Christmas Day', 'regular', 2026),
('2026-12-30', 'Rizal Day', 'regular', 2026),
('2026-03-20', 'Eid''l Fitr (Feast of Ramadan)', 'regular', 2026),
('2026-05-27', 'Eid''l Adha (Feast of Sacrifice)', 'regular', 2026),

-- Special Non-Working Days 2026
('2026-02-17', 'Chinese New Year', 'special_non_working', 2026),
('2026-02-25', 'EDSA People Power Anniversary', 'special_non_working', 2026),
('2026-04-04', 'Black Saturday', 'special_non_working', 2026),
('2026-08-21', 'Ninoy Aquino Day', 'special_non_working', 2026),
('2026-11-01', 'All Saints'' Day', 'special_non_working', 2026),
('2026-12-08', 'Feast of the Immaculate Conception', 'special_non_working', 2026),
('2026-12-24', 'Christmas Eve', 'special_non_working', 2026),
('2026-12-31', 'Last Day of the Year', 'special_non_working', 2026);
