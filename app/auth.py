"""
Authentication helpers for GenXcript Payroll SaaS.

Session persistence strategy: st.query_params + server-side cache
- On login/signup, a random session token is generated and stored in:
    1. A server-side dict (cached for the Streamlit process lifetime)
    2. st.query_params["sid"] — survives F5 browser refresh
- On every page load, main.py calls restore_from_query_params() which
  reads the token from the URL and restores the session silently.
- On logout, the token is invalidated and removed from the URL.

No external packages needed — st.query_params is built into Streamlit.
"""

import os
import uuid
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


# ============================================================
# Server-side session store
# Cached for the lifetime of the Streamlit process.
# Users need to log in again only if the server restarts.
# ============================================================

@st.cache_resource
def _session_cache() -> dict:
    return {}


# ============================================================
# Auth Client
# ============================================================

def _get_auth_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def _get_admin_auth_client() -> Client:
    """Service-role client required for admin Auth API (invite, delete user, etc.)."""
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)


# ============================================================
# Session helpers
# ============================================================

def is_logged_in() -> bool:
    return bool(st.session_state.get("user_id") and st.session_state.get("company_id"))


def get_current_user_email() -> str:
    return st.session_state.get("user_email", "")


def get_current_company_id() -> str:
    company_id = st.session_state.get("company_id")
    if not company_id:
        raise RuntimeError("No active session. Please log in.")
    return company_id


def get_current_role() -> str:
    """Returns the current user's role: 'admin', 'viewer', or 'employee'."""
    return st.session_state.get("user_role", "admin")


def is_employee_role() -> bool:
    return get_current_role() == "employee"


def _load_accessible_companies(user_id: str, db) -> list[dict]:
    """
    Return all companies the user can access as:
      [{"id": "...", "name": "...", "role": "admin|viewer|employee"}, ...]
    Sorted by company name.
    """
    access = (
        db.table("user_company_access")
        .select("company_id, role")
        .eq("user_id", user_id)
        .execute()
    )
    if not access.data:
        return []

    role_map     = {row["company_id"]: row["role"] for row in access.data}
    company_ids  = list(role_map.keys())

    companies = (
        db.table("companies")
        .select("id, name")
        .in_("id", company_ids)
        .order("name")
        .execute()
    )
    return [
        {"id": row["id"], "name": row["name"], "role": role_map.get(row["id"], "admin")}
        for row in companies.data
    ]


def _store_session(
    user_id: str,
    user_email: str,
    company_id: str,
    role: str = "admin",
    accessible_companies: list | None = None,
    company_name: str = "",
):
    """
    Persist session to:
    1. st.session_state (current render)
    2. Server-side cache (survives reruns)
    3. st.query_params["sid"] (survives F5 refresh)
    """
    accessible_companies = accessible_companies or []

    st.session_state.user_id               = user_id
    st.session_state.user_email            = user_email
    st.session_state.company_id            = company_id
    st.session_state.user_role             = role
    st.session_state.accessible_companies  = accessible_companies
    st.session_state.company_name          = company_name

    token = str(uuid.uuid4())
    _session_cache()[token] = {
        "user_id":               user_id,
        "user_email":            user_email,
        "company_id":            company_id,
        "user_role":             role,
        "accessible_companies":  accessible_companies,
        "company_name":          company_name,
    }
    st.query_params["sid"] = token


def restore_from_query_params() -> bool:
    """
    Try to restore session from URL query params.
    Called on every page load in main.py.
    Returns True if session was restored, False otherwise.
    """
    if is_logged_in():
        return True

    sid = st.query_params.get("sid")
    if not sid:
        return False

    session = _session_cache().get(sid)
    if not session:
        # Token exists in URL but not in cache (server restarted)
        st.query_params.clear()
        return False

    st.session_state.user_id              = session["user_id"]
    st.session_state.user_email           = session["user_email"]
    st.session_state.company_id           = session["company_id"]
    st.session_state.user_role            = session.get("user_role", "admin")
    st.session_state.accessible_companies = session.get("accessible_companies", [])
    st.session_state.company_name         = session.get("company_name", "")
    return True


def logout():
    """Invalidate session token and clear state."""
    sid = st.query_params.get("sid")
    if sid:
        _session_cache().pop(sid, None)
    st.query_params.clear()
    for key in ["user_id", "user_email", "company_id", "user_role",
                "accessible_companies", "company_name", "company_switcher"]:
        st.session_state.pop(key, None)


def update_active_company(company_id: str, role: str, company_name: str) -> None:
    """
    Switch the active company in session state + server cache.
    Call this then st.rerun() to reload the page under the new company.
    """
    st.session_state.company_id    = company_id
    st.session_state.user_role     = role
    st.session_state.company_name  = company_name
    st.session_state["company_switcher"] = company_id   # keep dropdown in sync

    sid = st.query_params.get("sid")
    if sid and sid in _session_cache():
        cache = _session_cache()[sid]
        cache["company_id"]           = company_id
        cache["user_role"]            = role
        cache["company_name"]         = company_name
        cache["accessible_companies"] = st.session_state.get("accessible_companies", [])


def add_accessible_company(company: dict) -> None:
    """
    Append a newly created company to the session's accessible list
    and update the server cache.
    company: {"id": "...", "name": "...", "role": "admin"}
    """
    accessible = list(st.session_state.get("accessible_companies") or [])
    if not any(c["id"] == company["id"] for c in accessible):
        accessible.append(company)
    accessible.sort(key=lambda c: c["name"].upper())
    st.session_state.accessible_companies = accessible

    sid = st.query_params.get("sid")
    if sid and sid in _session_cache():
        _session_cache()[sid]["accessible_companies"] = accessible


def ensure_accessible_companies_loaded() -> None:
    """
    Lazy-load accessible_companies for sessions created before this feature
    (e.g. server cache was cleared).  No-op if already populated.
    """
    if st.session_state.get("accessible_companies"):
        return
    user_id = st.session_state.get("user_id")
    if not user_id:
        return
    try:
        from app.db_helper import get_db
        accessible = _load_accessible_companies(user_id, get_db())
        st.session_state.accessible_companies = accessible
        current_id = st.session_state.get("company_id")
        st.session_state.company_name = next(
            (c["name"] for c in accessible if c["id"] == current_id), ""
        )
        sid = st.query_params.get("sid")
        if sid and sid in _session_cache():
            _session_cache()[sid]["accessible_companies"] = accessible
            _session_cache()[sid]["company_name"] = st.session_state.company_name
    except Exception:
        pass


# ============================================================
# Login
# ============================================================

def _resolve_login_email(identifier: str) -> tuple[str, str]:
    """
    If identifier looks like an email address, return it unchanged.
    Otherwise treat it as an Employee ID (e.g. "EMP-001"), look up the
    matching email in the employees table via the service-role client
    (which bypasses RLS so the lookup works before auth).

    Returns (email, error_message). error_message is "" on success.
    """
    if "@" in identifier:
        return identifier.strip(), ""

    try:
        from supabase import create_client
        svc = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
        result = (
            svc.table("employees")
            .select("email, is_active")
            .ilike("employee_no", identifier.strip())
            .execute()
        )
        if not result.data:
            return "", (
                f"No employee found with ID **{identifier.strip()}**. "
                "Please double-check your Employee ID or sign in with your email address instead."
            )
        emp = result.data[0]
        if not emp.get("email"):
            return "", (
                f"Employee **{identifier.strip()}** has no portal access set up yet. "
                "Ask your HR admin to send you a portal invite first."
            )
        return emp["email"], ""
    except Exception as e:
        return "", f"Employee lookup error: {e}"


def login(identifier: str, password: str) -> tuple[bool, str]:
    # Resolve Employee ID → email if needed
    email, lookup_err = _resolve_login_email(identifier)
    if lookup_err:
        return False, lookup_err

    try:
        client = _get_auth_client()
        response = client.auth.sign_in_with_password({"email": email, "password": password})
        user = response.user

        if not user:
            return False, "Invalid email or password."

        from app.db_helper import get_db
        db = get_db()
        result = (
            db.table("user_company_access")
            .select("company_id, role")
            .eq("user_id", str(user.id))
            .execute()
        )

        if not result.data:
            # Check if this email belongs to an invited employee (first login)
            emp_result = (
                db.table("employees")
                .select("id, company_id")
                .eq("email", user.email)
                .execute()
            )
            if emp_result.data:
                emp = emp_result.data[0]
                # Create user_company_access row and link user_id to employee
                db.table("user_company_access").insert({
                    "user_id":    str(user.id),
                    "company_id": emp["company_id"],
                    "role":       "employee",
                }).execute()
                db.table("employees").update({"user_id": str(user.id)}).eq("id", emp["id"]).execute()
                _store_session(str(user.id), user.email, emp["company_id"], "employee")
                return True, ""
            return False, "No company linked to this account. Contact support."

        row          = result.data[0]
        accessible   = _load_accessible_companies(str(user.id), db)
        company_name = next((c["name"] for c in accessible if c["id"] == row["company_id"]), "")
        _store_session(
            str(user.id), user.email, row["company_id"],
            row.get("role", "admin"), accessible, company_name,
        )
        return True, ""

    except Exception as e:
        msg = str(e)
        if "invalid login" in msg.lower() or "invalid credentials" in msg.lower():
            return False, "Incorrect email or password."
        return False, f"Login error: {msg}"


# ============================================================
# Signup
# ============================================================

def signup(
    email: str,
    password: str,
    company_name: str,
    region: str,
    pay_frequency: str,
) -> tuple[bool, str]:
    try:
        client = _get_auth_client()
        response = client.auth.sign_up({"email": email, "password": password})
        user = response.user

        if not user:
            return False, "Signup failed. Please try again."

        from app.db_helper import get_db
        db = get_db()

        company_result = db.table("companies").insert({
            "name": company_name.strip(),
            "region": region,
            "pay_frequency": pay_frequency,
        }).execute()

        if not company_result.data:
            return False, "Failed to create company. Please try again."

        company_id = company_result.data[0]["id"]

        db.table("user_company_access").insert({
            "user_id": str(user.id),
            "company_id": company_id,
            "role": "admin",
        }).execute()

        confirmed = (
            getattr(user, "email_confirmed_at", None)
            or getattr(user, "confirmed_at", None)
        )

        if confirmed:
            accessible = [{"id": company_id, "name": company_name.strip(), "role": "admin"}]
            _store_session(str(user.id), user.email, company_id, "admin",
                           accessible, company_name.strip())
            return True, ""
        else:
            return True, "CHECK_EMAIL"

    except Exception as e:
        msg = str(e)
        if "already registered" in msg.lower():
            return False, "An account with this email already exists. Please log in."
        return False, f"Signup error: {msg}"


# ============================================================
# Password Reset (Forgot Password)
# ============================================================

def send_password_reset(email: str) -> tuple[bool, str]:
    """
    Send a password-reset email via the public Supabase client.
    Works for any confirmed or invited user.
    The link redirects to APP_URL (defaults to http://localhost:8501).
    """
    try:
        app_url = os.environ.get("APP_URL", "http://localhost:8501")
        client = _get_auth_client()
        client.auth.reset_password_email(
            email,
            options={"redirect_to": app_url},
        )
        return True, ""
    except Exception as e:
        return False, f"Could not send reset email: {e}"


def get_user_from_access_token(access_token: str) -> dict | None:
    """
    Resolve a Supabase access_token JWT (from the implicit-flow hash) to
    {user_id, email}.

    Uses the public auth client's get_user(jwt) which validates the JWT
    server-side and returns the user record — no admin privileges needed.
    """
    try:
        pub = _get_auth_client()
        response = pub.auth.get_user(access_token)
        u = getattr(response, "user", None)
        if u:
            return {"user_id": u.id, "email": u.email}
    except Exception:
        pass
    return None


def exchange_recovery_code(code: str) -> dict | None:
    """
    Exchange the PKCE auth code from a Supabase password-reset email link.

    Supabase (PKCE flow) appends ?code=<value> to the redirect URL.
    This method exchanges that code for a real session and returns the
    user details so we can show the "Set New Password" form.

    Returns {user_id, email} on success, None on failure.
    """
    try:
        pub = _get_auth_client()
        resp = pub.auth.exchange_code_for_session({"auth_code": code})
        s = getattr(resp, "session", None)
        if s and getattr(s, "user", None):
            return {
                "user_id": s.user.id,
                "email":   s.user.email,
            }
    except Exception:
        pass
    return None


def set_new_password(user_id: str, new_password: str) -> tuple[bool, str]:
    """
    Set a new password for the user after a recovery flow.
    Uses the admin client so no current-password check is needed.
    """
    try:
        adm = _get_admin_auth_client()
        adm.auth.admin.update_user_by_id(user_id, {"password": new_password})
        return True, ""
    except Exception as e:
        return False, f"Failed to set new password: {e}"


# ============================================================
# Employee Invite
# ============================================================

def _find_auth_user_by_email(client, email: str) -> str | None:
    """Look up an existing Supabase auth user ID by email via admin list_users."""
    try:
        all_users = client.auth.admin.list_users()
        user_list = (
            all_users if isinstance(all_users, list)
            else getattr(all_users, "users", [])
        )
        for u in user_list:
            if u.email and u.email.lower() == email.lower():
                return str(u.id)
    except Exception:
        pass
    return None


def invite_employee(employee_email: str) -> tuple[bool, str]:
    """
    Create (or update) a Supabase Auth account for an employee with a
    system-generated temporary password, then email the credentials.

    Flow:
    1. Generate a random temp password.
    2. admin.create_user(email, password, email_confirm=True)
       — creates an immediately usable account (no confirmation link needed).
    3. If the account already exists, update the password via admin.update_user_by_id.
    4. Send a branded HTML email containing the portal URL + temp password.
       — requires SMTP_HOST / SMTP_USER / SMTP_PASSWORD in .env
       — if SMTP is not configured the caller receives the temp password in the
         error message so the admin can share it manually.

    Returns:
        (True,  user_id_str)  — account ready, email sent (or admin notified)
        (False, error_msg)    — unrecoverable error
    """
    from app.email_sender import generate_temp_password, send_temp_password_email
    from app.db_helper import get_db, get_company_id

    client     = _get_admin_auth_client()
    temp_pass  = generate_temp_password()
    user_id: str | None = None

    # ── Step 1: create or update the auth account ─────────────────────────────
    try:
        resp = client.auth.admin.create_user({
            "email":         employee_email,
            "password":      temp_pass,
            "email_confirm": True,   # skip the confirmation step — ready to log in
        })
        user_id = str(resp.user.id) if resp.user else None
    except Exception as e:
        msg = str(e).lower()
        if "already registered" in msg or "already been registered" in msg or "already exists" in msg or "duplicate" in msg:
            # Account exists — find it, then reset its password to our temp_pass
            user_id = _find_auth_user_by_email(client, employee_email)
            if user_id:
                try:
                    client.auth.admin.update_user_by_id(
                        user_id, {"password": temp_pass}
                    )
                except Exception as upd_err:
                    return False, f"Could not reset existing account password: {upd_err}"
            else:
                return False, "Account already exists but could not be located. Contact support."
        else:
            return False, f"Could not create account: {e}"

    if not user_id:
        return False, "Failed to create employee account — please try again."

    # ── Step 2: send the temp-password email ──────────────────────────────────
    # Fetch company name for the email greeting
    company_name = "your company"
    try:
        db = get_db()
        row = db.table("companies").select("name").eq("id", get_company_id()).single().execute()
        if row.data:
            company_name = row.data["name"]
    except Exception:
        pass

    portal_url = os.environ.get("APP_URL", "http://localhost:8501")
    email_ok, email_err = send_temp_password_email(
        to_email=employee_email,
        temp_password=temp_pass,
        company_name=company_name,
        portal_url=portal_url,
    )

    if not email_ok:
        # SMTP not configured or failed — return success but surface temp password
        # so the admin can share it manually.
        return True, f"{user_id}|SMTP_FAILED|{temp_pass}|{email_err}"

    return True, user_id


# ============================================================
# My Account — change own password / display name
# ============================================================

def change_own_password(current_password: str, new_password: str) -> tuple[bool, str]:
    """
    Verify the current password by re-authenticating, then update to the new one.
    Returns (True, "") on success or (False, error_message) on failure.
    """
    email = get_current_user_email()
    if not email:
        return False, "No active session email found."

    # Step 1: verify current password
    try:
        pub = _get_auth_client()
        pub.auth.sign_in_with_password({"email": email, "password": current_password})
    except Exception as e:
        msg = str(e).lower()
        if "invalid" in msg or "credentials" in msg or "password" in msg:
            return False, "Current password is incorrect."
        return False, f"Could not verify current password: {e}"

    # Step 2: update to new password via admin client
    try:
        user_id = st.session_state.get("user_id")
        adm = _get_admin_auth_client()
        adm.auth.admin.update_user_by_id(user_id, {"password": new_password})
        return True, ""
    except Exception as e:
        return False, f"Failed to update password: {e}"


def get_current_display_name() -> str:
    """Return the display_name stored in user_metadata, or empty string."""
    try:
        user_id = st.session_state.get("user_id")
        adm = _get_admin_auth_client()
        user = adm.auth.admin.get_user_by_id(user_id)
        return (user.user.user_metadata or {}).get("display_name", "")
    except Exception:
        return ""


def update_own_display_name(display_name: str) -> tuple[bool, str]:
    """Update the display_name in user_metadata for the current user."""
    try:
        user_id = st.session_state.get("user_id")
        adm = _get_admin_auth_client()
        adm.auth.admin.update_user_by_id(
            user_id,
            {"user_metadata": {"display_name": display_name.strip()}},
        )
        return True, ""
    except Exception as e:
        return False, f"Failed to update display name: {e}"
