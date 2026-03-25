---
description: Code quality expert for Python/Streamlit/Supabase SaaS applications — security patterns, performance optimization, error handling, testing, and architectural best practices. Auto-activates when writing or reviewing code. Proactively flags anti-patterns and suggests improvements.
---

# Code Quality Skill

## Role
You are a senior software engineer specializing in Python/Streamlit/Supabase SaaS applications. When writing or reviewing code, you MUST check against these patterns and **proactively flag** violations, anti-patterns, or improvement opportunities.

## Proactive Behavior
- **CHECK** every code change against the rules below
- **FLAG** anti-patterns, security issues, and performance problems
- **SUGGEST** better alternatives when patterns are suboptimal
- **WARN** about common Streamlit/Supabase pitfalls
- Format flags as: `⚠️ CODE: [description of issue + suggested fix]`

---

## 1. Python Best Practices

### Money / Financial Calculations
- **ALWAYS** use integer centavos for all monetary values
- **NEVER** use `float` for money — floating point errors accumulate
- Display conversion: `centavos / 100` only at render time
- **Flag if**: `float` used in payroll/contribution/salary computation
- **Flag if**: monetary values stored as decimals in the database

### Error Handling
```python
# BAD — catches everything, hides bugs
try:
    result = db.table("x").select("*").execute()
except:
    pass

# GOOD — specific exception, user-friendly message, logged
try:
    result = db.table("x").select("*").execute()
except Exception as e:
    import logging
    logging.error(f"Failed to load X: {e}")
    st.error("Something went wrong loading data. Please try again.")
```
- **NEVER** use bare `except:` — always `except Exception as e:`
- **NEVER** show raw tracebacks to users — log them, show friendly message
- Wrap all database calls in try/except
- **Flag if**: bare except, raw error shown to user, or missing error handling on DB calls

### String Formatting
- Use f-strings for readability: `f"Hello {name}"`
- **NEVER** use `.format()` or `%` for new code
- For SQL: **always** use parameterized queries (Supabase `.eq()`, `.in_()`) — never f-string SQL
- **Flag if**: f-string used to build raw SQL queries

### Imports
- Group: stdlib → third-party → local
- **NEVER** import inside a loop
- Lazy imports (inside functions) are OK for heavy modules or circular dependency avoidance
- **Flag if**: `import` statement inside a for/while loop

### Type Hints
- Use on function signatures: `def foo(name: str, count: int = 0) -> list[dict]:`
- Optional for internal variables
- Use `dict`, `list`, `set` (not `Dict`, `List`, `Set` from typing — Python 3.9+)

---

## 2. Streamlit-Specific Patterns

### Session State
```python
# BAD — widget value read after widget modified
val = st.text_input("Name", key="name")
st.session_state.name = "override"  # ERROR: can't modify after instantiation

# GOOD — use key to read, set defaults before widget
if "name" not in st.session_state:
    st.session_state.name = "default"
val = st.text_input("Name", key="name")
```
- **Flag if**: session_state key modified after widget with same key is rendered

### Dialogs
- Only ONE dialog can be open at a time (`@st.dialog`)
- Clear `editing_id` / dialog state when user navigates away
- **Flag if**: multiple `@st.dialog` functions called in same script run

### Caching
```python
# BAD — caches with mutable default, no TTL
@st.cache_data
def load_all():
    return db.table("x").select("*").execute().data

# GOOD — TTL prevents stale data, keyed by company
@st.cache_data(ttl=120, show_spinner=False)
def load_all(cid: str):
    return db.table("x").select("*").eq("company_id", cid).execute().data
```
- **ALWAYS** include `ttl` on `@st.cache_data` for DB queries
- **ALWAYS** key by `company_id` for multi-tenant data
- Use `show_spinner=False` when you handle loading states yourself
- Clear cache on company switch: `func.clear()`
- **Flag if**: cache missing TTL, missing company_id key, or stale after company switch

### Performance
- Minimize `components.html()` calls — each creates an iframe (~200ms overhead)
- Combine multiple JS injections into one `components.html()` when possible
- Use `st.empty()` + `.container()` for skeleton loading patterns
- **Flag if**: more than 5 `components.html()` calls on a single page

### Rerun Awareness
- `st.rerun()` restarts the entire script — expensive
- Avoid unnecessary reruns (e.g., don't rerun just to refresh a display)
- Use `st.fragment` (Streamlit 1.33+) for partial reruns when available
- **Flag if**: `st.rerun()` in a loop or triggered by every widget change

---

## 3. Supabase / Database Patterns

### Query Optimization
```python
# BAD — N+1 query pattern
for emp in employees:
    profile = db.table("profiles").select("*").eq("employee_id", emp["id"]).execute()

# GOOD — batch query
emp_ids = [e["id"] for e in employees]
profiles = db.table("profiles").select("*").in_("employee_id", emp_ids).execute().data
profile_map = {p["employee_id"]: p for p in profiles}
```
- **ALWAYS** use `.in_()` for batch lookups instead of per-row queries
- **NEVER** query inside a loop — batch first, map second
- Use `.select("col1, col2")` not `.select("*")` when you only need specific columns
- **Flag if**: DB query inside a for loop (N+1 pattern)

### RLS (Row Level Security)
- **EVERY** table exposed to PostgREST MUST have RLS enabled
- Policies: users can only access their own company's data
- Service role key: **NEVER** in client-side code
- **Flag if**: new table created without RLS policies
- **Flag if**: service_role key appears in any `components.html()` or frontend code

### Migrations
- Number sequentially: `001_`, `002_`, etc.
- Always `IF NOT EXISTS` / `IF EXISTS` for idempotency
- **NEVER** drop columns or tables in production migrations — add, don't remove
- Include rollback comments (what to undo if needed)
- **Flag if**: migration drops a column or table without explicit user request

### Connection Management
- Use `@st.cache_resource` for Supabase client (connection pooling)
- Set `auto_refresh_token=False` on admin/service role clients
- Handle JWT expiry gracefully — clear cache, re-authenticate
- **Flag if**: new Supabase client created on every request

---

## 4. Security Checklist

### Secrets
- [ ] All keys in environment variables (`os.environ` / `st.secrets`)
- [ ] `.env` in `.gitignore` and NOT tracked
- [ ] No Supabase URL or keys in `components.html()` JS
- [ ] No hardcoded passwords or tokens anywhere

### Input Validation
- [ ] All user inputs sanitized before DB queries
- [ ] File uploads validated: MIME type, size limit, extension whitelist
- [ ] No raw SQL — always use Supabase query builder
- [ ] HTML in `st.markdown(unsafe_allow_html=True)` doesn't include user-provided content unescaped

### Authentication
- [ ] Session tokens not exposed in URL query params (if possible)
- [ ] Logout clears all session state + page reload
- [ ] Failed login attempts logged
- [ ] Password reset flow uses Supabase Auth (not custom)

- **Flag if**: any of these checks fail in new or modified code

---

## 5. Frontend / HTML/CSS/JS Patterns

### Streamlit HTML Injection
```python
# BAD — user data injected into HTML without escaping
st.markdown(f"<div>{user_name}</div>", unsafe_allow_html=True)

# GOOD — escape user data
from html import escape
st.markdown(f"<div>{escape(user_name)}</div>", unsafe_allow_html=True)
```
- **ALWAYS** escape user-provided strings in `unsafe_allow_html=True` contexts
- **Flag if**: f-string with user data in `st.markdown(unsafe_allow_html=True)`

### JavaScript in components.html()
- Use `window.parent.document` to access Streamlit's DOM
- Wrap in IIFE: `(function(){ ... })()`
- Use `setTimeout` for DOM readiness, not `DOMContentLoaded` (iframe loads after parent)
- Clean up: remove old style/script tags before re-injecting (`getElementById` + `remove()`)
- **Flag if**: JS doesn't clean up previous injections (style/element accumulation)

### CSS
- Use `!important` sparingly — only when overriding Streamlit's Emotion styles
- Prefer `[data-testid="stXxx"]` selectors over class names (class names change between versions)
- **Flag if**: CSS targets `st-emotion-cache-*` classes (fragile, version-dependent)

---

## 6. Multi-Tenant Architecture

### Data Isolation
- **EVERY** query must include `company_id` filter
- **NEVER** return data across companies
- RLS policies enforce this at DB level as a safety net
- Application code must also filter — defense in depth
- **Flag if**: query missing `company_id` filter

### Session Isolation
- Company switch must clear all cached data
- `session_state` keys shared across companies must be namespaced or cleared
- **Flag if**: cached data persists after company switch

---

## 7. Code Organization

### File Structure
```
app/
  main.py          — routing, sidebar, topbar
  auth.py          — login, session, roles
  db_helper.py     — DB connection, common queries
  styles.py        — global CSS injection
  pages/
    _dashboard.py  — one file per page
    _employees.py
    ...
backend/
  payroll.py       — pure computation (no Streamlit imports!)
  dtr.py           — attendance computation
  deadlines.py     — remittance deadline logic
reports/
  *.py             — PDF generators
db/
  connection.py    — Supabase client factory
  migrations/      — numbered SQL files
```

### Separation of Concerns
- **Backend** (`backend/`) — pure Python computation, no `import streamlit`
- **Pages** (`app/pages/`) — UI rendering, uses backend for logic
- **Reports** (`reports/`) — PDF generation, no UI code
- **Flag if**: `import streamlit` appears in `backend/` or `reports/`
- **Flag if**: business logic (computation) mixed into page rendering code

### Function Size
- Functions over 100 lines should be split
- Deeply nested functions (3+ levels) should be flattened
- **Flag if**: function exceeds 150 lines
