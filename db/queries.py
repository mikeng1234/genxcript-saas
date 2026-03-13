"""
Database query functions for all tables.
Each function takes a Supabase client so callers control auth context.
"""

from supabase import Client


# ============================================================
# EMPLOYEES
# ============================================================

def list_employees(db: Client, company_id: str, active_only: bool = True) -> list[dict]:
    """Fetch all employees for a company, sorted by last name."""
    query = db.table("employees").select("*").eq("company_id", company_id)
    if active_only:
        query = query.eq("is_active", True)
    result = query.order("last_name").execute()
    return result.data


def get_employee(db: Client, employee_id: str) -> dict | None:
    """Fetch a single employee by ID."""
    result = db.table("employees").select("*").eq("id", employee_id).execute()
    return result.data[0] if result.data else None


def create_employee(db: Client, data: dict) -> dict:
    """Insert a new employee. Returns the created record."""
    result = db.table("employees").insert(data).execute()
    return result.data[0]


def update_employee(db: Client, employee_id: str, data: dict) -> dict:
    """Update an employee's fields. Returns the updated record."""
    result = db.table("employees").update(data).eq("id", employee_id).execute()
    return result.data[0]


def deactivate_employee(db: Client, employee_id: str) -> dict:
    """Soft-delete: set is_active = False instead of deleting."""
    return update_employee(db, employee_id, {"is_active": False})


def reactivate_employee(db: Client, employee_id: str) -> dict:
    """Re-enable a previously deactivated employee."""
    return update_employee(db, employee_id, {"is_active": True})


# ============================================================
# COMPANIES
# ============================================================

def list_companies(db: Client) -> list[dict]:
    """Fetch all companies the current user has access to."""
    result = db.table("companies").select("*").order("name").execute()
    return result.data


def get_company(db: Client, company_id: str) -> dict | None:
    """Fetch a single company by ID."""
    result = db.table("companies").select("*").eq("id", company_id).execute()
    return result.data[0] if result.data else None


def create_company(db: Client, data: dict) -> dict:
    """Insert a new company. Returns the created record."""
    result = db.table("companies").insert(data).execute()
    return result.data[0]


def update_company(db: Client, company_id: str, data: dict) -> dict:
    """Update a company's fields. Returns the updated record."""
    result = db.table("companies").update(data).eq("id", company_id).execute()
    return result.data[0]
