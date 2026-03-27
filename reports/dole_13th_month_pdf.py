"""
dole_13th_month_pdf.py
======================
Generates the DOLE Compliance Report for 13th Month Pay (PD 851).

Per DOLE Labor Advisory No. 18, Series of 2018 (DOLE LA 18-18):
  Every covered employer must submit this report to the nearest
  Regional Office not later than January 15 of each year.

Required fields (Part VI, DOLE LA 18-18):
  1. Name of establishment
  2. Address
  3. Principal product or business
  4. Total employment
  5. Total number of workers benefitted
  6. Amount granted per employee
  7. Total amount of benefits granted
  8. Name, position and telephone number of the person giving information
"""

import io
from datetime import date
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph, HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reports.pdf_fonts import FONT, FONT_BOLD


# ── Styles ─────────────────────────────────────────────────────────────────────

def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("T", parent=base["Heading1"],
            fontName=FONT_BOLD, fontSize=13, alignment=TA_CENTER, spaceAfter=1*mm),
        "subtitle": ParagraphStyle("S", parent=base["Normal"],
            fontName=FONT, fontSize=9, alignment=TA_CENTER,
            textColor=colors.grey, spaceAfter=1*mm),
        "company": ParagraphStyle("C", parent=base["Heading2"],
            fontName=FONT_BOLD, fontSize=11, alignment=TA_CENTER, spaceAfter=3*mm),
        "section": ParagraphStyle("SE", parent=base["Heading3"],
            fontName=FONT_BOLD, fontSize=10, spaceAfter=2*mm, spaceBefore=4*mm,
            textColor=colors.HexColor("#1a1a2e")),
        "body": ParagraphStyle("B", parent=base["Normal"],
            fontName=FONT, fontSize=9, spaceAfter=1*mm),
        "footer": ParagraphStyle("F", parent=base["Normal"],
            fontName=FONT, fontSize=7.5, textColor=colors.grey,
            alignment=TA_CENTER, spaceBefore=6*mm),
        "cell": ParagraphStyle("CL", parent=base["Normal"],
            fontName=FONT, fontSize=8.5),
        "cell_bold": ParagraphStyle("CB", parent=base["Normal"],
            fontName=FONT_BOLD, fontSize=8.5),
        "cell_right": ParagraphStyle("CR", parent=base["Normal"],
            fontName=FONT, fontSize=8.5, alignment=TA_RIGHT),
        "cell_right_bold": ParagraphStyle("CRB", parent=base["Normal"],
            fontName=FONT_BOLD, fontSize=8.5, alignment=TA_RIGHT),
    }


def _peso(centavos: int) -> str:
    return f"PHP {centavos / 100:,.2f}"


# ── Main Generator ─────────────────────────────────────────────────────────────

def generate_dole_13th_month_pdf(
    company: dict,
    employees: list[dict],           # all employee dicts
    annual_entries: dict,            # {employee_id: aggregated payroll_entries dict}
    year: int,
    principal_business: str = "",
    contact_name: str = "",
    contact_position: str = "",
    contact_tel: str = "",
) -> bytes:
    """
    Generate the DOLE 13th Month Pay Compliance Report PDF.

    Args:
        company:            companies row dict
        employees:          list of employee dicts (filtered to those with 13th month)
        annual_entries:     {employee_id: aggregated payroll row} for the year
        year:               report year (13th month paid in December of this year)
        principal_business: company's principal product or business
        contact_name:       name of person giving information
        contact_position:   position/title of that person
        contact_tel:        telephone number
    Returns:
        PDF bytes
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=18*mm, bottomMargin=18*mm,
    )
    s = _styles()
    story = []

    # ── Header ──────────────────────────────────────────────────────────────────
    story.append(Paragraph("Republic of the Philippines", s["subtitle"]))
    story.append(Paragraph("Department of Labor and Employment", s["subtitle"]))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        "REPORT ON COMPLIANCE WITH P.D. 851", s["title"]
    ))
    story.append(Paragraph(
        "(13th Month Pay Law)", s["subtitle"]
    ))
    story.append(Paragraph(
        f"For the Year {year} — Due January 15, {year + 1}", s["subtitle"]
    ))
    story.append(Paragraph(
        "DOLE Labor Advisory No. 18, Series of 2018", s["subtitle"]
    ))
    story.append(HRFlowable(width="100%", thickness=1.2,
                             color=colors.HexColor("#1a1a2e"), spaceAfter=4*mm))

    # ── Part I — Establishment Information ─────────────────────────────────────
    story.append(Paragraph("I.  ESTABLISHMENT INFORMATION", s["section"]))

    info_data = [
        ["1.  Name of Establishment:", company.get("name", "") or ""],
        ["2.  Address:",               company.get("address", "") or ""],
        ["3.  Principal Product / Business:", principal_business or ""],
    ]
    info_table = Table(info_data, colWidths=[70*mm, None])
    info_table.setStyle(TableStyle([
        ("FONTNAME",   (0, 0), (0, -1), FONT_BOLD),
        ("FONTNAME",   (1, 0), (1, -1), FONT),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 4*mm))

    # ── Part II — Summary Metrics ───────────────────────────────────────────────
    story.append(Paragraph("II.  SUMMARY", s["section"]))

    # Compute benefitted employees and totals
    benefitted = [
        emp for emp in employees
        if (annual_entries.get(emp["id"]) or {}).get("thirteenth_month_accrual", 0) > 0
    ]
    total_employment = len(employees)
    total_benefitted = len(benefitted)
    total_amount = sum(
        (annual_entries.get(emp["id"]) or {}).get("thirteenth_month_accrual", 0)
        for emp in benefitted
    )

    summary_data = [
        ["4.  Total Employment (all active employees):",
         str(total_employment)],
        ["5.  Total Number of Workers Benefitted:",
         str(total_benefitted)],
        ["7.  Total Amount of 13th Month Benefits Granted:",
         _peso(total_amount)],
    ]
    summary_table = Table(summary_data, colWidths=[110*mm, None])
    summary_table.setStyle(TableStyle([
        ("FONTNAME",   (0, 0), (0, -1), FONT_BOLD),
        ("FONTNAME",   (1, 0), (1, -1), FONT),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BACKGROUND", (-1, -1), (-1, -1), colors.HexColor("#f0f4ff")),
        ("FONTNAME",   (-1, -1), (-1, -1), FONT_BOLD),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 4*mm))

    # ── Part III — Per-Employee Detail (Item 6) ─────────────────────────────────
    story.append(Paragraph(
        "III.  AMOUNT GRANTED PER EMPLOYEE  (Item 6 — DOLE LA 18-18)", s["section"]
    ))

    col_w = [12*mm, 55*mm, 22*mm, 35*mm, 35*mm]
    header_row = [
        Paragraph("No.", s["cell_bold"]),
        Paragraph("Employee Name", s["cell_bold"]),
        Paragraph("Employee No.", s["cell_bold"]),
        Paragraph("Monthly Basic", s["cell_right_bold"]),
        Paragraph("13th Month Pay", s["cell_right_bold"]),
    ]
    rows = [header_row]

    sorted_benefitted = sorted(benefitted, key=lambda e: (
        (e.get("last_name") or "").upper(),
        (e.get("first_name") or "").upper(),
    ))

    for i, emp in enumerate(sorted_benefitted, start=1):
        agg = annual_entries.get(emp["id"]) or {}
        thirteenth = agg.get("thirteenth_month_accrual", 0)
        basic = emp.get("basic_salary", 0)
        rows.append([
            Paragraph(str(i), s["cell"]),
            Paragraph(
                f"{emp.get('last_name', '')}, {emp.get('first_name', '')}",
                s["cell"]
            ),
            Paragraph(emp.get("employee_no", ""), s["cell"]),
            Paragraph(_peso(basic), s["cell_right"]),
            Paragraph(_peso(thirteenth), s["cell_right"]),
        ])

    # Totals row
    rows.append([
        Paragraph("", s["cell"]),
        Paragraph("TOTAL", s["cell_bold"]),
        Paragraph("", s["cell"]),
        Paragraph("", s["cell"]),
        Paragraph(_peso(total_amount), s["cell_right_bold"]),
    ])

    detail_table = Table(rows, colWidths=col_w, repeatRows=1)
    detail_table.setStyle(TableStyle([
        # Header
        ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), FONT_BOLD),
        ("FONTSIZE",      (0, 0), (-1, -1), 8.5),
        ("ALIGN",         (0, 0), (-1, -1), "LEFT"),
        # Rows
        ("ROWBACKGROUNDS", (0, 1), (-1, -2),
         [colors.white, colors.HexColor("#f7f9ff")]),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        # Totals row
        ("BACKGROUND",    (0, -1), (-1, -1), colors.HexColor("#e8ecff")),
        ("FONTNAME",      (0, -1), (-1, -1), FONT_BOLD),
        ("LINEABOVE",     (0, -1), (-1, -1), 1, colors.HexColor("#1a1a2e")),
    ]))
    story.append(detail_table)
    story.append(Spacer(1, 6*mm))

    # ── Part IV — Person Giving Information (Item 8) ────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5,
                             color=colors.grey, spaceAfter=4*mm))
    story.append(Paragraph("IV.  PERSON GIVING INFORMATION  (Item 8)", s["section"]))

    contact_data = [
        ["Name:",      contact_name or "___________________________________"],
        ["Position:",  contact_position or "___________________________________"],
        ["Telephone:", contact_tel or "___________________________________"],
        ["Date:",      f"January ___, {year + 1}"],
    ]
    contact_table = Table(contact_data, colWidths=[28*mm, None])
    contact_table.setStyle(TableStyle([
        ("FONTNAME",      (0, 0), (0, -1), FONT_BOLD),
        ("FONTNAME",      (1, 0), (1, -1), FONT),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
    ]))
    story.append(contact_table)

    # ── Footer ──────────────────────────────────────────────────────────────────
    story.append(Paragraph(
        f"Generated by GeNXcript Payroll · {date.today().strftime('%B %d, %Y')} · "
        "Submit to nearest DOLE Regional Office not later than January 15.",
        s["footer"]
    ))

    doc.build(story)
    return buf.getvalue()
