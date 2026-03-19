-- ============================================================
-- SEED: Mabini Digital Co. — 10-employee QA test company
-- ============================================================
-- Resets the database by deleting GenXcript Tech Solutions,
-- then creates a fresh 10-employee, 3-department company with
-- 4 months of payroll + 3 months of attendance data to exercise
-- every feature in the application.
--
-- Departments : Administration (3) · Operations (4) · Sales (3)
-- Schedules   : Standard Day (8AM–5PM) + Night Shift (10PM–6AM)
-- Pay periods : Dec 2025 (finalized) · Jan 2026 (finalized)
--               Feb 2026 (reviewed)  · Mar 2026 (draft)
-- Time logs   : Dec 2025 + Jan + Feb 2026  (~56 working days × 10 emp)
-- Leave reqs  : 3 approved · 2 pending
-- OT requests : 3 approved · 2 pending
-- ============================================================

DO $$
DECLARE
  v_cid UUID;

  -- Departments
  d_admin UUID;
  d_ops   UUID;
  d_sales UUID;

  -- Schedules
  s_day   UUID;
  s_night UUID;

  -- Leave template
  t_std UUID;

  -- Employees
  e01 UUID;  -- Ana Reyes         GM              Admin      ₱75,000
  e02 UUID;  -- Ben Torres        HR Officer      Admin      ₱32,000
  e03 UUID;  -- Carla Diaz        Finance Officer Admin      ₱32,000
  e04 UUID;  -- Dan Flores        Ops Lead        Ops        ₱50,000
  e05 UUID;  -- Eva Santos        Sr. Technician  Ops        ₱38,000
  e06 UUID;  -- Fred Lim          Technician      Ops        ₱26,000
  e07 UUID;  -- Gia Cruz          Technician      Ops        ₱22,000  probationary / night shift
  e08 UUID;  -- Hugo Ramos        Sales Manager   Sales      ₱45,000
  e09 UUID;  -- Iris Tan          Sales Rep       Sales      ₱22,000
  e10 UUID;  -- Jake Yap          Sales Rep       Sales      ₱20,000  probationary

  -- Pay periods
  pp_dec UUID;
  pp_jan UUID;
  pp_feb UUID;
  pp_mar UUID;

  -- Payroll computation
  emp_rec    RECORD;
  period_rec RECORD;
  v_basic       BIGINT;
  v_salary_php  NUMERIC;
  v_hourly_php  NUMERIC;
  v_msc         NUMERIC;
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

  -- Time log loop
  v_date       DATE;
  v_dow        INT;
  v_day_num    INT;
  v_emp_seq    INT;
  v_seed       INT;
  v_late_pct   INT;
  v_late_min   INT;
  v_ot_pct     INT;
  v_ot_hrs_typ NUMERIC;
  v_absent_pct INT;
  v_is_night   BOOLEAN;
  v_late       INT;
  v_ut         INT;
  v_ot_hrs     NUMERIC;
  v_gross_hrs  NUMERIC;
  v_nsd_hrs    NUMERIC;
  v_time_in    TIME;
  v_time_out   TIME;

BEGIN

  -- ═══════════════════════════════════════════════════════════════════════════
  -- 0. CLEANUP  (delete old seed companies so script is safe to re-run)
  -- ═══════════════════════════════════════════════════════════════════════════
  -- Delete child tables that lack ON DELETE CASCADE before removing companies
  DELETE FROM payroll_entries
    WHERE employee_id IN (
      SELECT e.id FROM employees e
      JOIN companies c ON c.id = e.company_id
      WHERE c.name IN ('GenXcript Tech Solutions', 'Mabini Digital Co.')
    );
  DELETE FROM companies WHERE name IN ('GenXcript Tech Solutions', 'Mabini Digital Co.');
  RAISE NOTICE 'Old seed data deleted.';

  -- ═══════════════════════════════════════════════════════════════════════════
  -- 1. COMPANY
  -- ═══════════════════════════════════════════════════════════════════════════
  INSERT INTO companies (
    name, address, region, pay_frequency,
    bir_tin, sss_employer_no, philhealth_employer_no, pagibig_employer_no
  ) VALUES (
    'Mabini Digital Co.',
    '3F Mabini Tower, 222 Ayala Ave, Makati City',
    'NCR',
    'monthly',
    '987-654-321-000', 'SS-987654321', 'PH-0098765432-0', 'PB-0009876543'
  ) RETURNING id INTO v_cid;

  -- ═══════════════════════════════════════════════════════════════════════════
  -- 2. DEPARTMENTS
  -- ═══════════════════════════════════════════════════════════════════════════
  INSERT INTO departments (company_id, name, code, color, description, sort_order)
  VALUES (v_cid, 'Administration', 'ADMIN', '#0284c7',
          'General management, HR, and finance', 10)
  RETURNING id INTO d_admin;

  INSERT INTO departments (company_id, name, code, color, description, sort_order)
  VALUES (v_cid, 'Operations', 'OPS', '#059669',
          'Field technicians and operations team', 20)
  RETURNING id INTO d_ops;

  INSERT INTO departments (company_id, name, code, color, description, sort_order)
  VALUES (v_cid, 'Sales', 'SALES', '#d97706',
          'Sales management and representatives', 30)
  RETURNING id INTO d_sales;

  -- ═══════════════════════════════════════════════════════════════════════════
  -- 3. SCHEDULES
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

  -- ═══════════════════════════════════════════════════════════════════════════
  -- 4. LEAVE ENTITLEMENT TEMPLATE
  -- ═══════════════════════════════════════════════════════════════════════════
  INSERT INTO leave_entitlement_templates
    (company_id, name, vl_days, sl_days, cl_days,
     carry_over_cap, convertible_to_cash, conversion_rate)
  VALUES
    (v_cid, 'Standard', 15, 15, 5, 5, TRUE, 1.00)
  RETURNING id INTO t_std;

  -- ═══════════════════════════════════════════════════════════════════════════
  -- 5. EMPLOYEES  (10 employees across 3 departments)
  -- ═══════════════════════════════════════════════════════════════════════════

  -- ── Administration ───────────────────────────────────────────────────────

  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status,
    schedule_id, leave_template_id,
    sss_no, philhealth_no, pagibig_no, bir_tin, bank_account, is_active
  ) VALUES (
    v_cid, 'MDC-001', 'Ana', 'Reyes', 'General Manager',
    'regular', '2022-01-03', 7500000, 'monthly', 'ME',
    s_day, t_std,
    '33-1234501-0', '03-100000001-2', '1234-0001-0001', '111-222-333-000',
    'BDO 0012-3456-7890', TRUE
  ) RETURNING id INTO e01;

  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status,
    schedule_id, leave_template_id,
    sss_no, philhealth_no, pagibig_no, bir_tin, bank_account, is_active
  ) VALUES (
    v_cid, 'MDC-002', 'Ben', 'Torres', 'HR Officer',
    'regular', '2022-03-01', 3200000, 'monthly', 'S',
    s_day, t_std,
    '33-1234502-0', '03-100000002-2', '1234-0001-0002', '222-333-444-000',
    'BPI 1234-5678-90', TRUE
  ) RETURNING id INTO e02;

  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status,
    schedule_id, leave_template_id,
    sss_no, philhealth_no, pagibig_no, bir_tin, bank_account, is_active
  ) VALUES (
    v_cid, 'MDC-003', 'Carla', 'Diaz', 'Finance Officer',
    'regular', '2022-06-01', 3200000, 'monthly', 'ME',
    s_day, t_std,
    '33-1234503-0', '03-100000003-2', '1234-0001-0003', '333-444-555-000',
    'Metrobank 123-456-7890', TRUE
  ) RETURNING id INTO e03;

  -- ── Operations ────────────────────────────────────────────────────────────

  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status,
    schedule_id, leave_template_id,
    sss_no, philhealth_no, pagibig_no, bir_tin, bank_account, is_active
  ) VALUES (
    v_cid, 'MDC-004', 'Dan', 'Flores', 'Operations Lead',
    'regular', '2022-01-03', 5000000, 'monthly', 'S',
    s_day, t_std,
    '33-1234504-0', '03-100000004-2', '1234-0001-0004', '444-555-666-000',
    'UnionBank 0098-7654-3210', TRUE
  ) RETURNING id INTO e04;

  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status,
    schedule_id, leave_template_id,
    sss_no, philhealth_no, pagibig_no, bir_tin, bank_account, is_active
  ) VALUES (
    v_cid, 'MDC-005', 'Eva', 'Santos', 'Sr. Technician',
    'regular', '2022-04-01', 3800000, 'monthly', 'S',
    s_day, t_std,
    '33-1234505-0', '03-100000005-2', '1234-0001-0005', '555-666-777-000',
    'GCash 0917-555-1111', TRUE
  ) RETURNING id INTO e05;

  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status,
    schedule_id, leave_template_id,
    sss_no, philhealth_no, pagibig_no, bir_tin, bank_account, is_active
  ) VALUES (
    v_cid, 'MDC-006', 'Fred', 'Lim', 'Technician',
    'regular', '2023-01-09', 2600000, 'monthly', 'S',
    s_day, t_std,
    '33-1234506-0', '03-100000006-2', '1234-0001-0006', '666-777-888-000',
    'Maya 0918-666-2222', TRUE
  ) RETURNING id INTO e06;

  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status,
    schedule_id, leave_template_id,
    sss_no, philhealth_no, pagibig_no, bir_tin, bank_account, is_active
  ) VALUES (
    v_cid, 'MDC-007', 'Gia', 'Cruz', 'Technician',
    'probationary', '2025-10-01', 2200000, 'monthly', 'S',
    s_night, t_std,               -- ← Night Shift for NSD testing
    '33-1234507-0', '03-100000007-2', '1234-0001-0007', '777-888-999-000',
    'GCash 0919-777-3333', TRUE
  ) RETURNING id INTO e07;

  -- ── Sales ─────────────────────────────────────────────────────────────────

  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status,
    schedule_id, leave_template_id,
    sss_no, philhealth_no, pagibig_no, bir_tin, bank_account, is_active
  ) VALUES (
    v_cid, 'MDC-008', 'Hugo', 'Ramos', 'Sales Manager',
    'regular', '2022-02-01', 4500000, 'monthly', 'ME',
    s_day, t_std,
    '33-1234508-0', '03-100000008-2', '1234-0001-0008', '888-999-000-111',
    'BDO 0087-6543-2109', TRUE
  ) RETURNING id INTO e08;

  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status,
    schedule_id, leave_template_id,
    sss_no, philhealth_no, pagibig_no, bir_tin, bank_account, is_active
  ) VALUES (
    v_cid, 'MDC-009', 'Iris', 'Tan', 'Sales Representative',
    'regular', '2023-07-01', 2200000, 'monthly', 'S',
    s_day, t_std,
    '33-1234509-0', '03-100000009-2', '1234-0001-0009', '999-000-111-222',
    'GCash 0920-888-4444', TRUE
  ) RETURNING id INTO e09;

  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status,
    schedule_id, leave_template_id,
    sss_no, philhealth_no, pagibig_no, bir_tin, bank_account, is_active
  ) VALUES (
    v_cid, 'MDC-010', 'Jake', 'Yap', 'Sales Representative',
    'probationary', '2026-01-05', 2000000, 'monthly', 'S',
    s_day, t_std,
    '33-1234510-0', '03-100000010-2', '1234-0001-0010', '000-111-222-333',
    'Maya 0921-999-5555', TRUE
  ) RETURNING id INTO e10;

  -- ═══════════════════════════════════════════════════════════════════════════
  -- 6. REPORTING LINES
  -- ═══════════════════════════════════════════════════════════════════════════
  -- Ana (GM) → no manager
  -- Ben & Carla → Ana
  UPDATE employees SET manager_id = e01 WHERE id IN (e02, e03, e04, e08);
  -- Dan → Ana; Eva, Fred, Gia → Dan
  UPDATE employees SET manager_id = e04 WHERE id IN (e05, e06, e07);
  -- Hugo → Ana; Iris & Jake → Hugo
  UPDATE employees SET manager_id = e08 WHERE id IN (e09, e10);

  -- ═══════════════════════════════════════════════════════════════════════════
  -- 7. EMPLOYEE PROFILES  (department mapping + basic personal info)
  -- ═══════════════════════════════════════════════════════════════════════════
  INSERT INTO employee_profiles
    (employee_id, company_id, department, department_id,
     date_of_birth, sex, civil_status, nationality, mobile_no,
     present_address_street, present_address_city, present_address_province)
  VALUES
    (e01, v_cid, 'Administration', d_admin,
     '1985-03-12', 'Female', 'Married', 'Filipino', '0917-100-0001',
     '10 Palma St', 'Makati City', 'Metro Manila'),
    (e02, v_cid, 'Administration', d_admin,
     '1992-07-22', 'Male', 'Single', 'Filipino', '0917-100-0002',
     '22 Burgos St', 'Pasig City', 'Metro Manila'),
    (e03, v_cid, 'Administration', d_admin,
     '1990-11-05', 'Female', 'Married', 'Filipino', '0917-100-0003',
     '5 Dela Rosa St', 'Makati City', 'Metro Manila'),
    (e04, v_cid, 'Operations', d_ops,
     '1988-01-30', 'Male', 'Single', 'Filipino', '0917-100-0004',
     '18 Magallanes St', 'Taguig City', 'Metro Manila'),
    (e05, v_cid, 'Operations', d_ops,
     '1993-05-18', 'Female', 'Single', 'Filipino', '0917-100-0005',
     '33 Aguinaldo Ave', 'Paranaque City', 'Metro Manila'),
    (e06, v_cid, 'Operations', d_ops,
     '1995-09-09', 'Male', 'Single', 'Filipino', '0917-100-0006',
     '7 Luna St', 'Quezon City', 'Metro Manila'),
    (e07, v_cid, 'Operations', d_ops,
     '1998-04-15', 'Female', 'Single', 'Filipino', '0917-100-0007',
     '50 Rizal Ave', 'Caloocan City', 'Metro Manila'),
    (e08, v_cid, 'Sales', d_sales,
     '1986-12-03', 'Male', 'Married', 'Filipino', '0917-100-0008',
     '12 Mabini St', 'Makati City', 'Metro Manila'),
    (e09, v_cid, 'Sales', d_sales,
     '1997-02-28', 'Female', 'Single', 'Filipino', '0917-100-0009',
     '88 P. Ocampo St', 'Manila', 'Metro Manila'),
    (e10, v_cid, 'Sales', d_sales,
     '2000-08-10', 'Male', 'Single', 'Filipino', '0917-100-0010',
     '3 Balagtas St', 'Mandaluyong City', 'Metro Manila');

  -- ═══════════════════════════════════════════════════════════════════════════
  -- 8. COMPANY LOCATION  (Makati main office for geofencing tests)
  -- ═══════════════════════════════════════════════════════════════════════════
  INSERT INTO company_locations
    (company_id, name, address, latitude, longitude, radius_m, is_active)
  VALUES
    (v_cid, 'Main Office', '3F Mabini Tower, 222 Ayala Ave, Makati City',
     14.5547, 121.0244, 150, TRUE);

  -- ═══════════════════════════════════════════════════════════════════════════
  -- 9. PAY PERIODS
  -- ═══════════════════════════════════════════════════════════════════════════
  INSERT INTO pay_periods (company_id, period_start, period_end, payment_date, status, reviewed_by)
  VALUES (v_cid, '2025-12-01', '2025-12-31', '2025-12-24', 'finalized', 'Ana Reyes')
  RETURNING id INTO pp_dec;

  INSERT INTO pay_periods (company_id, period_start, period_end, payment_date, status, reviewed_by)
  VALUES (v_cid, '2026-01-01', '2026-01-31', '2026-01-30', 'finalized', 'Ana Reyes')
  RETURNING id INTO pp_jan;

  INSERT INTO pay_periods (company_id, period_start, period_end, payment_date, status, reviewed_by)
  VALUES (v_cid, '2026-02-01', '2026-02-28', '2026-02-27', 'reviewed', 'Ana Reyes')
  RETURNING id INTO pp_feb;

  INSERT INTO pay_periods (company_id, period_start, period_end, payment_date, status)
  VALUES (v_cid, '2026-03-01', '2026-03-31', '2026-03-31', 'draft')
  RETURNING id INTO pp_mar;

  -- ═══════════════════════════════════════════════════════════════════════════
  -- 10. PAYROLL ENTRIES  (10 employees × 4 periods = 40 rows)
  --     Contributions: 2025/2026 PH government rates (TRAIN Law)
  --     Dec: + 13th month accrual for all
  --     Jan/Feb: Dan & Eva get OT pay (sprint OT)
  --     Gia: night differential every month
  -- ═══════════════════════════════════════════════════════════════════════════
  FOR emp_rec IN (
    SELECT id, employee_no, basic_salary FROM employees
    WHERE  company_id = v_cid AND is_active ORDER BY employee_no
  ) LOOP
    v_basic      := emp_rec.basic_salary;
    v_salary_php := v_basic / 100.0;
    v_hourly_php := v_salary_php / (26.0 * 8.0);

    -- SSS EE 4.5% (MSC rounded to ₱500, capped at ₱30,000)
    v_msc    := LEAST(GREATEST(ROUND(v_salary_php / 500.0) * 500.0, 5000.0), 30000.0);
    v_sss_ee := ROUND(v_msc * 0.045)::BIGINT * 100;
    v_sss_er := ROUND(v_msc * 0.095)::BIGINT * 100;

    -- PhilHealth EE 2.5% (base capped at ₱100,000)
    v_phic_ee := ROUND(LEAST(v_salary_php, 100000.0) * 0.025)::BIGINT * 100;
    v_phic_er := v_phic_ee;

    -- Pag-IBIG EE 2%, max ₱100
    v_hdmf_ee := LEAST(ROUND(v_salary_php * 0.02)::BIGINT * 100, 10000::BIGINT);
    v_hdmf_er := 20000;

    -- Taxable income & withholding tax (TRAIN Law 2023+ monthly)
    v_taxable := v_salary_php - (v_sss_ee + v_phic_ee + v_hdmf_ee) / 100.0;
    v_wtax := CASE
      WHEN v_taxable <=   20833 THEN 0
      WHEN v_taxable <=   33332 THEN ROUND((v_taxable -   20833)    * 0.20)::BIGINT * 100
      WHEN v_taxable <=   66666 THEN ROUND((2500      + (v_taxable -  33333) * 0.25))::BIGINT * 100
      WHEN v_taxable <=  166666 THEN ROUND((10833.33  + (v_taxable -  66667) * 0.30))::BIGINT * 100
      WHEN v_taxable <=  666666 THEN ROUND((40833.33  + (v_taxable - 166667) * 0.32))::BIGINT * 100
      ELSE                           ROUND((200833.33 + (v_taxable - 666667) * 0.35))::BIGINT * 100
    END;

    -- Night differential: Gia (MDC-007) only — 22 working days × 7.5 NSD hrs × rate × 10%
    v_nsd_pay := CASE
      WHEN emp_rec.employee_no = 'MDC-007'
        THEN ROUND(22.0 * 7.5 * v_hourly_php * 0.10 * 100.0)::BIGINT
      ELSE 0
    END;

    FOR period_rec IN (
      SELECT id, period_start FROM pay_periods WHERE company_id = v_cid ORDER BY period_start
    ) LOOP
      v_month := EXTRACT(MONTH FROM period_rec.period_start)::INT;

      -- 13th month accrual — December only (1/12 of annual basic)
      v_13th := CASE WHEN v_month = 12 THEN ROUND(v_basic / 12.0)::BIGINT ELSE 0 END;

      -- OT pay: Dan & Eva in Jan/Feb (field project overtime)
      v_ot_pay := CASE
        WHEN emp_rec.employee_no = 'MDC-004' AND v_month IN (1, 2)
          THEN ROUND(8.0 * 2.0 * v_hourly_php * 1.25 * 100.0)::BIGINT
        WHEN emp_rec.employee_no = 'MDC-005' AND v_month IN (1, 2)
          THEN ROUND(6.0 * 2.0 * v_hourly_php * 1.25 * 100.0)::BIGINT
        ELSE 0
      END;

      v_gross   := v_basic + v_ot_pay + v_nsd_pay + v_13th;
      v_tot_ded := v_sss_ee + v_phic_ee + v_hdmf_ee + v_wtax;
      v_net     := v_gross - v_tot_ded;

      INSERT INTO payroll_entries (
        pay_period_id, employee_id,
        basic_pay, overtime_pay, night_differential, thirteenth_month_accrual, gross_pay,
        sss_employee,   philhealth_employee,   pagibig_employee,
        sss_employer,   philhealth_employer,   pagibig_employer,
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
  -- 11. TIME LOGS  (Dec 2025 + Jan + Feb 2026, Mon–Fri, all 10 employees)
  --
  --   Employee  Late%  LateMins  OT%  OT hrs  Absent%  Night?  Notes
  --   MDC-001   0%     0        5%    0.5     2%       N       GM, always on time
  --   MDC-002   5%     5        10%   0.5     2%       N       HR, minimal late
  --   MDC-003   5%     5        20%   1.0     2%       N       Finance, month-end OT
  --   MDC-004   10%    10       40%   2.0     3%       N       Ops Lead, frequent OT
  --   MDC-005   5%     5        45%   2.0     2%       N       Sr Tech, most OT
  --   MDC-006   20%    15       15%   1.0     5%       N       Tech, sometimes late
  --   MDC-007   15%    10       10%   0.5     5%       Y       Probationary night shift
  --   MDC-008   20%    10       10%   1.0     4%       N       Sales Mgr, occasionally late
  --   MDC-009   35%    20       5%    0.5     6%       N       Sales Rep, chronically late
  --   MDC-010   40%    20       5%    0.5     8%       N       New hire, adjustment period
  -- ═══════════════════════════════════════════════════════════════════════════

  FOR emp_rec IN (
    SELECT id, employee_no FROM employees
    WHERE  company_id = v_cid AND is_active ORDER BY employee_no
  ) LOOP
    v_emp_seq := CAST(SUBSTRING(emp_rec.employee_no FROM 5) AS INT);

    CASE emp_rec.employee_no
      WHEN 'MDC-001' THEN v_late_pct:= 0; v_late_min:= 0; v_ot_pct:= 5; v_ot_hrs_typ:=0.5; v_absent_pct:=2; v_is_night:=FALSE;
      WHEN 'MDC-002' THEN v_late_pct:= 5; v_late_min:= 5; v_ot_pct:=10; v_ot_hrs_typ:=0.5; v_absent_pct:=2; v_is_night:=FALSE;
      WHEN 'MDC-003' THEN v_late_pct:= 5; v_late_min:= 5; v_ot_pct:=20; v_ot_hrs_typ:=1.0; v_absent_pct:=2; v_is_night:=FALSE;
      WHEN 'MDC-004' THEN v_late_pct:=10; v_late_min:=10; v_ot_pct:=40; v_ot_hrs_typ:=2.0; v_absent_pct:=3; v_is_night:=FALSE;
      WHEN 'MDC-005' THEN v_late_pct:= 5; v_late_min:= 5; v_ot_pct:=45; v_ot_hrs_typ:=2.0; v_absent_pct:=2; v_is_night:=FALSE;
      WHEN 'MDC-006' THEN v_late_pct:=20; v_late_min:=15; v_ot_pct:=15; v_ot_hrs_typ:=1.0; v_absent_pct:=5; v_is_night:=FALSE;
      WHEN 'MDC-007' THEN v_late_pct:=15; v_late_min:=10; v_ot_pct:=10; v_ot_hrs_typ:=0.5; v_absent_pct:=5; v_is_night:=TRUE;
      WHEN 'MDC-008' THEN v_late_pct:=20; v_late_min:=10; v_ot_pct:=10; v_ot_hrs_typ:=1.0; v_absent_pct:=4; v_is_night:=FALSE;
      WHEN 'MDC-009' THEN v_late_pct:=35; v_late_min:=20; v_ot_pct:= 5; v_ot_hrs_typ:=0.5; v_absent_pct:=6; v_is_night:=FALSE;
      WHEN 'MDC-010' THEN v_late_pct:=40; v_late_min:=20; v_ot_pct:= 5; v_ot_hrs_typ:=0.5; v_absent_pct:=8; v_is_night:=FALSE;
      ELSE                 v_late_pct:=10; v_late_min:= 5; v_ot_pct:=10; v_ot_hrs_typ:=1.0; v_absent_pct:=4; v_is_night:=FALSE;
    END CASE;

    v_day_num := 0;
    v_date    := '2025-12-01'::DATE;

    WHILE v_date <= '2026-02-28'::DATE LOOP
      v_dow := EXTRACT(DOW FROM v_date)::INT;

      IF v_dow BETWEEN 1 AND 5 THEN   -- Mon–Fri
        v_day_num := v_day_num + 1;
        v_seed    := (v_emp_seq * 7919 + v_day_num * 31) % 100;

        IF v_seed < v_absent_pct THEN
          -- Absent
          INSERT INTO time_logs
            (company_id, employee_id, work_date, status,
             late_minutes, undertime_minutes, ot_hours, gross_hours, nsd_hours)
          VALUES (v_cid, emp_rec.id, v_date, 'absent', 0, 0, 0.0, 0.0, 0.0);

        ELSIF v_is_night THEN
          -- Night shift (Gia)
          v_late   := CASE WHEN v_seed < v_late_pct THEN v_late_min + (v_seed % 10) ELSE 0 END;
          v_ot_hrs := CASE WHEN v_seed >= (100 - v_ot_pct) THEN v_ot_hrs_typ + (v_seed % 20)::NUMERIC / 60.0 ELSE 0.0 END;
          v_time_in   := TIME '22:00' + (v_late * INTERVAL '1 minute');
          v_time_out  := TIME '06:00' + (ROUND(v_ot_hrs * 60)::INT * INTERVAL '1 minute');
          v_nsd_hrs   := GREATEST(0.0, 7.5 - v_late / 60.0);
          v_gross_hrs := 7.5 + v_ot_hrs;
          INSERT INTO time_logs
            (company_id, employee_id, work_date, time_in, time_out, status,
             late_minutes, undertime_minutes, ot_hours, gross_hours, nsd_hours)
          VALUES (v_cid, emp_rec.id, v_date, v_time_in, v_time_out, 'present',
                  v_late, 0, v_ot_hrs, v_gross_hrs, v_nsd_hrs);

        ELSE
          -- Standard day shift
          v_late := CASE
            WHEN v_seed < v_late_pct AND v_late_min > 0 THEN v_late_min + (v_seed % v_late_min)
            WHEN v_seed < v_late_pct                    THEN 5 + (v_seed % 5)
            ELSE 0
          END;
          v_time_in := TIME '08:00' + (v_late * INTERVAL '1 minute');

          IF v_seed >= (100 - v_ot_pct) THEN
            v_ot_hrs   := v_ot_hrs_typ + ((v_seed * 3) % 30)::NUMERIC / 60.0;
            v_time_out := TIME '17:00' + (ROUND(v_ot_hrs * 60)::INT * INTERVAL '1 minute');
            v_ut       := 0;
          ELSIF v_seed BETWEEN 88 AND 92 THEN
            v_ut       := 15 + (v_seed % 31);
            v_time_out := TIME '17:00' - (v_ut * INTERVAL '1 minute');
            v_ot_hrs   := 0.0;
          ELSE
            v_ot_hrs   := 0.0;
            v_ut       := 0;
            v_time_out := TIME '17:00' + ((v_seed % 8) * INTERVAL '1 minute');
          END IF;

          v_gross_hrs := GREATEST(0.0,
            EXTRACT(EPOCH FROM (v_time_out - v_time_in)) / 3600.0 - 1.0);

          INSERT INTO time_logs
            (company_id, employee_id, work_date, time_in, time_out, status,
             late_minutes, undertime_minutes, ot_hours, gross_hours, nsd_hours)
          VALUES (v_cid, emp_rec.id, v_date, v_time_in, v_time_out, 'present',
                  v_late, v_ut, v_ot_hrs, v_gross_hrs, 0.0);
        END IF;
      END IF;

      v_date := v_date + INTERVAL '1 day';
    END LOOP;
  END LOOP;

  -- ═══════════════════════════════════════════════════════════════════════════
  -- 12. LEAVE REQUESTS  (3 approved · 2 pending for approval workflow testing)
  -- ═══════════════════════════════════════════════════════════════════════════
  INSERT INTO leave_requests
    (company_id, employee_id, leave_type, start_date, end_date, days, reason, status)
  VALUES
    -- Approved: Ben (HR) — VL, Dec 23-24 (pre-Christmas)
    (v_cid, e02, 'VL', '2025-12-23', '2025-12-24', 2,
     'Pre-Christmas leave', 'approved'),

    -- Approved: Fred (Tech) — SL, Jan 13-14 (sick)
    (v_cid, e06, 'SL', '2026-01-13', '2026-01-14', 2,
     'Fever and rest', 'approved'),

    -- Approved: Iris (Sales) — CL, Feb 14 (Valentine's Day)
    (v_cid, e09, 'CL', '2026-02-14', '2026-02-14', 1,
     'Personal day off', 'approved'),

    -- PENDING: Jake (Sales, new hire) — VL Mar 17-18  ← test approval
    (v_cid, e10, 'VL', '2026-03-17', '2026-03-18', 2,
     'Family event', 'pending'),

    -- PENDING: Hugo (Sales Mgr) — SL Mar 20  ← test rejection
    (v_cid, e08, 'SL', '2026-03-20', '2026-03-20', 1,
     'Check-up appointment', 'pending');

  -- ═══════════════════════════════════════════════════════════════════════════
  -- 13. OVERTIME REQUESTS  (3 approved · 2 pending)
  -- ═══════════════════════════════════════════════════════════════════════════
  INSERT INTO overtime_requests
    (company_id, employee_id, ot_date, start_time, end_time, hours, reason, status)
  VALUES
    -- Approved: Dan — Jan 22, field installation project
    (v_cid, e04, '2026-01-22', '17:00', '19:00', 2.0,
     'Field installation — site A', 'approved'),

    -- Approved: Eva — Feb 5, urgent repair
    (v_cid, e05, '2026-02-05', '17:00', '19:00', 2.0,
     'Emergency repair — site B', 'approved'),

    -- Approved: Dan — Feb 19, client deadline
    (v_cid, e04, '2026-02-19', '17:00', '19:30', 2.5,
     'Client deadline — server migration', 'approved'),

    -- PENDING: Eva — Mar 12  ← test approval
    (v_cid, e05, '2026-03-12', '17:00', '19:00', 2.0,
     'Preventive maintenance run', 'pending'),

    -- PENDING: Dan — Mar 18  ← test rejection
    (v_cid, e04, '2026-03-18', '17:00', '20:00', 3.0,
     'System upgrade — datacenter', 'pending');

  -- ═══════════════════════════════════════════════════════════════════════════
  -- Done
  -- ═══════════════════════════════════════════════════════════════════════════
  RAISE NOTICE '====================================================';
  RAISE NOTICE ' Mabini Digital Co. — seed complete!';
  RAISE NOTICE '====================================================';
  RAISE NOTICE ' Company ID : %', v_cid;
  RAISE NOTICE '';
  RAISE NOTICE ' Employees (10):';
  RAISE NOTICE '   Admin  : MDC-001 Ana Reyes (GM)';
  RAISE NOTICE '            MDC-002 Ben Torres (HR)';
  RAISE NOTICE '            MDC-003 Carla Diaz (Finance)';
  RAISE NOTICE '   Ops    : MDC-004 Dan Flores (Lead)';
  RAISE NOTICE '            MDC-005 Eva Santos (Sr. Tech)';
  RAISE NOTICE '            MDC-006 Fred Lim   (Tech)';
  RAISE NOTICE '            MDC-007 Gia Cruz   (Tech, probationary, night shift)';
  RAISE NOTICE '   Sales  : MDC-008 Hugo Ramos (Sales Mgr)';
  RAISE NOTICE '            MDC-009 Iris Tan   (Sales Rep, chronically late)';
  RAISE NOTICE '            MDC-010 Jake Yap   (Sales Rep, probationary, new hire)';
  RAISE NOTICE '';
  RAISE NOTICE ' Pay Periods: Dec 2025 (finalized), Jan 2026 (finalized)';
  RAISE NOTICE '              Feb 2026 (reviewed),  Mar 2026 (draft)';
  RAISE NOTICE ' Time Logs : Dec 2025 + Jan + Feb 2026 (~560 rows)';
  RAISE NOTICE ' Leave Reqs: 3 approved + 2 pending';
  RAISE NOTICE ' OT Reqs   : 3 approved + 2 pending';
  RAISE NOTICE '';
  RAISE NOTICE ' Grant access:';
  RAISE NOTICE '   INSERT INTO user_company_access (user_id, company_id, role)';
  RAISE NOTICE '   VALUES (''<your-auth-uid>'', ''%'', ''admin'');', v_cid;
  RAISE NOTICE '====================================================';

END $$;
