-- ============================================================
-- SEED: GenXcript Tech Solutions — Full Personnel & Reporting Map
-- ============================================================
-- Run this in the Supabase SQL Editor AFTER running all
-- migrations (001 through 016).
--
-- Creates:
--   • 1 company     — GenXcript Tech Solutions
--   • 4 departments — Leadership, Technology & Product,
--                     Operations & HR, Sales & Growth
--   • 25 employees  — full org chart with salaries & reporting lines
--
-- After running, grant yourself access by replacing
-- <your-auth-uid> with your Supabase Auth user UUID:
--
--   INSERT INTO user_company_access (user_id, company_id, role)
--   SELECT '<your-auth-uid>', id, 'admin'
--   FROM companies WHERE name = 'GenXcript Tech Solutions';
-- ============================================================
--
-- ORG CHART SUMMARY
-- ─────────────────
-- [L4] EXECUTIVE LEADERSHIP
--       Emil Aguila — CEO
--
-- [L3] DEPARTMENTAL MANAGEMENT
--       Dom Salvatierra — CTO          (→ Emil)
--       Tess Madrigal   — Ops Director (→ Emil)
--       Teo Lacson      — Sales Dir.   (→ Emil)
--       Amara Sison     — Sr. Lead Dev (→ Dom)
--
-- [L2] SENIOR PROFESSIONALS
--       Rena Valerio    — Product Mgr  (→ Dom)
--       Bert Galang     — Finance Lead (→ Tess)
--       Lulu Pineda     — HR Mgr       (→ Tess)
--       Inigo San Jose  — UI/UX Design (→ Dom)
--       Clari Dizon     — Sr. Acct Mgr (→ Teo)
--
-- [L1] ASSOCIATE & SUPPORT STAFF
--       Jeric Lim       — FS Dev       (→ Amara)
--       Rina Malabanan  — FS Dev       (→ Amara)
--       Kenji Sato      — BE Dev       (→ Amara)
--       Thea Gomez      — FE Dev       (→ Amara)
--       Pao Tiongson    — QA/Tester    (→ Amara)
--       Vince Arnaiz    — Acct Mgr     (→ Clari)
--       Jo Tanco        — Sales Rep    (→ Clari)
--       Renzo Capili    — Sales Rep    (→ Clari)
--       Mon Silverio    — Sales Rep    (→ Clari)
--       Diego Ledesma   — Sales Rep    (→ Clari)
--       Sophie Laurel   — Mktg Spec    (→ Teo)
--       Gin Ferrer      — CS Lead      (→ Teo)
--       Mariel Ocampo   — Office Admin (→ Tess)
--       Lei Macaraig    — CS Support   (→ Gino)
--       Monchi Diaz     — CS Support   (→ Gino)
-- ============================================================

DO $$
DECLARE
  v_cid  UUID;   -- company id

  -- Departments
  d_lead UUID;   -- Leadership
  d_tech UUID;   -- Technology & Product
  d_ops  UUID;   -- Operations & HR
  d_sale UUID;   -- Sales & Growth

  -- ── [L4] Executive ──────────────────────────────────────
  e01 UUID;   -- Emilio Aguila        CEO

  -- ── [L3] Management ─────────────────────────────────────
  e02 UUID;   -- Dominic Salvatierra  CTO
  e03 UUID;   -- Teresa Madrigal      Ops & HR Director
  e04 UUID;   -- Mateo Lacson         Sales Director
  e05 UUID;   -- Amara Sison          Sr. Lead Developer

  -- ── [L2] Senior Professionals ───────────────────────────
  e06 UUID;   -- Serena Valerio       Product Manager
  e07 UUID;   -- Roberto Galang       Finance Lead
  e08 UUID;   -- Lourdes Pineda       HR & Payroll Manager
  e09 UUID;   -- Inigo San Jose       UI/UX Designer
  e10 UUID;   -- Clarissa Dizon       Sr. Account Manager

  -- ── [L1] Associates & Support ───────────────────────────
  e11 UUID;   -- Jeric Lim            Full-Stack Developer
  e12 UUID;   -- Rina Malabanan       Full-Stack Developer
  e13 UUID;   -- Kenji Sato           Backend Developer
  e14 UUID;   -- Althea Gomez         Frontend Developer
  e15 UUID;   -- Paolo Tiongson       QA/Tester
  e16 UUID;   -- Vince Arnaiz         Account Manager
  e17 UUID;   -- Joanna Tanco         Sales Rep
  e18 UUID;   -- Renzo Capili         Sales Rep
  e19 UUID;   -- Monica Silverio      Sales Rep
  e20 UUID;   -- Diego Ledesma        Sales Rep
  e21 UUID;   -- Sophia Laurel        Marketing Spec
  e22 UUID;   -- Gino Ferrer          Customer Support Lead
  e23 UUID;   -- Mariel Ocampo        Office Admin
  e24 UUID;   -- Leila Macaraig       Customer Support
  e25 UUID;   -- Ramon Diaz           Customer Support

BEGIN

  -- ────────────────────────────────────────────────────────
  -- 1. COMPANY
  -- ────────────────────────────────────────────────────────
  INSERT INTO companies (
    name, address, region, pay_frequency
  ) VALUES (
    'GenXcript Tech Solutions',
    'Unit 4F, The Hub Building, Alabang-Zapote Rd, Muntinlupa City',
    'NCR',
    'monthly'
  )
  RETURNING id INTO v_cid;

  -- ────────────────────────────────────────────────────────
  -- 2. DEPARTMENTS
  -- ────────────────────────────────────────────────────────
  INSERT INTO departments (company_id, name, code, color, description, sort_order)
  VALUES (
    v_cid, 'Leadership', 'LEAD', '#0284c7',
    'L4 Visibility Layer — executive direction and company strategy', 10
  ) RETURNING id INTO d_lead;

  INSERT INTO departments (company_id, name, code, color, description, sort_order)
  VALUES (
    v_cid, 'Technology & Product', 'TECH', '#6366f1',
    'L3/L2/L1 Execution Layer — engineering, QA, design, and product', 20
  ) RETURNING id INTO d_tech;

  INSERT INTO departments (company_id, name, code, color, description, sort_order)
  VALUES (
    v_cid, 'Operations & HR', 'OPS', '#059669',
    'L3/L2/L1 Enscript Layer — HR, finance, and operational backbone', 30
  ) RETURNING id INTO d_ops;

  INSERT INTO departments (company_id, name, code, color, description, sort_order)
  VALUES (
    v_cid, 'Sales & Growth', 'SALE', '#d97706',
    'L3/L2/L1 Generation Layer — sales, marketing, and customer success', 40
  ) RETURNING id INTO d_sale;

  -- ────────────────────────────────────────────────────────
  -- 3. EMPLOYEES  (inserted without reports_to first;
  --    reporting lines are set via UPDATE in step 4)
  -- ────────────────────────────────────────────────────────

  -- ── [L4] EXECUTIVE LEADERSHIP ───────────────────────────
  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status, is_active
  ) VALUES (
    v_cid, 'EMP-001', 'Emilio', 'Aguila', 'CEO',
    'regular', '2020-01-01', 18000000, 'monthly', 'ME', TRUE
  ) RETURNING id INTO e01;

  -- ── [L3] DEPARTMENTAL MANAGEMENT ────────────────────────
  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status, is_active
  ) VALUES (
    v_cid, 'EMP-002', 'Dominic', 'Salvatierra', 'CTO',
    'regular', '2020-01-15', 14000000, 'monthly', 'ME', TRUE
  ) RETURNING id INTO e02;

  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status, is_active
  ) VALUES (
    v_cid, 'EMP-003', 'Teresa', 'Madrigal', 'Ops & HR Director',
    'regular', '2020-03-01', 9500000, 'monthly', 'ME', TRUE
  ) RETURNING id INTO e03;

  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status, is_active
  ) VALUES (
    v_cid, 'EMP-004', 'Mateo', 'Lacson', 'Sales Director',
    'regular', '2020-07-01', 9000000, 'monthly', 'ME', TRUE
  ) RETURNING id INTO e04;

  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status, is_active
  ) VALUES (
    v_cid, 'EMP-005', 'Amara', 'Sison', 'Sr. Lead Developer',
    'regular', '2020-04-01', 11000000, 'monthly', 'S', TRUE
  ) RETURNING id INTO e05;

  -- ── [L2] SENIOR PROFESSIONALS ───────────────────────────
  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status, is_active
  ) VALUES (
    v_cid, 'EMP-006', 'Serena', 'Valerio', 'Product Manager',
    'regular', '2021-05-01', 8500000, 'monthly', 'ME', TRUE
  ) RETURNING id INTO e06;

  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status, is_active
  ) VALUES (
    v_cid, 'EMP-007', 'Roberto', 'Galang', 'Finance Lead',
    'regular', '2021-01-10', 6500000, 'monthly', 'ME', TRUE
  ) RETURNING id INTO e07;

  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status, is_active
  ) VALUES (
    v_cid, 'EMP-008', 'Lourdes', 'Pineda', 'HR & Payroll Manager',
    'regular', '2020-06-01', 5500000, 'monthly', 'ME', TRUE
  ) RETURNING id INTO e08;

  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status, is_active
  ) VALUES (
    v_cid, 'EMP-009', 'Inigo', 'San Jose', 'UI/UX Designer',
    'regular', '2022-06-01', 5500000, 'monthly', 'S', TRUE
  ) RETURNING id INTO e09;

  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status, is_active
  ) VALUES (
    v_cid, 'EMP-010', 'Clarissa', 'Dizon', 'Sr. Account Manager',
    'regular', '2021-01-15', 5500000, 'monthly', 'S', TRUE
  ) RETURNING id INTO e10;

  -- ── [L1] ASSOCIATE & SUPPORT STAFF ──────────────────────
  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status, is_active
  ) VALUES (
    v_cid, 'EMP-011', 'Jeric', 'Lim', 'Full-Stack Developer',
    'regular', '2021-02-01', 7500000, 'monthly', 'S', TRUE
  ) RETURNING id INTO e11;

  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status, is_active
  ) VALUES (
    v_cid, 'EMP-012', 'Rina', 'Malabanan', 'Full-Stack Developer',
    'regular', '2021-02-01', 7500000, 'monthly', 'S', TRUE
  ) RETURNING id INTO e12;

  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status, is_active
  ) VALUES (
    v_cid, 'EMP-013', 'Kenji', 'Sato', 'Backend Developer',
    'regular', '2021-08-01', 7000000, 'monthly', 'S', TRUE
  ) RETURNING id INTO e13;

  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status, is_active
  ) VALUES (
    v_cid, 'EMP-014', 'Althea', 'Gomez', 'Frontend Developer',
    'regular', '2022-01-10', 6500000, 'monthly', 'S', TRUE
  ) RETURNING id INTO e14;

  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status, is_active
  ) VALUES (
    v_cid, 'EMP-015', 'Paolo', 'Tiongson', 'QA/Tester',
    'regular', '2022-03-01', 4500000, 'monthly', 'S', TRUE
  ) RETURNING id INTO e15;

  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status, is_active
  ) VALUES (
    v_cid, 'EMP-016', 'Vince', 'Arnaiz', 'Account Manager',
    'regular', '2021-08-01', 4500000, 'monthly', 'S', TRUE
  ) RETURNING id INTO e16;

  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status, is_active
  ) VALUES (
    v_cid, 'EMP-017', 'Joanna', 'Tanco', 'Sales Rep',
    'regular', '2022-01-10', 3000000, 'monthly', 'S', TRUE
  ) RETURNING id INTO e17;

  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status, is_active
  ) VALUES (
    v_cid, 'EMP-018', 'Renzo', 'Capili', 'Sales Rep',
    'regular', '2022-03-01', 3000000, 'monthly', 'S', TRUE
  ) RETURNING id INTO e18;

  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status, is_active
  ) VALUES (
    v_cid, 'EMP-019', 'Monica', 'Silverio', 'Sales Rep',
    'regular', '2022-06-01', 3000000, 'monthly', 'S', TRUE
  ) RETURNING id INTO e19;

  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status, is_active
  ) VALUES (
    v_cid, 'EMP-020', 'Diego', 'Ledesma', 'Sales Rep',
    'regular', '2023-01-09', 3000000, 'monthly', 'S', TRUE
  ) RETURNING id INTO e20;

  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status, is_active
  ) VALUES (
    v_cid, 'EMP-021', 'Sophia', 'Laurel', 'Marketing Spec',
    'regular', '2022-09-01', 4000000, 'monthly', 'S', TRUE
  ) RETURNING id INTO e21;

  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status, is_active
  ) VALUES (
    v_cid, 'EMP-022', 'Gino', 'Ferrer', 'Customer Support Lead',
    'regular', '2021-04-01', 3500000, 'monthly', 'S', TRUE
  ) RETURNING id INTO e22;

  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status, is_active
  ) VALUES (
    v_cid, 'EMP-023', 'Mariel', 'Ocampo', 'Office Admin',
    'regular', '2021-06-15', 2800000, 'monthly', 'S', TRUE
  ) RETURNING id INTO e23;

  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status, is_active
  ) VALUES (
    v_cid, 'EMP-024', 'Leila', 'Macaraig', 'Customer Support',
    'regular', '2022-11-01', 2500000, 'monthly', 'S', TRUE
  ) RETURNING id INTO e24;

  INSERT INTO employees (
    company_id, employee_no, first_name, last_name, position,
    employment_type, date_hired, basic_salary, salary_type, tax_status, is_active
  ) VALUES (
    v_cid, 'EMP-025', 'Ramon', 'Diaz', 'Customer Support',
    'regular', '2023-03-01', 2500000, 'monthly', 'S', TRUE
  ) RETURNING id INTO e25;

  -- ────────────────────────────────────────────────────────
  -- 4. REPORTING LINES  (reports_to)
  -- ────────────────────────────────────────────────────────
  -- [L4] Emil → nobody (CEO)
  -- [L3] Direct reports to Emil
  UPDATE employees SET reports_to = e01 WHERE id IN (e02, e03, e04);
  -- [L3] Amara reports to Dominic (also L3, team lead role)
  UPDATE employees SET reports_to = e02 WHERE id = e05;

  -- [L2] Direct reports to Dominic
  UPDATE employees SET reports_to = e02 WHERE id IN (e06, e09);
  -- [L2] Direct reports to Teresa
  UPDATE employees SET reports_to = e03 WHERE id IN (e07, e08);
  -- [L2] Direct reports to Mateo
  UPDATE employees SET reports_to = e04 WHERE id = e10;

  -- [L1] Direct reports to Amara (dev team)
  UPDATE employees SET reports_to = e05 WHERE id IN (e11, e12, e13, e14, e15);
  -- [L1] Direct reports to Clarissa (sales team)
  UPDATE employees SET reports_to = e10 WHERE id IN (e16, e17, e18, e19, e20);
  -- [L1] Sophie & Gino report to Mateo
  UPDATE employees SET reports_to = e04 WHERE id IN (e21, e22);
  -- [L1] Mariel reports to Teresa
  UPDATE employees SET reports_to = e03 WHERE id = e23;
  -- [L1] Leila & Ramon report to Gino
  UPDATE employees SET reports_to = e22 WHERE id IN (e24, e25);

  -- ────────────────────────────────────────────────────────
  -- 5. EMPLOYEE PROFILES
  --    department text (legacy) + department_id FK (structured)
  -- ────────────────────────────────────────────────────────
  INSERT INTO employee_profiles (employee_id, company_id, department, department_id) VALUES
    -- Leadership
    (e01, v_cid, 'Leadership',           d_lead),
    -- Technology & Product
    (e02, v_cid, 'Technology & Product', d_tech),
    (e05, v_cid, 'Technology & Product', d_tech),
    (e06, v_cid, 'Technology & Product', d_tech),
    (e09, v_cid, 'Technology & Product', d_tech),
    (e11, v_cid, 'Technology & Product', d_tech),
    (e12, v_cid, 'Technology & Product', d_tech),
    (e13, v_cid, 'Technology & Product', d_tech),
    (e14, v_cid, 'Technology & Product', d_tech),
    (e15, v_cid, 'Technology & Product', d_tech),
    -- Operations & HR
    (e03, v_cid, 'Operations & HR',      d_ops),
    (e07, v_cid, 'Operations & HR',      d_ops),
    (e08, v_cid, 'Operations & HR',      d_ops),
    (e23, v_cid, 'Operations & HR',      d_ops),
    -- Sales & Growth
    (e04, v_cid, 'Sales & Growth',       d_sale),
    (e10, v_cid, 'Sales & Growth',       d_sale),
    (e16, v_cid, 'Sales & Growth',       d_sale),
    (e17, v_cid, 'Sales & Growth',       d_sale),
    (e18, v_cid, 'Sales & Growth',       d_sale),
    (e19, v_cid, 'Sales & Growth',       d_sale),
    (e20, v_cid, 'Sales & Growth',       d_sale),
    (e21, v_cid, 'Sales & Growth',       d_sale),
    (e22, v_cid, 'Sales & Growth',       d_sale),
    (e24, v_cid, 'Sales & Growth',       d_sale),
    (e25, v_cid, 'Sales & Growth',       d_sale);

  -- ────────────────────────────────────────────────────────
  -- 6. CONFIRMATION
  -- ────────────────────────────────────────────────────────
  RAISE NOTICE '================================================';
  RAISE NOTICE ' GenXcript Tech Solutions — seed complete!';
  RAISE NOTICE '================================================';
  RAISE NOTICE ' Company ID   : %', v_cid;
  RAISE NOTICE '';
  RAISE NOTICE ' Departments  : 4';
  RAISE NOTICE '   LEAD  Leadership           —  1 employee   (₱180,000/mo)';
  RAISE NOTICE '   TECH  Technology & Product —  9 employees  (₱720,000/mo)';
  RAISE NOTICE '   OPS   Operations & HR      —  4 employees  (₱243,000/mo)';
  RAISE NOTICE '   SALE  Sales & Growth       — 11 employees  (₱435,000/mo)';
  RAISE NOTICE '';
  RAISE NOTICE ' Employees    : 25';
  RAISE NOTICE ' Total Payroll: ₱1,578,000 / month';
  RAISE NOTICE '';
  RAISE NOTICE ' Reporting Tree:';
  RAISE NOTICE '   Emil Aguila (CEO)';
  RAISE NOTICE '   ├─ Dominic Salvatierra (CTO)';
  RAISE NOTICE '   │   ├─ Amara Sison (Sr. Lead Dev)';
  RAISE NOTICE '   │   │   ├─ Jeric Lim, Rina Malabanan, Kenji Sato';
  RAISE NOTICE '   │   │   └─ Althea Gomez, Paolo Tiongson';
  RAISE NOTICE '   │   ├─ Serena Valerio (Product Mgr)';
  RAISE NOTICE '   │   └─ Inigo San Jose (UI/UX)';
  RAISE NOTICE '   ├─ Teresa Madrigal (Ops & HR Dir.)';
  RAISE NOTICE '   │   ├─ Roberto Galang (Finance Lead)';
  RAISE NOTICE '   │   ├─ Lourdes Pineda (HR & Payroll Mgr)';
  RAISE NOTICE '   │   └─ Mariel Ocampo (Office Admin)';
  RAISE NOTICE '   └─ Mateo Lacson (Sales Dir.)';
  RAISE NOTICE '       ├─ Clarissa Dizon (Sr. Acct Mgr)';
  RAISE NOTICE '       │   └─ Vince, Joanna, Renzo, Monica, Diego';
  RAISE NOTICE '       ├─ Sophia Laurel (Mktg Spec)';
  RAISE NOTICE '       └─ Gino Ferrer (CS Lead)';
  RAISE NOTICE '           └─ Leila Macaraig, Ramon Diaz';
  RAISE NOTICE '';
  RAISE NOTICE ' To access in the app, run:';
  RAISE NOTICE '   INSERT INTO user_company_access (user_id, company_id, role)';
  RAISE NOTICE '   VALUES (''<your-auth-uid>'', ''%'', ''admin'');', v_cid;
  RAISE NOTICE '================================================';

END $$;
