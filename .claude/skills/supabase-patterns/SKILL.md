---
description: Supabase architecture patterns for GeNXcript Payroll — database schema conventions, RLS policies, migration standards, storage buckets, and multi-tenant data isolation. Auto-activates when creating tables, writing migrations, configuring RLS, or working with Supabase Storage. Proactively enforces project conventions.
---

# Supabase Patterns Skill (GeNXcript-specific)

## Role
You are the database architect for GeNXcript Payroll SaaS. When working with Supabase (tables, migrations, RLS, storage, queries), you MUST follow these project-specific conventions and **proactively enforce** them.

## Proactive Behavior
- **ENFORCE** naming conventions and schema patterns on every migration
- **FLAG** missing RLS policies, indexes, or constraints
- **SUGGEST** performance optimizations (indexes, query batching)
- **WARN** about multi-tenant data leakage risks
- Format flags as: `⚠️ SUPABASE: [description + fix]`

---

## 1. Schema Conventions

### Table Naming
- **snake_case**, plural: `employees`, `pay_periods`, `time_logs`
- Junction tables: `user_company_access` (not `user_companies`)
- History/log tables: `activity_log`, `remittance_records`

### Column Naming
- **snake_case**: `first_name`, `basic_salary`, `created_at`
- Primary key: `id UUID DEFAULT gen_random_uuid() PRIMARY KEY`
- Foreign keys: `{table_singular}_id` — e.g., `employee_id`, `company_id`
- Timestamps: `created_at TIMESTAMPTZ DEFAULT now()`, `updated_at TIMESTAMPTZ DEFAULT now()`
- Boolean: `is_active`, `is_overnight`, `perm_address_same`
- Money: **INTEGER** (centavos) — `basic_salary INTEGER` stores ₱30,000.00 as `3000000`

### Required Columns on Every Table
```sql
id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
company_id UUID NOT NULL REFERENCES companies(id),
created_at TIMESTAMPTZ DEFAULT now(),
-- updated_at only if rows are mutable
```
- **Flag if**: new table missing `company_id` (except auth-scoped tables like `user_preferences`)
- **Flag if**: monetary column uses DECIMAL, NUMERIC, or FLOAT instead of INTEGER

### Standard Patterns
```sql
-- Soft delete (preferred over hard delete)
is_active BOOLEAN DEFAULT TRUE

-- Enum-like text columns (not Postgres ENUM — easier to add values)
status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'reviewed', 'finalized', 'paid'))

-- Date columns (not TIMESTAMP for pure dates)
holiday_date DATE NOT NULL
period_start DATE NOT NULL
```

---

## 2. Migration Standards

### File Naming
- `{NNN}_{description}.sql` — e.g., `025_reports_to.sql`, `026_employee_photo.sql`
- Check latest number: `ls db/*.sql | sort` before creating
- **Flag if**: migration number conflicts with existing file

### Idempotency
```sql
-- ALWAYS use IF NOT EXISTS / IF EXISTS
ALTER TABLE employees ADD COLUMN IF NOT EXISTS reports_to UUID;
CREATE INDEX IF NOT EXISTS idx_employees_company ON employees(company_id);

-- For policies
DROP POLICY IF EXISTS "policy_name" ON table_name;
CREATE POLICY "policy_name" ON table_name ...;
```
- **Flag if**: migration not idempotent (would fail on re-run)

### Migration Template
```sql
-- Migration {NNN}: {description}
-- Purpose: {what this changes and why}

BEGIN;

-- DDL changes
ALTER TABLE public.{table} ADD COLUMN IF NOT EXISTS {column} {type} {constraints};

-- Indexes (if needed for query performance)
CREATE INDEX IF NOT EXISTS idx_{table}_{column} ON public.{table}({column});

-- RLS policies (if new table or new access pattern)
ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;

CREATE POLICY "{descriptive_name}"
  ON public.{table}
  FOR {SELECT|INSERT|UPDATE|DELETE}
  USING (company_id IN (SELECT get_user_company_ids()));

COMMIT;
```

---

## 3. RLS (Row Level Security) — MANDATORY

### Rules
- **EVERY** public table MUST have RLS enabled
- **EVERY** table with `company_id` MUST have company-scoped policies
- Service role bypasses RLS automatically — no policy needed for admin operations
- **Run `get_advisors(type: "security")` after every migration** to check for violations

### Standard Policy Patterns

#### Company-scoped table (most tables)
```sql
ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;

-- Read: user can see rows for their companies
CREATE POLICY "{table}_select" ON public.{table}
  FOR SELECT USING (
    company_id IN (
      SELECT company_id FROM public.user_company_access
      WHERE user_id = auth.uid()
    )
  );

-- Write: same scope
CREATE POLICY "{table}_insert" ON public.{table}
  FOR INSERT WITH CHECK (
    company_id IN (
      SELECT company_id FROM public.user_company_access
      WHERE user_id = auth.uid()
    )
  );

CREATE POLICY "{table}_update" ON public.{table}
  FOR UPDATE USING (
    company_id IN (
      SELECT company_id FROM public.user_company_access
      WHERE user_id = auth.uid()
    )
  );
```

#### User-scoped table (e.g., user_preferences)
```sql
CREATE POLICY "own_data" ON public.{table}
  FOR ALL USING (auth.uid() = user_id);
```

#### Shared/global table (e.g., holidays with company_id IS NULL)
```sql
CREATE POLICY "read_national" ON public.holidays
  FOR SELECT USING (
    company_id IS NULL  -- national holidays visible to all
    OR company_id IN (SELECT get_user_company_ids())
  );
```

- **Flag if**: table has RLS disabled (check via `get_advisors`)
- **Flag if**: new table created without RLS policies in the same migration

---

## 4. Storage Buckets

### Existing Buckets
| Bucket | Public? | Purpose |
|--------|---------|---------|
| `dtr-snapshots` | Yes | Clock-in/out face photos |
| `employee-photos` | Yes | Employee profile pictures |

### Conventions
- Bucket names: **kebab-case**
- File paths: `{company_id}/{employee_id}.{ext}` or `{company_id}/{date}/{filename}`
- **Always compress** images before upload (max 200px for avatars, 640px for snapshots)
- **Cache-bust** URLs with `?v={timestamp}` parameter
- Clean up old files when replacing (delete then upload)

### Upload Pattern
```python
# Compress → remove old → upload → get URL → bust cache
compressed = _compress_photo(raw_bytes)
path = f"{company_id}/{employee_id}.jpg"
try:
    db.storage.from_("bucket").remove([path])
except:
    pass
db.storage.from_("bucket").upload(
    path, compressed,
    file_options={"content-type": "image/jpeg", "upsert": "true"},
)
url = db.storage.from_("bucket").get_public_url(path)
url += f"?v={int(time.time())}"
```

---

## 5. Query Patterns

### Multi-Tenant Queries
```python
# ALWAYS filter by company_id
db.table("employees").select("*").eq("company_id", get_company_id()).execute()

# NEVER query without company filter (even if RLS protects)
# BAD:
db.table("employees").select("*").execute()  # Returns all companies' data via service role!
```

### Batch Lookups (avoid N+1)
```python
# BAD — N+1
for emp in employees:
    profile = db.table("profiles").select("*").eq("employee_id", emp["id"]).execute()

# GOOD — batch
ids = [e["id"] for e in employees]
profiles = db.table("profiles").select("*").in_("employee_id", ids).execute().data
lookup = {p["employee_id"]: p for p in profiles}
```

### Upsert Pattern
```python
db.table("employee_profiles").upsert({
    "employee_id": emp_id,
    "company_id": get_company_id(),
    **profile_data,
}, on_conflict="employee_id").execute()
```

- **Flag if**: query missing `company_id` filter
- **Flag if**: query inside a loop (N+1 pattern)
- **Flag if**: `select("*")` when only 2-3 columns needed

---

## 6. Connection Management

### Client Factory
```python
# db/connection.py — singleton cached client
@st.cache_resource(ttl=2700)  # 45-minute TTL
def get_db():
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"],
        options=ClientOptions(
            auto_refresh_token=False,  # Service role doesn't need refresh
            persist_session=False,
        )
    )
```

### JWT Expiry Handling
- Catch `PGRST303` and `jwt expired` errors
- Clear `get_db` cache: `get_db.clear()`
- Show user-friendly message, redirect to login
- **Flag if**: JWT error not caught in page render
