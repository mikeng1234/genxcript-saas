-- ============================================================
-- SEED: Palawan Trading Corp. — 35-employee payroll test data
-- ============================================================
-- Creates a realistic 35-employee company across 5 departments
-- with 18 months of semi-monthly payroll data (36 pay periods).
--
-- Departments : Operations (10) · Sales (8) · Finance (6)
--               Admin (6) · Executive (5)
-- Pay periods : Oct 2024 – Mar 2026 (semi-monthly, 36 periods)
-- Status      : 34 periods = "paid", last 2 = "draft"
-- All monetary values: INTEGER centavos (₱1 = 100 centavos)
-- ============================================================

DO $$
DECLARE
  v_cid         UUID;
  v_owner_id    UUID := '241167c3-483f-4f16-ac0a-9532a16c05d3';

  -- Departments
  d_ops         UUID;
  d_sales       UUID;
  d_fin         UUID;
  d_admin       UUID;
  d_exec        UUID;

  -- Employee IDs (35 total)
  emp_ids       UUID[35];

  -- Pay period tracking
  pp_ids        UUID[];
  v_pp_id       UUID;

  -- Loop variables
  i             INT;
  j             INT;
  v_year        INT;
  v_month       INT;
  v_half        INT;  -- 1 = 1st-15th, 2 = 16th-end
  v_period_start DATE;
  v_period_end   DATE;
  v_payment_date DATE;
  v_status       TEXT;
  v_pp_count     INT := 0;

  -- Employee record for payroll loop
  emp_rec       RECORD;

  -- Payroll computation variables
  v_basic_salary  BIGINT;   -- full monthly salary in centavos
  v_basic_pay     BIGINT;   -- semi-monthly = salary / 2
  v_salary_php    NUMERIC;  -- monthly salary in pesos
  v_msc           NUMERIC;  -- SSS monthly salary credit

  -- Earnings
  v_ot_pay        BIGINT;
  v_holiday_pay   BIGINT;
  v_nsd_pay       BIGINT;
  v_allow_nt      BIGINT;   -- nontaxable allowances
  v_allow_t       BIGINT;   -- taxable allowances
  v_commission    BIGINT;
  v_13th          BIGINT;
  v_gross         BIGINT;

  -- Government contributions (semi-monthly = monthly / 2)
  v_sss_ee        BIGINT;
  v_sss_er        BIGINT;
  v_phic_ee       BIGINT;
  v_phic_er       BIGINT;
  v_hdmf_ee       BIGINT;
  v_hdmf_er       BIGINT;

  -- Tax & deductions
  v_taxable       NUMERIC;
  v_wtax          BIGINT;
  v_sss_loan      BIGINT;
  v_pagibig_loan  BIGINT;
  v_cash_advance  BIGINT;
  v_other_ded     BIGINT;
  v_absent_ded    BIGINT;
  v_tot_ded       BIGINT;
  v_net           BIGINT;

  -- Deterministic pseudo-random seed
  v_seed          INT;
  v_dept_name     TEXT;
  v_position      TEXT;

BEGIN

  -- ═══════════════════════════════════════════════════════════════════════════
  -- 0. CLEANUP (safe to re-run)
  -- ═══════════════════════════════════════════════════════════════════════════
  DELETE FROM payroll_entries
    WHERE employee_id IN (
      SELECT e.id FROM employees e
      JOIN companies c ON c.id = e.company_id
      WHERE c.name = 'Palawan Trading Corp.'
    );
  DELETE FROM companies WHERE name = 'Palawan Trading Corp.';
  RAISE NOTICE 'Old Palawan Trading seed data deleted.';

  -- ═══════════════════════════════════════════════════════════════════════════
  -- 1. COMPANY
  -- ═══════════════════════════════════════════════════════════════════════════
  INSERT INTO companies (
    name, address, region, pay_frequency, daily_rate_divisor,
    bir_tin, sss_employer_no, philhealth_employer_no, pagibig_employer_no
  ) VALUES (
    'Palawan Trading Corp.',
    '245 Rizal Avenue, Puerto Princesa, Palawan',
    'MIMAROPA',
    'semi-monthly',
    26,
    '123-456-789-000',
    '04-1234567-8',
    '12-034567891-2',
    '1234-5678-9012'
  ) RETURNING id INTO v_cid;

  -- ═══════════════════════════════════════════════════════════════════════════
  -- 2. USER-COMPANY ACCESS
  -- ═══════════════════════════════════════════════════════════════════════════
  INSERT INTO user_company_access (user_id, company_id, role)
  VALUES (v_owner_id, v_cid, 'admin');

  -- ═══════════════════════════════════════════════════════════════════════════
  -- 3. DEPARTMENTS
  -- ═══════════════════════════════════════════════════════════════════════════
  INSERT INTO departments (company_id, name, code, color, description, sort_order)
  VALUES (v_cid, 'Operations', 'OPS', '#059669',
          'Warehouse, logistics, inventory, and delivery', 10)
  RETURNING id INTO d_ops;

  INSERT INTO departments (company_id, name, code, color, description, sort_order)
  VALUES (v_cid, 'Sales', 'SALES', '#d97706',
          'Sales associates, supervisors, and account management', 20)
  RETURNING id INTO d_sales;

  INSERT INTO departments (company_id, name, code, color, description, sort_order)
  VALUES (v_cid, 'Finance', 'FIN', '#0284c7',
          'Accounting, billing, and financial management', 30)
  RETURNING id INTO d_fin;

  INSERT INTO departments (company_id, name, code, color, description, sort_order)
  VALUES (v_cid, 'Admin', 'ADMIN', '#7c3aed',
          'HR, office management, and IT support', 40)
  RETURNING id INTO d_admin;

  INSERT INTO departments (company_id, name, code, color, description, sort_order)
  VALUES (v_cid, 'Executive', 'EXEC', '#dc2626',
          'C-suite and executive leadership', 50)
  RETURNING id INTO d_exec;

  -- ═══════════════════════════════════════════════════════════════════════════
  -- 4. EMPLOYEES (35 across 5 departments — proper org ladder)
  -- ═══════════════════════════════════════════════════════════════════════════
  -- Org Chart:
  --   GM (Eduardo Gonzales)
  --   ├── VP Operations (Rosario Hernandez)
  --   │   └── Operations Manager (Diana Dela Cruz)
  --   │       ├── Warehouse Supervisor (Elena Garcia)
  --   │       │   ├── Warehouse Staff ×3 (Ricardo, Maria, Jose)
  --   │       │   └── Inventory Clerk ×2 (Carmen, Angelo)
  --   │       └── Logistics Supervisor (Roberto Torres)
  --   │           ├── Delivery Driver ×2 (Patricia, Fernando[resigned])
  --   │           └── Dispatch Coordinator (placeholder — Roberto covers)
  --   ├── VP Sales & Marketing (Antonio Lopez)
  --   │   └── Area Sales Manager (Teresa Castillo)
  --   │       ├── Sales Supervisor - North (Sofia Lopez)
  --   │       │   ├── Sales Representative ×2 (Miguel, Andres[probi])
  --   │       │   └── Sales Clerk (Lorna)
  --   │       └── Sales Supervisor - South (Rafael Martinez)
  --   │           ├── Account Executive (Cristina Rivera)
  --   │           └── Account Executive (Marco Navarro[resigned])
  --   ├── VP Finance & Admin (Luisa Martinez)
  --   │   ├── Finance Manager (Victoria Garcia)
  --   │   │   ├── Senior Accountant (Gabriel Soriano)
  --   │   │   ├── Junior Accountant (Angelica Pascual)
  --   │   │   ├── Bookkeeper (Dennis Santos)
  --   │   │   ├── Billing Clerk (Paolo Reyes)
  --   │   │   └── Cashier (Jasmine Cruz)
  --   │   └── Admin & HR Manager (Jonathan Villanueva)
  --   │       ├── HR Officer (Maricel Mendoza)
  --   │       ├── IT Support Specialist (Jerome Ramos)
  --   │       ├── Admin Clerk (Kenneth Torres)
  --   │       ├── Receptionist (Anna Aquino)
  --   │       └── Admin Clerk (Bianca Dela Cruz[resigned])
  --   └── Executive Assistant (Raymond Rivera)

  -- ── Executive (5 employees: PTC-031 to PTC-035) ──────────────────────────
  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status,
    sss_no, philhealth_no, pagibig_no, bir_tin, bank_account, is_active
  ) VALUES
    (v_cid, 'PTC-031', 'Eduardo', 'Gonzales', 'GENERAL MANAGER',
     'regular', '2020-01-06', 12000000, 'monthly', 'ME3',
     '34-8123431-1', '12-100000031-3', '2001-0005-0031', '301-205-131-000',
     'BDO 0012-3456-0031', TRUE),
    (v_cid, 'PTC-032', 'Rosario', 'Hernandez', 'VP OPERATIONS',
     'regular', '2020-01-06', 8500000, 'monthly', 'ME2',
     '34-8123432-2', '12-100000032-3', '2001-0005-0032', '301-205-132-000',
     'BPI 1234-5678-32', TRUE),
    (v_cid, 'PTC-033', 'Antonio', 'Lopez', 'VP SALES & MARKETING',
     'regular', '2020-03-16', 8000000, 'monthly', 'ME1',
     '34-8123433-3', '12-100000033-3', '2001-0005-0033', '301-205-133-000',
     'Metrobank 456-789-0033', TRUE),
    (v_cid, 'PTC-034', 'Luisa', 'Martinez', 'VP FINANCE & ADMIN',
     'regular', '2020-05-04', 8000000, 'monthly', 'ME',
     '34-8123434-4', '12-100000034-3', '2001-0005-0034', '301-205-134-000',
     'BDO 0012-3456-0034', TRUE),
    (v_cid, 'PTC-035', 'Raymond', 'Rivera', 'EXECUTIVE ASSISTANT',
     'regular', '2021-09-01', 3000000, 'monthly', 'S',
     '34-8123435-5', '12-100000035-3', '2001-0005-0035', '301-205-135-000',
     'BPI 1234-5678-35', TRUE);

  -- ── Operations (10 employees: PTC-001 to PTC-010) ─────────────────────────
  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status,
    sss_no, philhealth_no, pagibig_no, bir_tin, bank_account, is_active
  ) VALUES
    (v_cid, 'PTC-010', 'Diana', 'Dela Cruz', 'OPERATIONS MANAGER',
     'regular', '2020-01-06', 4500000, 'monthly', 'ME2',
     '34-8123410-0', '12-100000010-3', '2001-0001-0010', '301-201-110-000',
     'BPI 1234-5678-10', TRUE),
    (v_cid, 'PTC-004', 'Elena', 'Garcia', 'WAREHOUSE SUPERVISOR',
     'regular', '2020-02-03', 2800000, 'monthly', 'ME',
     '34-8123404-4', '12-100000004-3', '2001-0001-0004', '301-201-104-000',
     'Metrobank 456-789-0004', TRUE),
    (v_cid, 'PTC-001', 'Ricardo', 'Santos', 'WAREHOUSE STAFF',
     'regular', '2020-06-15', 1400000, 'monthly', 'S',
     '34-8123401-1', '12-100000001-3', '2001-0001-0001', '301-201-101-000',
     'BDO 0012-3456-0001', TRUE),
    (v_cid, 'PTC-002', 'Maria', 'Cruz', 'WAREHOUSE STAFF',
     'regular', '2021-03-01', 1300000, 'monthly', 'ME1',
     '34-8123402-2', '12-100000002-3', '2001-0001-0002', '301-201-102-000',
     'BPI 1234-5678-02', TRUE),
    (v_cid, 'PTC-003', 'Jose', 'Reyes', 'WAREHOUSE STAFF',
     'regular', '2022-01-10', 1200000, 'monthly', 'S',
     '34-8123403-3', '12-100000003-3', '2001-0001-0003', '301-201-103-000',
     NULL, TRUE),
    (v_cid, 'PTC-006', 'Carmen', 'Mendoza', 'INVENTORY CLERK',
     'regular', '2021-11-01', 1600000, 'monthly', 'ME2',
     '34-8123406-6', '12-100000006-3', '2001-0001-0006', '301-201-106-000',
     'BDO 0012-3456-0006', TRUE),
    (v_cid, 'PTC-007', 'Angelo', 'Villanueva', 'INVENTORY CLERK',
     'regular', '2023-04-03', 1500000, 'monthly', 'S',
     '34-8123407-7', '12-100000007-3', '2001-0001-0007', '301-201-107-000',
     NULL, TRUE),
    (v_cid, 'PTC-005', 'Roberto', 'Torres', 'LOGISTICS SUPERVISOR',
     'regular', '2021-08-16', 2600000, 'monthly', 'S',
     '34-8123405-5', '12-100000005-3', '2001-0001-0005', '301-201-105-000',
     NULL, TRUE),
    (v_cid, 'PTC-008', 'Patricia', 'Aquino', 'DELIVERY DRIVER',
     'regular', '2022-07-18', 1500000, 'monthly', 'ME1',
     '34-8123408-8', '12-100000008-3', '2001-0001-0008', '301-201-108-000',
     'GCash 0917-800-0008', TRUE),
    (v_cid, 'PTC-009', 'Fernando', 'Ramos', 'DELIVERY DRIVER',
     'regular', '2023-01-09', 1500000, 'monthly', 'S',
     '34-8123409-9', '12-100000009-3', '2001-0001-0009', '301-201-109-000',
     NULL, FALSE);  -- RESIGNED

  -- ── Sales & Marketing (8 employees: PTC-011 to PTC-018) ───────────────────
  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status,
    sss_no, philhealth_no, pagibig_no, bir_tin, bank_account, is_active
  ) VALUES
    (v_cid, 'PTC-018', 'Teresa', 'Castillo', 'AREA SALES MANAGER',
     'regular', '2020-03-02', 5000000, 'monthly', 'ME3',
     '34-8123418-8', '12-100000018-3', '2001-0002-0018', '301-202-118-000',
     'BPI 1234-5678-18', TRUE),
    (v_cid, 'PTC-014', 'Sofia', 'Lopez', 'SALES SUPERVISOR',
     'regular', '2020-09-07', 2800000, 'monthly', 'ME1',
     '34-8123414-4', '12-100000014-3', '2001-0002-0014', '301-202-114-000',
     'BPI 1234-5678-14', TRUE),
    (v_cid, 'PTC-015', 'Rafael', 'Martinez', 'SALES SUPERVISOR',
     'regular', '2021-01-11', 2600000, 'monthly', 'S',
     '34-8123415-5', '12-100000015-3', '2001-0002-0015', '301-202-115-000',
     'Metrobank 456-789-0015', TRUE),
    (v_cid, 'PTC-011', 'Miguel', 'Bautista', 'SALES REPRESENTATIVE',
     'regular', '2021-06-01', 1600000, 'monthly', 'S',
     '34-8123411-1', '12-100000011-3', '2001-0002-0011', '301-202-111-000',
     'BDO 0012-3456-0011', TRUE),
    (v_cid, 'PTC-012', 'Lorna', 'Gonzales', 'SALES CLERK',
     'regular', '2022-02-14', 1400000, 'monthly', 'ME',
     '34-8123412-2', '12-100000012-3', '2001-0002-0012', '301-202-112-000',
     NULL, TRUE),
    (v_cid, 'PTC-013', 'Andres', 'Hernandez', 'SALES REPRESENTATIVE',
     'probationary', '2025-06-02', 1400000, 'monthly', 'S',
     '34-8123413-3', '12-100000013-3', '2001-0002-0013', '301-202-113-000',
     'Maya 0921-300-0013', TRUE),
    (v_cid, 'PTC-016', 'Cristina', 'Rivera', 'ACCOUNT EXECUTIVE',
     'regular', '2020-04-20', 3500000, 'monthly', 'ME2',
     '34-8123416-6', '12-100000016-3', '2001-0002-0016', '301-202-116-000',
     'BDO 0012-3456-0016', TRUE),
    (v_cid, 'PTC-017', 'Marco', 'Navarro', 'ACCOUNT EXECUTIVE',
     'regular', '2022-09-05', 3200000, 'monthly', 'S',
     '34-8123417-7', '12-100000017-3', '2001-0002-0017', '301-202-117-000',
     NULL, FALSE);  -- RESIGNED

  -- ── Finance (6 employees: PTC-019 to PTC-024) ────────────────────────────
  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status,
    sss_no, philhealth_no, pagibig_no, bir_tin, bank_account, is_active
  ) VALUES
    (v_cid, 'PTC-024', 'Victoria', 'Garcia', 'FINANCE MANAGER',
     'regular', '2020-07-01', 5500000, 'monthly', 'ME2',
     '34-8123424-4', '12-100000024-3', '2001-0003-0024', '301-203-124-000',
     'BDO 0012-3456-0024', TRUE),
    (v_cid, 'PTC-019', 'Gabriel', 'Soriano', 'SENIOR ACCOUNTANT',
     'regular', '2021-05-03', 2800000, 'monthly', 'S',
     '34-8123419-9', '12-100000019-3', '2001-0003-0019', '301-203-119-000',
     'BDO 0012-3456-0019', TRUE),
    (v_cid, 'PTC-020', 'Angelica', 'Pascual', 'JUNIOR ACCOUNTANT',
     'regular', '2022-08-01', 2200000, 'monthly', 'ME',
     '34-8123420-0', '12-100000020-3', '2001-0003-0020', '301-203-120-000',
     'BPI 1234-5678-20', TRUE),
    (v_cid, 'PTC-021', 'Dennis', 'Santos', 'BOOKKEEPER',
     'regular', '2023-03-13', 1800000, 'monthly', 'S',
     '34-8123421-1', '12-100000021-3', '2001-0003-0021', '301-203-121-000',
     NULL, TRUE),
    (v_cid, 'PTC-023', 'Paolo', 'Reyes', 'BILLING CLERK',
     'regular', '2022-11-07', 1800000, 'monthly', 'ME1',
     '34-8123423-3', '12-100000023-3', '2001-0003-0023', '301-203-123-000',
     'Metrobank 456-789-0023', TRUE),
    (v_cid, 'PTC-022', 'Jasmine', 'Cruz', 'CASHIER',
     'regular', '2024-01-08', 1400000, 'monthly', 'S',
     '34-8123422-2', '12-100000022-3', '2001-0003-0022', '301-203-122-000',
     'GCash 0917-800-0022', TRUE);

  -- ── Admin & HR (6 employees: PTC-025 to PTC-030) ──────────────────────────
  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status,
    sss_no, philhealth_no, pagibig_no, bir_tin, bank_account, is_active
  ) VALUES
    (v_cid, 'PTC-027', 'Jonathan', 'Villanueva', 'ADMIN & HR MANAGER',
     'regular', '2020-11-02', 3800000, 'monthly', 'ME1',
     '34-8123427-7', '12-100000027-3', '2001-0004-0027', '301-204-127-000',
     'BDO 0012-3456-0027', TRUE),
    (v_cid, 'PTC-026', 'Maricel', 'Mendoza', 'HR OFFICER',
     'regular', '2021-02-01', 2800000, 'monthly', 'ME',
     '34-8123426-6', '12-100000026-3', '2001-0004-0026', '301-204-126-000',
     'BPI 1234-5678-26', TRUE),
    (v_cid, 'PTC-029', 'Jerome', 'Ramos', 'IT SUPPORT SPECIALIST',
     'regular', '2022-05-16', 2400000, 'monthly', 'S',
     '34-8123429-9', '12-100000029-3', '2001-0004-0029', '301-204-129-000',
     'GCash 0917-800-0029', TRUE),
    (v_cid, 'PTC-025', 'Kenneth', 'Torres', 'ADMIN CLERK',
     'regular', '2023-06-19', 1500000, 'monthly', 'S',
     '34-8123425-5', '12-100000025-3', '2001-0004-0025', '301-204-125-000',
     NULL, TRUE),
    (v_cid, 'PTC-028', 'Anna', 'Aquino', 'RECEPTIONIST',
     'regular', '2024-03-04', 1300000, 'monthly', 'S',
     '34-8123428-8', '12-100000028-3', '2001-0004-0028', '301-204-128-000',
     NULL, TRUE),
    (v_cid, 'PTC-030', 'Bianca', 'Dela Cruz', 'ADMIN CLERK',
     'probationary', '2025-10-01', 1400000, 'monthly', 'S',
     '34-8123430-0', '12-100000030-3', '2001-0004-0030', '301-204-130-000',
     NULL, FALSE);  -- RESIGNED

  RAISE NOTICE 'Palawan Trading Corp: 35 employees created with org ladder.';

  -- ═══════════════════════════════════════════════════════════════════════════
  -- 5. PAY PERIODS — 36 semi-monthly periods (Oct 2024 – Mar 2026)
  -- ═══════════════════════════════════════════════════════════════════════════
  pp_ids := ARRAY[]::UUID[];

  FOR v_year IN 2024..2026 LOOP
    FOR v_month IN 1..12 LOOP
      -- Only generate Oct 2024 onwards, up to Mar 2026
      IF (v_year = 2024 AND v_month < 10) THEN CONTINUE; END IF;
      IF (v_year = 2026 AND v_month > 3)  THEN CONTINUE; END IF;

      FOR v_half IN 1..2 LOOP
        IF v_half = 1 THEN
          v_period_start := make_date(v_year, v_month, 1);
          v_period_end   := make_date(v_year, v_month, 15);
        ELSE
          v_period_start := make_date(v_year, v_month, 16);
          -- Last day of month
          v_period_end   := (make_date(v_year, v_month, 1) + INTERVAL '1 month' - INTERVAL '1 day')::DATE;
        END IF;

        -- Payment date = 5 days after period_end
        v_payment_date := v_period_end + 5;

        v_pp_count := v_pp_count + 1;

        -- Last 2 periods (Mar 2026 both halves) are draft, rest are paid
        IF v_year = 2026 AND v_month = 3 THEN
          v_status := 'draft';
        ELSE
          v_status := 'paid';
        END IF;

        INSERT INTO pay_periods (company_id, period_start, period_end, payment_date, status)
        VALUES (v_cid, v_period_start, v_period_end, v_payment_date, v_status)
        RETURNING id INTO v_pp_id;

        pp_ids := pp_ids || v_pp_id;
      END LOOP;
    END LOOP;
  END LOOP;

  RAISE NOTICE 'Palawan Trading Corp: % pay periods created.', v_pp_count;

  -- ═══════════════════════════════════════════════════════════════════════════
  -- 6. PAYROLL ENTRIES — 32 active employees × 36 periods = 1,152 rows
  --    Government contributions use 2025 Philippine rates.
  --    All values are semi-monthly (monthly / 2).
  -- ═══════════════════════════════════════════════════════════════════════════

  FOR emp_rec IN (
    SELECT id, employee_no, basic_salary, position
    FROM employees
    WHERE company_id = v_cid AND is_active
    ORDER BY employee_no
  ) LOOP

    v_basic_salary := emp_rec.basic_salary;  -- monthly, centavos
    v_basic_pay    := v_basic_salary / 2;    -- semi-monthly
    v_salary_php   := v_basic_salary / 100.0; -- monthly pesos

    -- ── SSS: EE 4.5%, ER 9.5% on MSC (capped at ₱35,000 for 2025) ──
    v_msc    := LEAST(GREATEST(ROUND(v_salary_php / 500.0) * 500.0, 5000.0), 35000.0);
    v_sss_ee := (ROUND(v_msc * 0.045) * 100)::BIGINT / 2;  -- semi-monthly
    v_sss_er := (ROUND(v_msc * 0.095) * 100)::BIGINT / 2;

    -- ── PhilHealth: 2.5% EE, 2.5% ER, floor ₱10k, ceiling ₱100k ──
    v_phic_ee := (ROUND(LEAST(GREATEST(v_salary_php, 10000.0), 100000.0) * 0.025) * 100)::BIGINT / 2;
    v_phic_er := v_phic_ee;

    -- ── Pag-IBIG: EE 2% (1% if ≤₱1,500), ER 2%, max ₱200/mo each ──
    IF v_salary_php <= 1500 THEN
      v_hdmf_ee := LEAST((ROUND(v_salary_php * 0.01) * 100)::BIGINT, 20000::BIGINT) / 2;
    ELSE
      v_hdmf_ee := LEAST((ROUND(v_salary_php * 0.02) * 100)::BIGINT, 20000::BIGINT) / 2;
    END IF;
    v_hdmf_er := LEAST((ROUND(v_salary_php * 0.02) * 100)::BIGINT, 20000::BIGINT) / 2;

    -- ── Withholding Tax (TRAIN Law semi-monthly brackets) ──
    -- Compute on semi-monthly taxable income
    v_taxable := (v_basic_pay - v_sss_ee - v_phic_ee - v_hdmf_ee) / 100.0;

    v_wtax := CASE
      WHEN v_taxable <=  10417 THEN 0
      WHEN v_taxable <=  16666 THEN ROUND((v_taxable -  10417) * 0.20)::BIGINT * 100
      WHEN v_taxable <=  33333 THEN ROUND((1250   + (v_taxable - 16667) * 0.25))::BIGINT * 100
      WHEN v_taxable <=  83333 THEN ROUND((5416.67 + (v_taxable - 33334) * 0.30))::BIGINT * 100
      WHEN v_taxable <= 333333 THEN ROUND((20416.67 + (v_taxable - 83334) * 0.32))::BIGINT * 100
      ELSE                          ROUND((100416.67 + (v_taxable - 333334) * 0.35))::BIGINT * 100
    END;

    -- Determine department for this employee (by position/employee_no range)
    v_dept_name := CASE
      WHEN emp_rec.employee_no <= 'PTC-010' THEN 'Operations'
      WHEN emp_rec.employee_no <= 'PTC-018' THEN 'Sales'
      WHEN emp_rec.employee_no <= 'PTC-024' THEN 'Finance'
      WHEN emp_rec.employee_no <= 'PTC-030' THEN 'Admin'
      ELSE 'Executive'
    END;

    -- Recurring loan deductions for select employees (semi-monthly)
    v_sss_loan := CASE
      WHEN emp_rec.employee_no IN ('PTC-004', 'PTC-006', 'PTC-014', 'PTC-023') THEN 150000  -- ₱1,500
      ELSE 0
    END;
    v_pagibig_loan := CASE
      WHEN emp_rec.employee_no IN ('PTC-001', 'PTC-008', 'PTC-026') THEN 100000  -- ₱1,000
      ELSE 0
    END;

    -- Loop through all 36 pay periods
    FOR j IN 1..array_length(pp_ids, 1) LOOP

      -- Deterministic seed for pseudo-random variation per employee-period
      v_seed := (CAST(SUBSTRING(emp_rec.employee_no FROM 5) AS INT) * 100) + j;

      -- Determine month from period index (2 periods per month)
      -- j=1,2 => Oct 2024; j=3,4 => Nov 2024; ... j=35,36 => Mar 2026
      v_month := ((j - 1) / 2)::INT;  -- 0-based month offset
      v_month := ((v_month + 10 - 1) % 12) + 1;  -- actual month (Oct=10, Nov=11, ... Sep=9)

      -- ── Overtime pay ──
      -- Operations staff sometimes have overtime, others rarely
      IF v_dept_name = 'Operations' AND emp_rec.position != 'Operations Manager' THEN
        IF (v_seed % 3) = 0 THEN
          v_ot_pay := (500 + (v_seed % 4500))::BIGINT;  -- 500-5000 centavos
        ELSE
          v_ot_pay := 0;
        END IF;
      ELSIF v_dept_name IN ('Sales', 'Admin') THEN
        IF (v_seed % 7) = 0 THEN
          v_ot_pay := (500 + (v_seed % 3000))::BIGINT;
        ELSE
          v_ot_pay := 0;
        END IF;
      ELSE
        v_ot_pay := 0;  -- Executives and Finance managers no OT
      END IF;

      -- ── Holiday pay ──
      -- Non-zero in months with Philippine holidays: Dec, Jan, Apr, Jun, Aug, Nov
      IF v_month IN (12, 1, 4, 6, 8, 11) THEN
        v_holiday_pay := (v_basic_pay * (50 + (v_seed % 150)) / 10000)::BIGINT;  -- 0.5% - 2% of basic
      ELSE
        v_holiday_pay := 0;
      END IF;

      -- ── Night differential ──
      -- Only for Operations warehouse/logistics/delivery staff
      IF v_dept_name = 'Operations' AND emp_rec.position IN ('Warehouse Staff', 'Delivery Driver') THEN
        IF (v_seed % 4) < 2 THEN
          v_nsd_pay := (v_basic_pay * 3 / 100)::BIGINT;  -- ~3% of semi-monthly basic
        ELSE
          v_nsd_pay := 0;
        END IF;
      ELSE
        v_nsd_pay := 0;
      END IF;

      -- ── Nontaxable allowances (rice/meal) ──
      IF (v_seed % 5) < 2 THEN
        v_allow_nt := (1000 + (v_seed % 2000))::BIGINT;  -- 1000-3000 centavos
      ELSE
        v_allow_nt := 0;
      END IF;

      v_allow_t := 0;  -- no taxable allowances

      -- ── Commission (Sales dept only) ──
      IF v_dept_name = 'Sales' THEN
        IF (v_seed % 3) != 0 THEN
          v_commission := (1000 + (v_seed % 9000))::BIGINT;  -- 1000-10000 centavos
        ELSE
          v_commission := 0;
        END IF;
      ELSE
        v_commission := 0;
      END IF;

      -- ── 13th month accrual ──
      -- Per semi-monthly period: basic_salary / 24
      v_13th := (v_basic_salary / 24)::BIGINT;

      -- ── Gross pay ──
      v_gross := v_basic_pay + v_ot_pay + v_holiday_pay + v_nsd_pay
                 + v_allow_nt + v_allow_t + v_commission;

      -- ── Absent deduction ──
      IF (v_seed % 10) = 0 THEN
        v_absent_ded := (1000 + (v_seed % 4000))::BIGINT;  -- 1000-5000 centavos
      ELSE
        v_absent_ded := 0;
      END IF;

      -- ── Cash advance / other deductions ──
      IF (v_seed % 12) = 0 THEN
        v_cash_advance := (200000 + (v_seed % 300000))::BIGINT;  -- ₱2,000-₱5,000
      ELSE
        v_cash_advance := 0;
      END IF;

      v_other_ded := 0;

      -- ── Total deductions ──
      v_tot_ded := v_sss_ee + v_phic_ee + v_hdmf_ee + v_wtax
                   + v_sss_loan + v_pagibig_loan + v_cash_advance + v_other_ded;

      -- ── Net pay ──
      v_net := v_gross - v_tot_ded - v_absent_ded;

      INSERT INTO payroll_entries (
        pay_period_id, employee_id,
        basic_pay, overtime_pay, holiday_pay, night_differential,
        allowances_nontaxable, allowances_taxable, commission,
        thirteenth_month_accrual, gross_pay,
        sss_employee, philhealth_employee, pagibig_employee,
        sss_employer, philhealth_employer, pagibig_employer,
        withholding_tax,
        sss_loan, pagibig_loan, cash_advance, other_deductions,
        absent_deduction, total_deductions, net_pay
      ) VALUES (
        pp_ids[j], emp_rec.id,
        v_basic_pay, v_ot_pay, v_holiday_pay, v_nsd_pay,
        v_allow_nt, v_allow_t, v_commission,
        v_13th, v_gross,
        v_sss_ee, v_phic_ee, v_hdmf_ee,
        v_sss_er, v_phic_er, v_hdmf_er,
        v_wtax,
        v_sss_loan, v_pagibig_loan, v_cash_advance, v_other_ded,
        v_absent_ded, v_tot_ded, v_net
      );

    END LOOP;  -- pay periods
  END LOOP;  -- employees

  RAISE NOTICE 'Palawan Trading Corp: payroll entries created for 32 active employees × 36 periods.';
  RAISE NOTICE 'Seed complete.';

END $$;


-- ============================================================
-- PART 2: Schedules + Employee Profiles + Schedule Assignment
-- ============================================================
-- Run AFTER the main block above (needs company & employee IDs to exist)

DO $$
DECLARE
  v_cid         UUID;
  s_standard    UUID;
  s_warehouse   UUID;
  s_exec        UUID;
  emp_rec       RECORD;
  v_dob         DATE;
  v_sex         TEXT;
  v_civil       TEXT;
  v_seed        INT := 0;
  v_middle      TEXT;
  v_mobile      TEXT;
  v_street      TEXT;
  v_brgy        TEXT;
  v_emergency   TEXT;
  v_rel         TEXT;
  v_degree      TEXT;
  v_school      TEXT;
  v_grad_yr     INT;

  -- Arrays for random-ish data
  midnames      TEXT[] := ARRAY['A.','B.','C.','D.','E.','G.','J.','L.','M.','N.','P.','R.','S.','T.'];
  streets       TEXT[] := ARRAY['123 Rizal St.','45 Mabini Ave.','78 Quezon Blvd.','12 Bonifacio Dr.',
                                '56 Luna St.','90 Del Pilar Rd.','34 Burgos Ave.','67 Aguinaldo St.',
                                '23 Malacanang Dr.','89 Katipunan Ave.','15 Magsaysay Blvd.',
                                '42 Osmena St.','77 Roxas Ave.','31 Laurel Dr.','63 Quirino Blvd.'];
  brgys         TEXT[] := ARRAY['Brgy. San Pedro','Brgy. San Miguel','Brgy. Sta. Monica','Brgy. Mandaragat',
                                'Brgy. Bancao-Bancao','Brgy. San Jose','Brgy. Tagburos','Brgy. Tiniguiban',
                                'Brgy. Irawan','Brgy. Sicsican','Brgy. Bagong Sikat','Brgy. Maligaya'];
  em_names      TEXT[] := ARRAY['Maria Santos','Jose Cruz','Elena Reyes','Pedro Garcia','Rosa Torres',
                                'Juan Mendoza','Carmen Navarro','Roberto Gonzales','Ana Lopez','Luis Rivera',
                                'Sofia Castillo','Miguel Aquino','Teresa Ramos','Antonio Bautista','Linda Pascual'];
  em_rels       TEXT[] := ARRAY['Mother','Father','Spouse','Sister','Brother','Aunt','Uncle'];
  schools       TEXT[] := ARRAY['Palawan State University','Holy Trinity University','Western Philippines University',
                                'University of the Philippines','Polytechnic University','Technological University',
                                'De La Salle University','Ateneo de Manila','University of Santo Tomas',
                                'Mapua University','FEU Institute of Technology','Adamson University'];
  degrees       TEXT[] := ARRAY['BS Business Administration','BS Accountancy','BS Information Technology',
                                'BS Management','BS Marketing','BS Computer Science','AB Communication',
                                'BS Industrial Engineering','BS HRM','BS Customs Administration',
                                'BS Office Administration','BS Entrepreneurship'];
BEGIN

  -- Get company ID
  SELECT id INTO v_cid FROM companies WHERE name = 'Palawan Trading Corp.';
  IF v_cid IS NULL THEN
    RAISE EXCEPTION 'Palawan Trading Corp. not found. Run Part 1 first.';
  END IF;

  -- ═══════════════════════════════════════════════════════════════════════════
  -- SCHEDULES
  -- ═══════════════════════════════════════════════════════════════════════════

  -- Delete old schedules for this company
  UPDATE employees SET schedule_id = NULL WHERE company_id = v_cid;
  DELETE FROM schedules WHERE company_id = v_cid;

  INSERT INTO schedules (company_id, name, start_time, end_time, break_minutes, work_days, is_overnight)
  VALUES (v_cid, 'Standard Day', '08:00', '17:00', 60,
          ARRAY['Monday','Tuesday','Wednesday','Thursday','Friday'], false)
  RETURNING id INTO s_standard;

  INSERT INTO schedules (company_id, name, start_time, end_time, break_minutes, work_days, is_overnight)
  VALUES (v_cid, 'Warehouse Shift', '07:00', '16:00', 60,
          ARRAY['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'], false)
  RETURNING id INTO s_warehouse;

  INSERT INTO schedules (company_id, name, start_time, end_time, break_minutes, work_days, is_overnight)
  VALUES (v_cid, 'Executive Flex', '09:00', '18:00', 60,
          ARRAY['Monday','Tuesday','Wednesday','Thursday','Friday'], false)
  RETURNING id INTO s_exec;

  -- Assign schedules based on position
  UPDATE employees SET schedule_id = s_warehouse
    WHERE company_id = v_cid
      AND position IN ('WAREHOUSE STAFF','DELIVERY DRIVER','INVENTORY CLERK','WAREHOUSE SUPERVISOR','LOGISTICS SUPERVISOR');

  UPDATE employees SET schedule_id = s_exec
    WHERE company_id = v_cid
      AND position IN ('GENERAL MANAGER','VP OPERATIONS','VP SALES & MARKETING','VP FINANCE & ADMIN','EXECUTIVE ASSISTANT');

  UPDATE employees SET schedule_id = s_standard
    WHERE company_id = v_cid AND schedule_id IS NULL;

  RAISE NOTICE 'Schedules created and assigned.';

  -- ═══════════════════════════════════════════════════════════════════════════
  -- EMPLOYEE PROFILES
  -- ═══════════════════════════════════════════════════════════════════════════

  -- Delete old profiles for this company
  DELETE FROM employee_profiles WHERE company_id = v_cid;

  FOR emp_rec IN
    SELECT id, employee_no, first_name, last_name, date_hired, position
    FROM employees
    WHERE company_id = v_cid
    ORDER BY employee_no
  LOOP
    v_seed := v_seed + 1;

    -- Deterministic pseudo-random selections
    v_middle := midnames[1 + (v_seed % array_length(midnames, 1))];
    v_sex := CASE WHEN v_seed % 3 = 0 THEN 'Male' ELSE 'Female' END;
    v_civil := CASE
      WHEN v_seed % 5 = 0 THEN 'Married'
      WHEN v_seed % 5 = 1 THEN 'Single'
      WHEN v_seed % 5 = 2 THEN 'Married'
      WHEN v_seed % 5 = 3 THEN 'Single'
      ELSE 'Widowed'
    END;
    v_dob := DATE '1975-01-15' + (v_seed * 347) * INTERVAL '1 day';
    -- Keep DOB in realistic range (1975-2000)
    IF v_dob > DATE '2000-12-31' THEN
      v_dob := v_dob - INTERVAL '25 years';
    END IF;
    IF v_dob < DATE '1970-01-01' THEN
      v_dob := v_dob + INTERVAL '10 years';
    END IF;

    v_mobile := '09' || LPAD(((170000000 + v_seed * 7654321)::BIGINT % 1000000000::BIGINT)::TEXT, 9, '0');
    v_street := streets[1 + (v_seed % array_length(streets, 1))];
    v_brgy   := brgys[1 + (v_seed % array_length(brgys, 1))];

    v_emergency := em_names[1 + (v_seed % array_length(em_names, 1))];
    v_rel       := em_rels[1 + (v_seed % array_length(em_rels, 1))];

    v_degree  := degrees[1 + (v_seed % array_length(degrees, 1))];
    v_school  := schools[1 + (v_seed % array_length(schools, 1))];
    v_grad_yr := 2000 + (v_seed % 20);

    INSERT INTO employee_profiles (
      employee_id, company_id,
      middle_name, date_of_birth, sex, civil_status,
      nationality, religion, mobile_no,
      present_address_street, present_address_barangay,
      present_address_city, present_address_province, present_address_zip,
      perm_address_same,
      emergency_name, emergency_relationship, emergency_phone,
      education_degree, education_school, education_year,
      department, regularization_date
    ) VALUES (
      emp_rec.id, v_cid,
      v_middle, v_dob, v_sex, v_civil,
      'Filipino', 'Roman Catholic',
      v_mobile,
      v_street, v_brgy,
      'Puerto Princesa', 'Palawan', '5300',
      true,
      v_emergency, v_rel,
      '09' || LPAD(((180000000 + v_seed * 9876543)::BIGINT % 1000000000::BIGINT)::TEXT, 9, '0'),
      v_degree, v_school, v_grad_yr,
      CASE
        WHEN emp_rec.position IN ('WAREHOUSE STAFF','DELIVERY DRIVER','INVENTORY CLERK','WAREHOUSE SUPERVISOR','LOGISTICS SUPERVISOR','OPERATIONS MANAGER') THEN 'Operations'
        WHEN emp_rec.position IN ('SALES REPRESENTATIVE','SALES CLERK','SALES SUPERVISOR','ACCOUNT EXECUTIVE','AREA SALES MANAGER') THEN 'Sales'
        WHEN emp_rec.position IN ('SENIOR ACCOUNTANT','JUNIOR ACCOUNTANT','BOOKKEEPER','CASHIER','BILLING CLERK','FINANCE MANAGER') THEN 'Finance'
        WHEN emp_rec.position IN ('ADMIN CLERK','HR OFFICER','ADMIN & HR MANAGER','RECEPTIONIST','IT SUPPORT SPECIALIST') THEN 'Admin'
        ELSE 'Executive'
      END,
      emp_rec.date_hired + INTERVAL '6 months'
    );

  END LOOP;

  RAISE NOTICE 'Employee profiles created for all 35 employees.';
  RAISE NOTICE 'Part 2 complete: schedules + profiles.';

END $$;
