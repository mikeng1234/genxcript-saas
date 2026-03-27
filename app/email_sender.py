"""
Email utility for GeNXcript Payroll SaaS.

Sends transactional emails via SMTP (e.g. Gmail, Outlook, any SMTP relay).

Required .env variables:
    SMTP_HOST     = smtp.gmail.com
    SMTP_PORT     = 587
    SMTP_USER     = youremail@gmail.com
    SMTP_PASSWORD = your_gmail_app_password   ← NOT your regular Gmail password.
                                                 Go to Google Account → Security →
                                                 2-Step Verification → App Passwords
    APP_URL       = http://localhost:8501     ← URL employees open to log in

If SMTP is not configured, functions return (False, "SMTP not configured") and
the caller can fall back to showing the temp password to the admin.
"""

import os
import smtplib
import secrets
import string
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


# ── Helpers ──────────────────────────────────────────────────────────────────

def generate_temp_password(length: int = 12) -> str:
    """
    Generate a cryptographically random temporary password.
    Guarantees at least one uppercase, one lowercase, one digit, one symbol.
    """
    upper   = string.ascii_uppercase
    lower   = string.ascii_lowercase
    digits  = string.digits
    symbols = "!@#$%"
    all_chars = upper + lower + digits + symbols

    while True:
        pwd = "".join(secrets.choice(all_chars) for _ in range(length))
        if (
            any(c in upper   for c in pwd)
            and any(c in lower   for c in pwd)
            and any(c in digits  for c in pwd)
            and any(c in symbols for c in pwd)
        ):
            return pwd


def _smtp_config() -> dict | None:
    """Return SMTP config dict if all required vars are set, else None."""
    host = os.environ.get("SMTP_HOST", "")
    port = os.environ.get("SMTP_PORT", "587")
    user = os.environ.get("SMTP_USER", "")
    pwd  = os.environ.get("SMTP_PASSWORD", "")
    if host and user and pwd:
        return {"host": host, "port": int(port), "user": user, "password": pwd}
    return None


# ── Public API ────────────────────────────────────────────────────────────────

def send_temp_password_email(
    to_email: str,
    temp_password: str,
    company_name: str = "your company",
    portal_url: str | None = None,
) -> tuple[bool, str]:
    """
    Email an employee their system-generated temporary password.

    Returns (True, "") on success, (False, error_message) on failure.
    """
    cfg = _smtp_config()
    if not cfg:
        return False, "SMTP not configured"

    if portal_url is None:
        portal_url = os.environ.get("APP_URL", "http://localhost:8501")

    subject = f"Your {company_name} Payroll Portal Access"

    plain = (
        f"Hello,\n\n"
        f"Your employer has set up your Payroll Portal access.\n\n"
        f"  Portal URL : {portal_url}\n"
        f"  Email      : {to_email}\n"
        f"  Password   : {temp_password}\n\n"
        f"Log in and click 'Forgot Password' to set your own password.\n\n"
        f"— GeNXcript Payroll"
    )

    html = f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0">
  <tr><td align="center" style="padding:40px 20px;">
    <table width="560" cellpadding="0" cellspacing="0"
           style="background:#fff;border-radius:12px;overflow:hidden;
                  box-shadow:0 4px 16px rgba(0,0,0,.08);">

      <!-- Header -->
      <tr>
        <td style="background:linear-gradient(135deg,#1e3a5f,#2563eb);
                   padding:32px 40px;text-align:center;">
          <h1 style="margin:0;color:#fff;font-size:22px;font-weight:700;
                     letter-spacing:.5px;">GeNXcript Payroll</h1>
          <p  style="margin:4px 0 0;color:#93c5fd;font-size:13px;">
            Portal Access Credentials</p>
        </td>
      </tr>

      <!-- Body -->
      <tr>
        <td style="padding:36px 40px;">
          <p style="margin:0 0 16px;color:#334155;font-size:15px;line-height:1.6;">
            Hello,<br><br>
            Your employer (<strong>{company_name}</strong>) has set up your payroll
            portal access. Use the credentials below to sign in.
          </p>

          <!-- Credentials box -->
          <table width="100%" cellpadding="0" cellspacing="0"
                 style="background:#f8fafc;border:1px solid #e2e8f0;
                        border-radius:8px;margin-bottom:24px;">
            <tr>
              <td style="padding:20px 24px;">
                <table cellpadding="4" cellspacing="0">
                  <tr>
                    <td style="color:#64748b;font-size:13px;width:120px;">Portal&nbsp;URL</td>
                    <td style="color:#1e293b;font-size:13px;">
                      <a href="{portal_url}" style="color:#2563eb;">{portal_url}</a>
                    </td>
                  </tr>
                  <tr>
                    <td style="color:#64748b;font-size:13px;">Email</td>
                    <td style="color:#1e293b;font-size:13px;">{to_email}</td>
                  </tr>
                  <tr>
                    <td style="color:#64748b;font-size:13px;vertical-align:top;
                               padding-top:8px;">Temporary<br>Password</td>
                    <td style="padding-top:8px;">
                      <span style="display:inline-block;background:#1e3a5f;color:#fff;
                                   font-family:monospace;font-size:18px;font-weight:700;
                                   letter-spacing:3px;padding:8px 16px;border-radius:6px;">
                        {temp_password}
                      </span>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>

          <p style="margin:0 0 8px;color:#64748b;font-size:13px;line-height:1.6;">
            After signing in, click <strong>Forgot Password</strong> on the login page
            to replace this temporary password with one of your own.
          </p>
        </td>
      </tr>

      <!-- Footer -->
      <tr>
        <td style="background:#f8fafc;border-top:1px solid #e2e8f0;
                   padding:16px 40px;text-align:center;">
          <p style="margin:0;color:#94a3b8;font-size:11px;">
            GeNXcript Payroll — Philippine SME Payroll System
          </p>
        </td>
      </tr>

    </table>
  </td></tr>
</table>
</body>
</html>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = cfg["user"]
    msg["To"]      = to_email
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html,  "html"))

    try:
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(cfg["user"], cfg["password"])
            server.sendmail(cfg["user"], to_email, msg.as_string())
        return True, ""
    except smtplib.SMTPAuthenticationError:
        return False, "SMTP authentication failed — check SMTP_USER and SMTP_PASSWORD in .env"
    except smtplib.SMTPException as e:
        return False, f"SMTP error: {e}"
    except Exception as e:
        return False, f"Email send error: {e}"
