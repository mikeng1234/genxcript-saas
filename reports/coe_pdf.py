"""
Certificate of Employment (COE) PDF Generator.

Generates a formal COE on A4 paper with company letterhead,
standard employment certification body, and a signature block.
"""

import io
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reports.pdf_fonts import FONT, FONT_BOLD


# ── Brand colours (matches payslip palette) ───────────────────────────────────
_BRAND_DARK  = colors.HexColor("#1e3a5f")   # dark navy — header / title
_BRAND_MID   = colors.HexColor("#2563eb")   # blue accent — rule line
_TEXT_MAIN   = colors.HexColor("#1f2937")
_TEXT_MUTED  = colors.HexColor("#6b7280")


def _ordinal(n: int) -> str:
    """Return English ordinal string: 1st, 2nd, 3rd …"""
    if 11 <= n % 100 <= 13:
        return f"{n}th"
    return f"{n}{['th','st','nd','rd'][min(n % 10, 4) if n % 10 < 4 else 0]}"


def generate_coe_pdf(company: dict, employee: dict, include_salary: bool = True) -> bytes:
    """
    Generate a Certificate of Employment PDF.

    Args:
        company:         companies row dict (name, address, tin, etc.)
        employee:        employees row dict (first_name, last_name, position,
                         employment_type, date_hired, basic_salary, salary_type)
        include_salary:  If True, the second paragraph states the basic salary.
                         If False, a generic paragraph is used instead.

    Returns:
        PDF as bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=25 * mm,
        rightMargin=25 * mm,
    )

    styles = getSampleStyleSheet()

    # ── Custom paragraph styles ────────────────────────────────────────────────
    company_name_style = ParagraphStyle(
        "CompanyName",
        fontSize=18,
        leading=22,
        textColor=_BRAND_DARK,
        fontName=FONT_BOLD,
        alignment=TA_CENTER,
        spaceAfter=2,
    )
    company_sub_style = ParagraphStyle(
        "CompanySub",
        fontSize=9,
        leading=13,
        textColor=_TEXT_MUTED,
        fontName=FONT,
        alignment=TA_CENTER,
        spaceAfter=0,
    )
    doc_title_style = ParagraphStyle(
        "DocTitle",
        fontSize=13,
        leading=18,
        textColor=_BRAND_DARK,
        fontName=FONT_BOLD,
        alignment=TA_CENTER,
        spaceBefore=14,
        spaceAfter=4,
    )
    date_style = ParagraphStyle(
        "DateLine",
        fontSize=9,
        textColor=_TEXT_MUTED,
        fontName=FONT,
        alignment=TA_CENTER,
        spaceAfter=18,
    )
    body_style = ParagraphStyle(
        "Body",
        fontSize=11,
        leading=18,
        textColor=_TEXT_MAIN,
        fontName=FONT,
        alignment=TA_LEFT,
        spaceBefore=0,
        spaceAfter=12,
        firstLineIndent=0,
    )
    label_style = ParagraphStyle(
        "Label",
        fontSize=9,
        textColor=_TEXT_MUTED,
        fontName=FONT_BOLD,
        alignment=TA_LEFT,
        spaceAfter=2,
    )
    sig_name_style = ParagraphStyle(
        "SigName",
        fontSize=11,
        fontName=FONT_BOLD,
        textColor=_TEXT_MAIN,
        alignment=TA_LEFT,
        spaceAfter=2,
    )
    sig_title_style = ParagraphStyle(
        "SigTitle",
        fontSize=9,
        fontName=FONT,
        textColor=_TEXT_MUTED,
        alignment=TA_LEFT,
    )

    # ── Data preparation ───────────────────────────────────────────────────────
    co_name    = company.get("name", "Company Name")
    co_address = company.get("address", "")
    co_tin     = company.get("tin", "")
    co_contact = company.get("contact_no", "") or company.get("email", "")

    emp_first  = employee.get("first_name", "")
    emp_last   = employee.get("last_name",  "")
    emp_full   = f"{emp_first} {emp_last}".strip()
    position   = employee.get("position", "Employee") or "Employee"
    emp_type   = (employee.get("employment_type") or "regular").capitalize()
    date_hired_raw = employee.get("date_hired", "")
    try:
        hired_dt   = date.fromisoformat(date_hired_raw)
        hired_str  = hired_dt.strftime(f"%B {_ordinal(hired_dt.day)}, %Y")
    except Exception:
        hired_str  = date_hired_raw or "—"

    salary_centavos = employee.get("basic_salary", 0) or 0
    salary_pesos    = salary_centavos / 100
    salary_type     = (employee.get("salary_type") or "monthly").capitalize()
    salary_str      = f"PHP {salary_pesos:,.2f} {salary_type}"

    today       = date.today()
    issued_str  = today.strftime(f"%B {_ordinal(today.day)}, %Y")

    # ── Company sub-line (address + TIN) ──────────────────────────────────────
    sub_parts = [p for p in [co_address, f"TIN: {co_tin}" if co_tin else "", co_contact] if p]
    co_sub    = "  |  ".join(sub_parts) if sub_parts else ""

    # ── Flowables ─────────────────────────────────────────────────────────────
    story = []

    # Company header
    story.append(Paragraph(co_name, company_name_style))
    if co_sub:
        story.append(Paragraph(co_sub, company_sub_style))

    # Accent rule
    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width="100%", thickness=2, color=_BRAND_MID, spaceAfter=0))

    # Document title
    story.append(Paragraph("CERTIFICATE OF EMPLOYMENT", doc_title_style))
    story.append(Paragraph(f"Date Issued: {issued_str}", date_style))

    # Body paragraph — TO WHOM IT MAY CONCERN
    story.append(Paragraph("TO WHOM IT MAY CONCERN:", body_style))

    story.append(Paragraph(
        f"This is to certify that <b>{emp_full}</b> is currently employed by "
        f"<b>{co_name}</b> as <b>{position}</b> on a <b>{emp_type}</b> basis, "
        f"effective <b>{hired_str}</b>.",
        body_style,
    ))

    if include_salary:
        second_para = (
            f"At the time of this certification, <b>{emp_full}</b> holds a basic salary "
            f"of <b>{salary_str}</b> and continues to be an active member of our "
            f"organization, performing duties and responsibilities assigned to the "
            f"said position with dedication and professionalism."
        )
    else:
        second_para = (
            f"<b>{emp_full}</b> continues to be an active member of our organization, "
            f"performing duties and responsibilities assigned to the said position "
            f"with dedication and professionalism."
        )
    story.append(Paragraph(second_para, body_style))

    story.append(Paragraph(
        "This certification is issued upon the request of the above-named employee "
        "for whatever legal purpose it may serve.",
        body_style,
    ))

    # Spacer before signature
    story.append(Spacer(1, 20 * mm))

    # Signature block (left-aligned, two-column: sig line | blank)
    sig_line = "_" * 38
    sig_data = [
        [Paragraph(sig_line, body_style), ""],
        [Paragraph("Authorized Signatory", sig_title_style), ""],
        [Paragraph(co_name, sig_title_style), ""],
    ]
    sig_table = Table(sig_data, colWidths=["50%", "50%"])
    sig_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",   (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 1),
    ]))
    story.append(sig_table)

    # Bottom rule + doc control footer
    story.append(Spacer(1, 18 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=_TEXT_MUTED))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        f"Document generated on {issued_str} via GenXcript Payroll System. "
        "This document is system-generated and valid without a wet signature "
        "unless otherwise required by the requesting party.",
        ParagraphStyle(
            "Footer",
            fontSize=7.5,
            textColor=_TEXT_MUTED,
            fontName=FONT,
            alignment=TA_CENTER,
        ),
    ))

    doc.build(story)
    return buffer.getvalue()
