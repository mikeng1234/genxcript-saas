"""
Government Remittance Report PDF Generators.

Generates PDF reports for Philippine government agency submissions:
- SSS R3 / R5 — Monthly Collection List
- PhilHealth RF-1 — Monthly Remittance Report
- Pag-IBIG MCRF — Monthly Collection Remittance Form
- BIR 1601-C — Monthly Withholding Tax Remittance

All monetary values are in centavos internally, displayed as pesos in PDFs.
"""

import io
from datetime import date
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph, PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reports.pdf_fonts import FONT, FONT_BOLD, peso as _fmt


# ============================================================
# Shared Helpers
# ============================================================

def _fmt_plain(centavos: int) -> str:
    """Format centavos as plain number (no peso sign) for table cells."""
    return f"{centavos / 100:,.2f}"


def _get_styles():
    """Return common paragraph styles used across all reports."""
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Heading1"],
        fontName=FONT_BOLD, fontSize=14, alignment=TA_CENTER, spaceAfter=2 * mm,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle", parent=styles["Normal"],
        fontName=FONT, fontSize=10, alignment=TA_CENTER, textColor=colors.grey,
        spaceAfter=1 * mm,
    )
    company_style = ParagraphStyle(
        "CompanyName", parent=styles["Heading2"],
        fontName=FONT_BOLD, fontSize=12, alignment=TA_CENTER, spaceAfter=1 * mm,
    )
    section_style = ParagraphStyle(
        "SectionHeader", parent=styles["Heading3"],
        fontName=FONT_BOLD, fontSize=10, spaceAfter=2 * mm, spaceBefore=4 * mm,
        textColor=colors.HexColor("#333333"),
    )
    note_style = ParagraphStyle(
        "Note", parent=styles["Normal"],
        fontName=FONT, fontSize=8, textColor=colors.grey, alignment=TA_CENTER,
        spaceBefore=6 * mm,
    )
    small_style = ParagraphStyle(
        "Small", parent=styles["Normal"],
        fontName=FONT, fontSize=8, textColor=colors.HexColor("#555555"),
    )

    return {
        "title": title_style,
        "subtitle": subtitle_style,
        "company": company_style,
        "section": section_style,
        "note": note_style,
        "small": small_style,
        "normal": styles["Normal"],
    }


def _build_header(elements, styles, company, report_title, report_subtitle, period_label):
    """Add the standard report header block."""
    elements.append(Paragraph(company.get("name", "Company"), styles["company"]))
    elements.append(Paragraph(company.get("address", "") or "", styles["subtitle"]))
    elements.append(Spacer(1, 3 * mm))
    elements.append(Paragraph(report_title, styles["title"]))
    elements.append(Paragraph(report_subtitle, styles["subtitle"]))
    elements.append(Paragraph(f"Applicable Period: {period_label}", styles["subtitle"]))
    elements.append(Spacer(1, 4 * mm))


def _build_company_info_row(elements, styles, company, agency_field, agency_label):
    """Add the employer registration number row."""
    reg_no = company.get(agency_field, "") or "—"
    info_data = [
        ["Employer Name:", company.get("name", ""), f"{agency_label}:", reg_no],
        ["Address:", company.get("address", "") or "—", "", ""],
    ]
    info_table = Table(info_data, colWidths=[80, 200, 100, 120])
    info_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 0), (0, -1), FONT_BOLD),
        ("FONTNAME", (2, 0), (2, -1), FONT_BOLD),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 3 * mm))


# ============================================================
# Standard Table Styling
# ============================================================

def _standard_table_style():
    """Return a consistent table style for all report data tables."""
    return TableStyle([
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),

        # Data rows
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),

        # Grid
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#2563eb")),

        # Alternating row colors
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f8f9fa")]),

        # Right-align amount columns (will be overridden per report)
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ])


def _totals_row_style(row_index, col_count):
    """Return style commands for the totals row."""
    return [
        ("BACKGROUND", (0, row_index), (-1, row_index), colors.HexColor("#e8f0fe")),
        ("FONTNAME", (0, row_index), (-1, row_index), FONT_BOLD),
        ("LINEABOVE", (0, row_index), (-1, row_index), 1.5, colors.HexColor("#2563eb")),
    ]


# ============================================================
# SSS R3 — Monthly Collection List
# ============================================================

def generate_sss_r3(company, employees, entries, period_label):
    """
    Generate SSS R3 Monthly Collection List as PDF.

    Shows each employee's SSS number, monthly salary credit,
    employee share, employer share, EC contribution, and total.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        topMargin=12 * mm, bottomMargin=12 * mm,
        leftMargin=12 * mm, rightMargin=12 * mm,
    )

    styles = _get_styles()
    elements = []

    _build_header(
        elements, styles, company,
        "SSS MONTHLY COLLECTION LIST",
        "Form R3 / R5",
        period_label,
    )
    _build_company_info_row(elements, styles, company, "sss_employer_no", "SSS Employer No.")

    # Table header
    header = ["#", "Employee Name", "SSS No.", "Monthly Salary\nCredit (₱)",
              "EE Share (₱)", "ER Share (₱)", "Total (₱)"]

    data = [header]
    total_ee = 0
    total_er = 0

    for i, emp in enumerate(employees, 1):
        entry = entries.get(emp["id"])
        if not entry:
            continue

        ee = entry["sss_employee"]
        er = entry["sss_employer"]
        total = ee + er
        total_ee += ee
        total_er += er

        # Monthly Salary Credit = gross pay (clamped in computation)
        msc = entry["gross_pay"]

        data.append([
            str(i),
            f"{emp['last_name']}, {emp['first_name']}",
            emp.get("sss_no", "") or "—",
            _fmt_plain(msc),
            _fmt_plain(ee),
            _fmt_plain(er),
            _fmt_plain(total),
        ])

    # Totals row
    grand_total = total_ee + total_er
    data.append(["", "TOTAL", "", "", _fmt_plain(total_ee), _fmt_plain(total_er), _fmt_plain(grand_total)])

    col_widths = [25, 180, 80, 90, 80, 80, 80]
    table = Table(data, colWidths=col_widths, repeatRows=1)

    style = _standard_table_style()
    # Right-align amount columns
    style.add("ALIGN", (3, 1), (-1, -1), "RIGHT")
    style.add("ALIGN", (0, 1), (0, -1), "CENTER")

    # Totals row styling
    totals_idx = len(data) - 1
    for cmd in _totals_row_style(totals_idx, len(header)):
        style.add(*cmd)

    table.setStyle(style)
    elements.append(table)

    # Summary box
    elements.append(Spacer(1, 6 * mm))
    summary_data = [
        ["Total Employee Share:", _fmt(total_ee)],
        ["Total Employer Share:", _fmt(total_er)],
        ["Grand Total Remittance:", _fmt(grand_total)],
        ["Number of Employees:", str(len(data) - 2)],  # minus header and totals
    ]
    summary_table = Table(summary_data, colWidths=[150, 100])
    summary_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), FONT_BOLD),
        ("FONTNAME", (1, 0), (1, -1), FONT),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("FONTNAME", (0, -2), (-1, -2), FONT_BOLD),
        ("LINEABOVE", (0, -2), (-1, -2), 1, colors.black),
        ("LINEBELOW", (0, -2), (-1, -2), 1, colors.black),
    ]))
    elements.append(summary_table)

    # Footer
    elements.append(Paragraph(
        "This is a system-generated report. Verify against official SSS records before submission.",
        styles["note"],
    ))

    doc.build(elements)
    return buffer.getvalue()


# ============================================================
# PhilHealth RF-1 — Monthly Remittance Report
# ============================================================

def generate_philhealth_rf1(company, employees, entries, period_label):
    """
    Generate PhilHealth RF-1 Monthly Remittance Report as PDF.

    Shows each employee's PhilHealth number, monthly basic salary,
    premium amount, and EE/ER shares.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        topMargin=12 * mm, bottomMargin=12 * mm,
        leftMargin=12 * mm, rightMargin=12 * mm,
    )

    styles = _get_styles()
    elements = []

    _build_header(
        elements, styles, company,
        "PHILHEALTH MONTHLY REMITTANCE REPORT",
        "Form RF-1",
        period_label,
    )
    _build_company_info_row(elements, styles, company, "philhealth_employer_no", "PhilHealth ER No.")

    header = ["#", "Employee Name", "PhilHealth No.", "Monthly Basic\nSalary (₱)",
              "EE Share (₱)", "ER Share (₱)", "Total Premium (₱)"]

    data = [header]
    total_ee = 0
    total_er = 0

    for i, emp in enumerate(employees, 1):
        entry = entries.get(emp["id"])
        if not entry:
            continue

        ee = entry["philhealth_employee"]
        er = entry["philhealth_employer"]
        total = ee + er
        total_ee += ee
        total_er += er

        data.append([
            str(i),
            f"{emp['last_name']}, {emp['first_name']}",
            emp.get("philhealth_no", "") or "—",
            _fmt_plain(entry["basic_pay"]),
            _fmt_plain(ee),
            _fmt_plain(er),
            _fmt_plain(total),
        ])

    grand_total = total_ee + total_er
    data.append(["", "TOTAL", "", "", _fmt_plain(total_ee), _fmt_plain(total_er), _fmt_plain(grand_total)])

    col_widths = [25, 180, 90, 90, 80, 80, 90]
    table = Table(data, colWidths=col_widths, repeatRows=1)

    style = _standard_table_style()
    style.add("ALIGN", (3, 1), (-1, -1), "RIGHT")
    style.add("ALIGN", (0, 1), (0, -1), "CENTER")

    totals_idx = len(data) - 1
    for cmd in _totals_row_style(totals_idx, len(header)):
        style.add(*cmd)

    table.setStyle(style)
    elements.append(table)

    # Summary
    elements.append(Spacer(1, 6 * mm))
    summary_data = [
        ["Total Employee Share:", _fmt(total_ee)],
        ["Total Employer Share:", _fmt(total_er)],
        ["Grand Total Premium:", _fmt(grand_total)],
        ["Number of Employees:", str(len(data) - 2)],
    ]
    summary_table = Table(summary_data, colWidths=[150, 100])
    summary_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), FONT_BOLD),
        ("FONTNAME", (1, 0), (1, -1), FONT),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("FONTNAME", (0, -2), (-1, -2), FONT_BOLD),
        ("LINEABOVE", (0, -2), (-1, -2), 1, colors.black),
        ("LINEBELOW", (0, -2), (-1, -2), 1, colors.black),
    ]))
    elements.append(summary_table)

    elements.append(Paragraph(
        "This is a system-generated report. Verify against official PhilHealth records before submission.",
        styles["note"],
    ))

    doc.build(elements)
    return buffer.getvalue()


# ============================================================
# Pag-IBIG MCRF — Monthly Collection Remittance Form
# ============================================================

def generate_pagibig_mcrf(company, employees, entries, period_label):
    """
    Generate Pag-IBIG MCRF Monthly Collection Remittance Form as PDF.

    Shows each employee's Pag-IBIG MID number, monthly compensation,
    employee and employer contributions.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        topMargin=12 * mm, bottomMargin=12 * mm,
        leftMargin=12 * mm, rightMargin=12 * mm,
    )

    styles = _get_styles()
    elements = []

    _build_header(
        elements, styles, company,
        "PAG-IBIG MONTHLY COLLECTION REMITTANCE FORM",
        "MCRF",
        period_label,
    )
    _build_company_info_row(elements, styles, company, "pagibig_employer_no", "Pag-IBIG ER No.")

    header = ["#", "Employee Name", "Pag-IBIG MID No.", "Monthly\nCompensation (₱)",
              "EE Share (₱)", "ER Share (₱)", "Total (₱)"]

    data = [header]
    total_ee = 0
    total_er = 0

    for i, emp in enumerate(employees, 1):
        entry = entries.get(emp["id"])
        if not entry:
            continue

        ee = entry["pagibig_employee"]
        er = entry["pagibig_employer"]
        total = ee + er
        total_ee += ee
        total_er += er

        data.append([
            str(i),
            f"{emp['last_name']}, {emp['first_name']}",
            emp.get("pagibig_no", "") or "—",
            _fmt_plain(entry["gross_pay"]),
            _fmt_plain(ee),
            _fmt_plain(er),
            _fmt_plain(total),
        ])

    grand_total = total_ee + total_er
    data.append(["", "TOTAL", "", "", _fmt_plain(total_ee), _fmt_plain(total_er), _fmt_plain(grand_total)])

    col_widths = [25, 180, 90, 100, 80, 80, 80]
    table = Table(data, colWidths=col_widths, repeatRows=1)

    style = _standard_table_style()
    style.add("ALIGN", (3, 1), (-1, -1), "RIGHT")
    style.add("ALIGN", (0, 1), (0, -1), "CENTER")

    totals_idx = len(data) - 1
    for cmd in _totals_row_style(totals_idx, len(header)):
        style.add(*cmd)

    table.setStyle(style)
    elements.append(table)

    # Summary
    elements.append(Spacer(1, 6 * mm))
    summary_data = [
        ["Total Employee Share:", _fmt(total_ee)],
        ["Total Employer Share:", _fmt(total_er)],
        ["Grand Total Contribution:", _fmt(grand_total)],
        ["Number of Employees:", str(len(data) - 2)],
    ]
    summary_table = Table(summary_data, colWidths=[160, 100])
    summary_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), FONT_BOLD),
        ("FONTNAME", (1, 0), (1, -1), FONT),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("FONTNAME", (0, -2), (-1, -2), FONT_BOLD),
        ("LINEABOVE", (0, -2), (-1, -2), 1, colors.black),
        ("LINEBELOW", (0, -2), (-1, -2), 1, colors.black),
    ]))
    elements.append(summary_table)

    elements.append(Paragraph(
        "This is a system-generated report. Verify against official Pag-IBIG records before submission.",
        styles["note"],
    ))

    doc.build(elements)
    return buffer.getvalue()


# ============================================================
# BIR 1601-C — Monthly Withholding Tax Remittance
# ============================================================

def generate_bir_1601c(company, employees, entries, period_label):
    """
    Generate BIR 1601-C Monthly Withholding Tax Remittance report as PDF.

    Shows each employee's BIR TIN, gross compensation, non-taxable
    allowances, taxable income, and tax withheld.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        topMargin=12 * mm, bottomMargin=12 * mm,
        leftMargin=12 * mm, rightMargin=12 * mm,
    )

    styles = _get_styles()
    elements = []

    _build_header(
        elements, styles, company,
        "BIR MONTHLY WITHHOLDING TAX REMITTANCE",
        "Form 1601-C — Monthly Remittance Return of Income Taxes Withheld on Compensation",
        period_label,
    )
    _build_company_info_row(elements, styles, company, "bir_tin", "Employer TIN")

    header = ["#", "Employee Name", "BIR TIN", "Gross\nCompensation (₱)",
              "Non-Taxable (₱)", "Mandatory\nDeductions (₱)",
              "Taxable\nIncome (₱)", "Tax Withheld (₱)"]

    data = [header]
    total_gross = 0
    total_nontax = 0
    total_mandatory = 0
    total_taxable = 0
    total_wht = 0

    for i, emp in enumerate(employees, 1):
        entry = entries.get(emp["id"])
        if not entry:
            continue

        gross = entry["gross_pay"]
        nontax = entry["allowances_nontaxable"]
        # Mandatory deductions = SSS_ee + PhilHealth_ee + PagIBIG_ee
        mandatory = entry["sss_employee"] + entry["philhealth_employee"] + entry["pagibig_employee"]
        # Taxable income = gross - nontaxable - mandatory deductions
        taxable = gross - nontax - mandatory
        wht = entry["withholding_tax"]

        total_gross += gross
        total_nontax += nontax
        total_mandatory += mandatory
        total_taxable += taxable
        total_wht += wht

        data.append([
            str(i),
            f"{emp['last_name']}, {emp['first_name']}",
            emp.get("bir_tin", "") or "—",
            _fmt_plain(gross),
            _fmt_plain(nontax),
            _fmt_plain(mandatory),
            _fmt_plain(taxable),
            _fmt_plain(wht),
        ])

    data.append([
        "", "TOTAL", "",
        _fmt_plain(total_gross),
        _fmt_plain(total_nontax),
        _fmt_plain(total_mandatory),
        _fmt_plain(total_taxable),
        _fmt_plain(total_wht),
    ])

    col_widths = [22, 150, 70, 85, 75, 80, 80, 80]
    table = Table(data, colWidths=col_widths, repeatRows=1)

    style = _standard_table_style()
    style.add("ALIGN", (3, 1), (-1, -1), "RIGHT")
    style.add("ALIGN", (0, 1), (0, -1), "CENTER")

    totals_idx = len(data) - 1
    for cmd in _totals_row_style(totals_idx, len(header)):
        style.add(*cmd)

    table.setStyle(style)
    elements.append(table)

    # Summary
    elements.append(Spacer(1, 6 * mm))
    summary_data = [
        ["Total Gross Compensation:", _fmt(total_gross)],
        ["Less: Non-Taxable Allowances:", _fmt(total_nontax)],
        ["Less: Mandatory Contributions (EE):", _fmt(total_mandatory)],
        ["Total Taxable Compensation:", _fmt(total_taxable)],
        ["Total Tax Withheld:", _fmt(total_wht)],
        ["Number of Employees:", str(len(data) - 2)],
    ]
    summary_table = Table(summary_data, colWidths=[190, 100])
    summary_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), FONT_BOLD),
        ("FONTNAME", (1, 0), (1, -1), FONT),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("FONTNAME", (0, -3), (-1, -3), FONT_BOLD),
        ("FONTNAME", (0, -2), (-1, -2), FONT_BOLD),
        ("LINEABOVE", (0, -3), (-1, -3), 1, colors.black),
        ("LINEBELOW", (0, -2), (-1, -2), 1, colors.black),
    ]))
    elements.append(summary_table)

    elements.append(Paragraph(
        "This is a system-generated report. Verify against official BIR records before submission.",
        styles["note"],
    ))

    doc.build(elements)
    return buffer.getvalue()
