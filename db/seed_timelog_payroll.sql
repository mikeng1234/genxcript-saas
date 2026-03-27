-- ============================================================
-- SEED: 5-Month Payroll & Attendance Data
-- ============================================================
-- Period   : October 2025 – February 2026  (5 monthly pay periods)
-- Requires : seed_test_company.sql already run (creates 25 employees)
-- Run AFTER all migrations 001–020 in Supabase SQL Editor.
--
-- Creates:
--   • 2 shift schedules        Standard Day (08:00–17:00) + Night Shift (22:00–06:00)
--   • 1 leave template         Standard Regular (15 VL / 15 SL / 5 CL)
--   • 5 pay periods            Oct 2025 → Feb 2026  (finalized/finalized/finalized/reviewed/draft)
--   • 125 payroll entries      25 employees × 5 months  with TRAIN Law deductions
--   • ~2,600 time logs         Mon–Fri across 5 months  with realistic late/OT/absent patterns
--   • 8 approved leave reqs    VL/SL/CL across various employees and months
--   • 10 approved OT requests  Dev-team sprint support (Nov, Dec, Jan)
-- ============================================================

DO $$
DECLARE
  v_cid   UUID;   -- company id

  -- Schedules
  s_day   UUID;   -- Standard Day  08:00–17:00  Mon–Fri  60 min break
  s_night UUID;   -- Night Shift   22:00–06:00  Mon–Fri  30 min break (overnight)

  -- Leave template
  t_std   UUID;

  -- Loop records
  emp_rec    RECORD;
  period_rec RECORD;

  -- ── Payroll computation variables (all monetary in centavos) ──────────────
  v_basic       BIGINT;    -- basic_salary (centavos)
  v_salary_php  NUMERIC;   -- basic in PHP
  v_hourly_php  NUMERIC;   -- hourly rate in PHP  (÷ 26 days × 8 hrs)
  v_msc         NUMERIC;   -- SSS monthly salary credit (PHP)
  v_sss_ee      BIGINT;
  v_sss_er      BIGINT;
  v_phic_ee     BIGINT;
  v_phic_er     BIGINT;
  v_hdmf_ee     BIGINT;
  v_hdmf_er     BIGINT;
  v_taxable     NUMERIC;
  v_wtax        BIGINT;
  v_ot_pay      BIGINT;
  v_nsd_pay     BIGINT;
  v_13th        BIGINT;
  v_gross       BIGINT;
  v_tot_ded     BIGINT;
  v_net         BIGINT;
  v_month       INT;
  v_is_sprint   BOOLEAN;   -- TRUE for Nov / Dec / Jan (dev team sprint months)

  -- ── Time log loop variables ───────────────────────────────────────────────
  v_date       DATE;
  v_dow        INT;
  v_day_num    INT;
  v_emp_seq    INT;   -- 1–25 parsed from employee_no
  v_seed       INT;   -- deterministic variation seed [0..99]

  -- Employee attendance personality
  v_late_pct   INT;   -- % of days that are late
  v_late_min   INT;   -- typical late minutes when late
  v_ot_pct     INT;   -- % of days with overtime
  v_ot_hrs_typ NUMERIC; -- typical OT hours when OT
  v_absent_pct INT;   -- % of days absent
  v_is_night   BOOLEAN; -- night-shift employee

  -- Per-day computed values
  v_late      INT;
  v_ut        INT;
  v_ot_hrs    NUMERIC;
  v_gross_hrs NUMERIC;
  v_nsd_hrs   NUMERIC;
  v_time_in   TIME;
  v_time_out  TIME;

BEGIN

  -- ── Validate prerequisite ─────────────────────────────────────────────────
  SELECT id INTO v_cid FROM companies WHERE name = 'GeNXcript Tech Solutions';
  IF v_cid IS NULL THEN
    RAISE EXCEPTION 'Company "GeNXcript Tech Solutions" not found. Run seed_test_company.sql first.';
  END IF;

  -- ═══════════════════════════════════════════════════════════════════════════
  -- 0. CLEANUP  (makes the script re-runnable / idempotent)
  --    Delete all data previously seeded for this company so we can start fresh.
  -- ═══════════════════════════════════════════════════════════════════════════

  -- Clear FK references on employees before dropping schedules / templates
  UPDATE employees SET schedule_id = NULL, leave_template_id = NULL
    WHERE company_id = v_cid;

  -- Cascade-delete pay_periods → payroll_entries
  DELETE FROM pay_periods        WHERE company_id = v_cid;

  -- Direct deletes (no cascade needed)
  DELETE FROM time_logs          WHERE company_id = v_cid;
  DELETE FROM leave_requests     WHERE company_id = v_cid;
  DELETE FROM overtime_requests  WHERE company_id = v_cid;

  -- Schedules and templates
  DELETE FROM schedules                    WHERE company_id = v_cid;
  DELETE FROM leave_entitlement_templates  WHERE company_id = v_cid;

  RAISE NOTICE 'Cleanup complete — re-seeding fresh data.';

  -- ═══════════════════════════════════════════════════════════════════════════
  -- 1. SCHEDULES
  -- ═══════════════════════════════════════════════════════════════════════════

  INSERT INTO schedules
    (company_id, name, start_time, end_time, break_minutes, work_days, is_overnight)
  VALUES
    (v_cid, 'Standard Day', '08:00', '17:00', 60,
     ARRAY['Mon','Tue','Wed','Thu','Fri'], FALSE)
  RETURNING id INTO s_day;

  INSERT INTO schedules
    (company_id, name, start_time, end_time, break_minutes, work_days, is_overnight)
  VALUES
    (v_cid, 'Night Shift', '22:00', '06:00', 30,
     ARRAY['Mon','Tue','Wed','Thu','Fri'], TRUE)
  RETURNING id INTO s_night;

  -- Everyone gets Standard Day; CS team (Gino, Leila, Ramon) gets Night Shift
  UPDATE employees SET schedule_id = s_day   WHERE company_id = v_cid;
  UPDATE employees SET schedule_id = s_night
    WHERE company_id = v_cid
      AND employee_no IN ('EMP-022', 'EMP-024', 'EMP-025');

  -- ═══════════════════════════════════════════════════════════════════════════
  -- 2. LEAVE ENTITLEMENT TEMPLATE
  -- ═══════════════════════════════════════════════════════════════════════════

  INSERT INTO leave_entitlement_templates
    (company_id, name, vl_days, sl_days, cl_days,
     carry_over_cap, convertible_to_cash, conversion_rate)
  VALUES
    (v_cid, 'Standard (Regular)', 15, 15, 5, 5, TRUE, 1.00)
  RETURNING id INTO t_std;

  UPDATE employees SET leave_template_id = t_std WHERE company_id = v_cid;

  -- ═══════════════════════════════════════════════════════════════════════════
  -- 3. PAY PERIODS  (monthly, Oct 2025 – Feb 2026)
  -- ═══════════════════════════════════════════════════════════════════════════

  INSERT INTO pay_periods
    (company_id, period_start, period_end, payment_date, status, reviewed_by)
  VALUES
    (v_cid, '2025-10-01', '2025-10-31', '2025-10-31', 'finalized', 'Lourdes Pineda'),
    (v_cid, '2025-11-01', '2025-11-30', '2025-11-28', 'finalized', 'Lourdes Pineda'),
    (v_cid, '2025-12-01', '2025-12-31', '2025-12-24', 'finalized', 'Lourdes Pineda'),
    (v_cid, '2026-01-01', '2026-01-31', '2026-01-31', 'reviewed',  'Lourdes Pineda'),
    (v_cid, '2026-02-01', '2026-02-28', '2026-02-27', 'draft',     NULL);

  -- ═══════════════════════════════════════════════════════════════════════════
  -- 4. PAYROLL ENTRIES  (25 employees × 5 periods = 125 rows)
  --
  --    2025 PH government contribution rates:
  --      SSS EE   : 4.5% of MSC  (max MSC ₱30,000 → max EE ₱1,350/mo)
  --      SSS ER   : 9.5% of MSC
  --      PhilHealth EE/ER : 2.5% each of LEAST(salary, ₱100,000)
  --      Pag-IBIG EE : 2% of salary, max ₱100; ER always ₱200
  --      Withholding tax  : TRAIN Law 2023+ monthly brackets (no exemptions)
  --
  --    Sprint months (Nov/Dec/Jan): dev team gets OT pay from approved OT requests
  --    December: all employees get 1/12 thirteenth-month accrual
  --    Night-shift employees: night_differential = 22 days × 7.5 NSD hrs × rate × 10%
  -- ═══════════════════════════════════════════════════════════════════════════

  FOR emp_rec IN (
    SELECT id, employee_no, basic_salary, salary_type
    FROM   employees
    WHERE  company_id = v_cid AND is_active
    ORDER  BY employee_no
  ) LOOP
    v_basic      := emp_rec.basic_salary;
    v_salary_php := v_basic / 100.0;
    v_hourly_php := v_salary_php / (26.0 * 8.0);   -- ÷ 26 days/mo × 8 hrs/day

    -- ── SSS (4.5% EE / 9.5% ER of monthly salary credit) ──────────────────
    v_msc    := LEAST(GREATEST(ROUND(v_salary_php / 500.0) * 500.0, 5000.0), 30000.0);
    v_sss_ee := ROUND(v_msc * 0.045)::BIGINT * 100;
    v_sss_er := ROUND(v_msc * 0.095)::BIGINT * 100;

    -- ── PhilHealth (2.5% EE = 2.5% ER, base capped at ₱100,000) ───────────
    v_phic_ee := ROUND(LEAST(v_salary_php, 100000.0) * 0.025)::BIGINT * 100;
    v_phic_er := v_phic_ee;

    -- ── Pag-IBIG (2% EE, max ₱100 = 10,000 centavos; ER always ₱200) ──────
    v_hdmf_ee := LEAST(ROUND(v_salary_php * 0.02)::BIGINT * 100, 10000::BIGINT);
    v_hdmf_er := 20000;

    -- ── Withholding tax via TRAIN Law 2023+ monthly brackets ───────────────
    v_taxable := v_salary_php - (v_sss_ee + v_phic_ee + v_hdmf_ee) / 100.0;
    v_wtax := CASE
      WHEN v_taxable <=   20833 THEN 0
      WHEN v_taxable <=   33332 THEN ROUND((v_taxable -   20833)    * 0.20)::BIGINT * 100
      WHEN v_taxable <=   66666 THEN ROUND((2500      + (v_taxable -  33333) * 0.25))::BIGINT * 100
      WHEN v_taxable <=  166666 THEN ROUND((10833.33  + (v_taxable -  66667) * 0.30))::BIGINT * 100
      WHEN v_taxable <=  666666 THEN ROUND((40833.33  + (v_taxable - 166667) * 0.32))::BIGINT * 100
      ELSE                           ROUND((200833.33 + (v_taxable - 666667) * 0.35))::BIGINT * 100
    END;

    -- ── Night differential (night-shift employees; avg 22 working days/mo) ─
    v_nsd_pay := CASE
      WHEN emp_rec.employee_no IN ('EMP-022', 'EMP-024', 'EMP-025')
        THEN ROUND(22.0 * 7.5 * v_hourly_php * 0.10 * 100.0)::BIGINT
      ELSE 0
    END;

    -- ── Insert one payroll entry per pay period ─────────────────────────────
    FOR period_rec IN (
      SELECT id, period_start
      FROM   pay_periods
      WHERE  company_id = v_cid
      ORDER  BY period_start
    ) LOOP
      v_month     := EXTRACT(MONTH FROM period_rec.period_start)::INT;
      v_is_sprint := v_month IN (11, 12, 1);   -- Nov / Dec / Jan

      -- Overtime pay: dev + lead team scale with sprint intensity
      v_ot_pay := CASE
        WHEN emp_rec.employee_no IN ('EMP-002','EMP-005','EMP-011','EMP-012') AND v_is_sprint
          THEN ROUND(14.0 * 2.5 * v_hourly_php * 1.25 * 100.0)::BIGINT
        WHEN emp_rec.employee_no IN ('EMP-013','EMP-014') AND v_is_sprint
          THEN ROUND(12.0 * 2.0 * v_hourly_php * 1.25 * 100.0)::BIGINT
        WHEN emp_rec.employee_no IN ('EMP-002','EMP-005','EMP-011','EMP-012') AND NOT v_is_sprint
          THEN ROUND( 5.0 * 1.5 * v_hourly_php * 1.25 * 100.0)::BIGINT
        WHEN emp_rec.employee_no IN ('EMP-013','EMP-014') AND NOT v_is_sprint
          THEN ROUND( 4.0 * 1.5 * v_hourly_php * 1.25 * 100.0)::BIGINT
        ELSE 0
      END;

      -- 13th-month accrual: December only (1/12 of annual basic)
      v_13th := CASE WHEN v_month = 12 THEN ROUND(v_basic / 12.0)::BIGINT ELSE 0 END;

      v_gross   := v_basic + v_ot_pay + v_nsd_pay + v_13th;
      v_tot_ded := v_sss_ee + v_phic_ee + v_hdmf_ee + v_wtax;
      v_net     := v_gross - v_tot_ded;

      INSERT INTO payroll_entries (
        pay_period_id, employee_id,
        basic_pay, overtime_pay, night_differential, thirteenth_month_accrual, gross_pay,
        sss_employee,    philhealth_employee,    pagibig_employee,
        sss_employer,    philhealth_employer,    pagibig_employer,
        withholding_tax, total_deductions, net_pay
      ) VALUES (
        period_rec.id, emp_rec.id,
        v_basic, v_ot_pay, v_nsd_pay, v_13th, v_gross,
        v_sss_ee, v_phic_ee, v_hdmf_ee,
        v_sss_er, v_phic_er, v_hdmf_er,
        v_wtax, v_tot_ded, v_net
      );
    END LOOP;
  END LOOP;

  -- ═══════════════════════════════════════════════════════════════════════════
  -- 5. TIME LOGS  (~2,600 rows)
  --
  --    For every working day (Mon–Fri) from 2025-10-01 to 2026-02-28.
  --    Each employee has an "attendance personality" that determines:
  --      • late_pct  — probability (%) of arriving late on any given day
  --      • late_min  — baseline late minutes when late (adds ±variation)
  --      • ot_pct    — probability (%) of staying past 17:00
  --      • ot_hrs    — typical OT duration when OT
  --      • absent_pct — probability (%) of being absent
  --      • is_night  — TRUE for CS team (EMP-022/024/025)
  --
  --    Deterministic variation formula:
  --      seed = (emp_seq × 7919 + day_num × 31) mod 100
  --    Produces a repeatable, non-trivial pattern per employee × day.
  -- ═══════════════════════════════════════════════════════════════════════════

  FOR emp_rec IN (
    SELECT id, employee_no
    FROM   employees
    WHERE  company_id = v_cid AND is_active
    ORDER  BY employee_no
  ) LOOP
    -- Parse sequence number from "EMP-NNN"
    v_emp_seq := CAST(SUBSTRING(emp_rec.employee_no FROM 5) AS INT);

    -- ── Assign attendance personality ──────────────────────────────────────
    CASE emp_rec.employee_no
      -- late_pct  late_min  ot_pct  ot_hrs  absent_pct  is_night
      WHEN 'EMP-001' THEN v_late_pct:= 0; v_late_min:= 0; v_ot_pct:= 5; v_ot_hrs_typ:=1.0; v_absent_pct:=2; v_is_night:=FALSE;
      WHEN 'EMP-002' THEN v_late_pct:=15; v_late_min:= 5; v_ot_pct:=60; v_ot_hrs_typ:=2.0; v_absent_pct:=2; v_is_night:=FALSE;
      WHEN 'EMP-003' THEN v_late_pct:= 0; v_late_min:= 0; v_ot_pct:= 5; v_ot_hrs_typ:=0.5; v_absent_pct:=2; v_is_night:=FALSE;
      WHEN 'EMP-004' THEN v_late_pct:=30; v_late_min:=10; v_ot_pct:= 5; v_ot_hrs_typ:=0.5; v_absent_pct:=5; v_is_night:=FALSE;
      WHEN 'EMP-005' THEN v_late_pct:=15; v_late_min:= 5; v_ot_pct:=65; v_ot_hrs_typ:=2.5; v_absent_pct:=1; v_is_night:=FALSE;
      WHEN 'EMP-006' THEN v_late_pct:=25; v_late_min:=10; v_ot_pct:=30; v_ot_hrs_typ:=1.5; v_absent_pct:=4; v_is_night:=FALSE;
      WHEN 'EMP-007' THEN v_late_pct:= 0; v_late_min:= 0; v_ot_pct:= 5; v_ot_hrs_typ:=0.5; v_absent_pct:=2; v_is_night:=FALSE;
      WHEN 'EMP-008' THEN v_late_pct:= 0; v_late_min:= 0; v_ot_pct:= 5; v_ot_hrs_typ:=0.5; v_absent_pct:=2; v_is_night:=FALSE;
      WHEN 'EMP-009' THEN v_late_pct:=35; v_late_min:=15; v_ot_pct:=30; v_ot_hrs_typ:=1.5; v_absent_pct:=4; v_is_night:=FALSE;
      WHEN 'EMP-010' THEN v_late_pct:=20; v_late_min:=10; v_ot_pct:=10; v_ot_hrs_typ:=1.0; v_absent_pct:=4; v_is_night:=FALSE;
      WHEN 'EMP-011' THEN v_late_pct:=20; v_late_min:= 5; v_ot_pct:=65; v_ot_hrs_typ:=2.5; v_absent_pct:=1; v_is_night:=FALSE;
      WHEN 'EMP-012' THEN v_late_pct:=20; v_late_min:= 5; v_ot_pct:=60; v_ot_hrs_typ:=2.0; v_absent_pct:=1; v_is_night:=FALSE;
      WHEN 'EMP-013' THEN v_late_pct:=10; v_late_min:= 5; v_ot_pct:=55; v_ot_hrs_typ:=2.0; v_absent_pct:=1; v_is_night:=FALSE;
      WHEN 'EMP-014' THEN v_late_pct:=30; v_late_min:=15; v_ot_pct:=35; v_ot_hrs_typ:=1.5; v_absent_pct:=3; v_is_night:=FALSE;
      WHEN 'EMP-015' THEN v_late_pct:=40; v_late_min:=20; v_ot_pct:=20; v_ot_hrs_typ:=1.0; v_absent_pct:=8; v_is_night:=FALSE;
      WHEN 'EMP-016' THEN v_late_pct:=30; v_late_min:=10; v_ot_pct:= 5; v_ot_hrs_typ:=0.5; v_absent_pct:=4; v_is_night:=FALSE;
      WHEN 'EMP-017' THEN v_late_pct:=40; v_late_min:=15; v_ot_pct:= 5; v_ot_hrs_typ:=0.5; v_absent_pct:=8; v_is_night:=FALSE;
      WHEN 'EMP-018' THEN v_late_pct:=35; v_late_min:=15; v_ot_pct:= 5; v_ot_hrs_typ:=0.5; v_absent_pct:=5; v_is_night:=FALSE;
      WHEN 'EMP-019' THEN v_late_pct:=30; v_late_min:=20; v_ot_pct:= 5; v_ot_hrs_typ:=0.5; v_absent_pct:=8; v_is_night:=FALSE;
      WHEN 'EMP-020' THEN v_late_pct:=45; v_late_min:=25; v_ot_pct:= 5; v_ot_hrs_typ:=0.5; v_absent_pct:=8; v_is_night:=FALSE;
      WHEN 'EMP-021' THEN v_late_pct:=25; v_late_min:=10; v_ot_pct:=20; v_ot_hrs_typ:=1.0; v_absent_pct:=4; v_is_night:=FALSE;
      WHEN 'EMP-022' THEN v_late_pct:=10; v_late_min:= 5; v_ot_pct:=20; v_ot_hrs_typ:=1.0; v_absent_pct:=4; v_is_night:=TRUE;
      WHEN 'EMP-023' THEN v_late_pct:= 5; v_late_min:= 5; v_ot_pct:= 5; v_ot_hrs_typ:=0.5; v_absent_pct:=4; v_is_night:=FALSE;
      WHEN 'EMP-024' THEN v_late_pct:=10; v_late_min:=10; v_ot_pct:=15; v_ot_hrs_typ:=1.0; v_absent_pct:=5; v_is_night:=TRUE;
      WHEN 'EMP-025' THEN v_late_pct:=20; v_late_min:=15; v_ot_pct:=10; v_ot_hrs_typ:=0.5; v_absent_pct:=8; v_is_night:=TRUE;
      ELSE                 v_late_pct:=10; v_late_min:= 5; v_ot_pct:=10; v_ot_hrs_typ:=1.0; v_absent_pct:=4; v_is_night:=FALSE;
    END CASE;

    -- ── Date loop ──────────────────────────────────────────────────────────
    v_day_num := 0;
    v_date    := '2025-10-01'::DATE;

    WHILE v_date <= '2026-02-28'::DATE LOOP
      v_dow := EXTRACT(DOW FROM v_date)::INT;   -- 0=Sun … 6=Sat

      IF v_dow BETWEEN 1 AND 5 THEN             -- weekdays only (Mon–Fri)
        v_day_num := v_day_num + 1;
        -- Deterministic seed [0–99]
        v_seed := (v_emp_seq * 7919 + v_day_num * 31) % 100;

        -- ── ABSENT ─────────────────────────────────────────────────────────
        IF v_seed < v_absent_pct THEN
          INSERT INTO time_logs
            (company_id, employee_id, work_date, status,
             late_minutes, undertime_minutes, ot_hours, gross_hours, nsd_hours)
          VALUES
            (v_cid, emp_rec.id, v_date, 'absent', 0, 0, 0.0, 0.0, 0.0);

        -- ── NIGHT SHIFT ────────────────────────────────────────────────────
        ELSIF v_is_night THEN
          v_late   := CASE WHEN v_seed < v_late_pct
                        THEN v_late_min + (v_seed % 10)
                        ELSE 0 END;
          v_ot_hrs := CASE WHEN v_seed >= (100 - v_ot_pct)
                        THEN v_ot_hrs_typ + (v_seed % 20)::NUMERIC / 60.0
                        ELSE 0.0 END;
          v_time_in   := TIME '22:00' + (v_late * INTERVAL '1 minute');
          v_time_out  := TIME '06:00' + (ROUND(v_ot_hrs * 60)::INT * INTERVAL '1 minute');
          -- NSD = shift hours in 10 PM–6 AM window minus late deduction
          v_nsd_hrs   := GREATEST(0.0, 7.5 - v_late / 60.0);
          v_gross_hrs := 7.5 + v_ot_hrs;   -- 8 h shift − 0.5 h break + OT

          INSERT INTO time_logs
            (company_id, employee_id, work_date, time_in, time_out, status,
             late_minutes, undertime_minutes, ot_hours, gross_hours, nsd_hours)
          VALUES
            (v_cid, emp_rec.id, v_date, v_time_in, v_time_out, 'present',
             v_late, 0, v_ot_hrs, v_gross_hrs, v_nsd_hrs);

        -- ── STANDARD DAY SHIFT ─────────────────────────────────────────────
        ELSE
          -- Late?
          v_late := CASE
            WHEN v_seed < v_late_pct AND v_late_min > 0
              THEN v_late_min + (v_seed % v_late_min)
            WHEN v_seed < v_late_pct
              THEN 5 + (v_seed % 5)
            ELSE 0
          END;
          v_time_in := TIME '08:00' + (v_late * INTERVAL '1 minute');

          IF v_seed >= (100 - v_ot_pct) THEN
            -- OT: stay past 17:00
            v_ot_hrs   := v_ot_hrs_typ + ((v_seed * 3) % 30)::NUMERIC / 60.0;
            v_time_out := TIME '17:00' + (ROUND(v_ot_hrs * 60)::INT * INTERVAL '1 minute');
            v_ut       := 0;

          ELSIF v_seed BETWEEN 88 AND 92 THEN
            -- ~5% undertime: leave before 17:00
            v_ut       := 15 + (v_seed % 31);
            v_time_out := TIME '17:00' - (v_ut * INTERVAL '1 minute');
            v_ot_hrs   := 0.0;

          ELSE
            -- Normal: leave 0–7 min after 17:00
            v_ot_hrs   := 0.0;
            v_ut       := 0;
            v_time_out := TIME '17:00' + ((v_seed % 8) * INTERVAL '1 minute');
          END IF;

          -- gross_hours = (clock-out − clock-in) − 1 h break
          v_gross_hrs := GREATEST(
            0.0,
            EXTRACT(EPOCH FROM (v_time_out - v_time_in)) / 3600.0 - 1.0
          );

          INSERT INTO time_logs
            (company_id, employee_id, work_date, time_in, time_out, status,
             late_minutes, undertime_minutes, ot_hours, gross_hours, nsd_hours)
          VALUES
            (v_cid, emp_rec.id, v_date, v_time_in, v_time_out, 'present',
             v_late, v_ut, v_ot_hrs, v_gross_hrs, 0.0);
        END IF;
      END IF;

      v_date := v_date + INTERVAL '1 day';
    END LOOP;
  END LOOP;   -- end employee loop

  -- ═══════════════════════════════════════════════════════════════════════════
  -- 6. APPROVED LEAVE REQUESTS  (8 requests, realistic spread)
  -- ═══════════════════════════════════════════════════════════════════════════

  INSERT INTO leave_requests
    (company_id, employee_id, leave_type, start_date, end_date, days, reason, status)
  VALUES
    -- Oct: Mateo (Sales Dir) — 3-day VL (family vacation)
    (v_cid,
     (SELECT id FROM employees WHERE company_id=v_cid AND employee_no='EMP-004'),
     'VL', '2025-10-13', '2025-10-15', 3, 'Family vacation', 'approved'),

    -- Nov: Inigo (UI/UX) — 2-day SL (flu)
    (v_cid,
     (SELECT id FROM employees WHERE company_id=v_cid AND employee_no='EMP-009'),
     'SL', '2025-11-10', '2025-11-11', 2, 'Sick leave — flu', 'approved'),

    -- Nov: Paolo (QA) — 1-day CL
    (v_cid,
     (SELECT id FROM employees WHERE company_id=v_cid AND employee_no='EMP-015'),
     'CL', '2025-11-20', '2025-11-20', 1, 'Personal errands', 'approved'),

    -- Dec: Joanna (Sales) — 2-day SL
    (v_cid,
     (SELECT id FROM employees WHERE company_id=v_cid AND employee_no='EMP-017'),
     'SL', '2025-12-03', '2025-12-04', 2, 'Medical check-up', 'approved'),

    -- Dec: Monica (Sales) — 2-day VL (holiday travel)
    (v_cid,
     (SELECT id FROM employees WHERE company_id=v_cid AND employee_no='EMP-019'),
     'VL', '2025-12-22', '2025-12-23', 2, 'Holiday travel', 'approved'),

    -- Jan: Diego (Sales) — 1-day CL
    (v_cid,
     (SELECT id FROM employees WHERE company_id=v_cid AND employee_no='EMP-020'),
     'CL', '2026-01-09', '2026-01-09', 1, 'Personal appointment', 'approved'),

    -- Jan: Althea (FE Dev) — 2-day SL (fever)
    (v_cid,
     (SELECT id FROM employees WHERE company_id=v_cid AND employee_no='EMP-014'),
     'SL', '2026-01-21', '2026-01-22', 2, 'Fever and rest day', 'approved'),

    -- Feb: Sophia (Mktg) — 3-day VL (anniversary trip)
    (v_cid,
     (SELECT id FROM employees WHERE company_id=v_cid AND employee_no='EMP-021'),
     'VL', '2026-02-10', '2026-02-12', 3, 'Anniversary trip', 'approved');

  -- ═══════════════════════════════════════════════════════════════════════════
  -- 7. APPROVED OVERTIME REQUESTS  (10 requests — dev team sprint support)
  -- ═══════════════════════════════════════════════════════════════════════════

  INSERT INTO overtime_requests
    (company_id, employee_id, ot_date, start_time, end_time, hours, reason, status)
  VALUES
    -- Nov sprint — API integration deadline
    (v_cid, (SELECT id FROM employees WHERE company_id=v_cid AND employee_no='EMP-005'),
     '2025-11-07', '17:00', '19:30', 2.5, 'API integration deadline', 'approved'),
    (v_cid, (SELECT id FROM employees WHERE company_id=v_cid AND employee_no='EMP-011'),
     '2025-11-07', '17:00', '19:30', 2.5, 'API integration deadline', 'approved'),
    (v_cid, (SELECT id FROM employees WHERE company_id=v_cid AND employee_no='EMP-013'),
     '2025-11-14', '17:00', '19:00', 2.0, 'Database migration — staging', 'approved'),

    -- Dec sprint — year-end release
    (v_cid, (SELECT id FROM employees WHERE company_id=v_cid AND employee_no='EMP-002'),
     '2025-12-05', '17:00', '19:00', 2.0, 'Year-end release — architecture review', 'approved'),
    (v_cid, (SELECT id FROM employees WHERE company_id=v_cid AND employee_no='EMP-005'),
     '2025-12-05', '17:00', '20:00', 3.0, 'Year-end release — backend finalization', 'approved'),
    (v_cid, (SELECT id FROM employees WHERE company_id=v_cid AND employee_no='EMP-012'),
     '2025-12-12', '17:00', '19:30', 2.5, 'UI polish & staging QA', 'approved'),
    (v_cid, (SELECT id FROM employees WHERE company_id=v_cid AND employee_no='EMP-014'),
     '2025-12-12', '17:00', '18:30', 1.5, 'Frontend responsive fixes', 'approved'),

    -- Jan sprint — Q1 kickoff tasks
    (v_cid, (SELECT id FROM employees WHERE company_id=v_cid AND employee_no='EMP-011'),
     '2026-01-09', '17:00', '19:30', 2.5, 'Q1 sprint kickoff — feature scaffolding', 'approved'),
    (v_cid, (SELECT id FROM employees WHERE company_id=v_cid AND employee_no='EMP-013'),
     '2026-01-16', '17:00', '19:00', 2.0, 'Performance optimization — DB queries', 'approved'),
    (v_cid, (SELECT id FROM employees WHERE company_id=v_cid AND employee_no='EMP-005'),
     '2026-01-23', '17:00', '19:30', 2.5, 'Architecture review — microservices design', 'approved');

  -- ═══════════════════════════════════════════════════════════════════════════
  -- Done
  -- ═══════════════════════════════════════════════════════════════════════════
  RAISE NOTICE '====================================================';
  RAISE NOTICE ' Payroll & Attendance seed — COMPLETE';
  RAISE NOTICE '====================================================';
  RAISE NOTICE ' Company      : GeNXcript Tech Solutions';
  RAISE NOTICE ' Pay periods  : 5  (Oct 2025 – Feb 2026)';
  RAISE NOTICE '   finalized  : Oct / Nov / Dec 2025';
  RAISE NOTICE '   reviewed   : Jan 2026';
  RAISE NOTICE '   draft      : Feb 2026';
  RAISE NOTICE ' Payroll rows : 125  (25 employees × 5 months)';
  RAISE NOTICE ' Time logs    : ~2,600  (Mon–Fri, all 25 employees)';
  RAISE NOTICE ' Leave reqs   : 8   (all approved)';
  RAISE NOTICE ' OT requests  : 10  (all approved — dev team sprints)';
  RAISE NOTICE '====================================================';
  RAISE NOTICE '';
  RAISE NOTICE ' Analytics highlights:';
  RAISE NOTICE '   Most late:  EMP-020 Diego (45%%), EMP-017 Joanna (40%%)';
  RAISE NOTICE '               EMP-015 Paolo (40%%), EMP-009 Inigo (35%%)';
  RAISE NOTICE '   Most OT:    EMP-005 Amara (65%%), EMP-011 Jeric (65%%)';
  RAISE NOTICE '               EMP-012 Rina (60%%),  EMP-002 Dom (60%%)';
  RAISE NOTICE '   NSD hours:  EMP-022 Gino / EMP-024 Leila / EMP-025 Ramon';
  RAISE NOTICE '====================================================';

END $$;
