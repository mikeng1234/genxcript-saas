"""
PDF Payslip Generator.

Generates a professional payslip PDF for one employee per pay period.
Uses reportlab for PDF creation.
"""

import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reports.pdf_fonts import FONT, FONT_BOLD, peso as _fmt


def generate_payslip_pdf(
    company: dict,
    employee: dict,
    pay_period: dict,
    entry: dict,
) -> bytes:
    """
    Generate a single payslip as a PDF.

    Args:
        company: Company record from DB.
        employee: Employee record from DB.
        pay_period: Pay period record from DB.
        entry: Payroll entry record from DB.

    Returns:
        PDF file as bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "PayslipTitle", parent=styles["Heading1"],
        fontName=FONT_BOLD, fontSize=16, alignment=TA_CENTER, spaceAfter=2 * mm,
    )
    subtitle_style = ParagraphStyle(
        "PayslipSubtitle", parent=styles["Normal"],
        fontName=FONT, fontSize=10, alignment=TA_CENTER, textColor=colors.grey, spaceAfter=4 * mm,
    )
    section_style = ParagraphStyle(
        "SectionHeader", parent=styles["Heading3"],
        fontName=FONT_BOLD, fontSize=11, spaceAfter=2 * mm, spaceBefore=4 * mm,
        textColor=colors.HexColor("#333333"),
    )
    note_style = ParagraphStyle(
        "Note", parent=styles["Normal"],
        fontName=FONT, fontSize=8, textColor=colors.grey, alignment=TA_CENTER, spaceBefore=6 * mm,
    )

    elements = []

    # ---- Company Header ----
    elements.append(Paragraph(company.get("name", "Company"), title_style))
    elements.append(Paragraph(company.get("address", "") or "", subtitle_style))

    # ---- Payslip Title ----
    elements.append(Paragraph("PAYSLIP", ParagraphStyle(
        "PSTitle", parent=styles["Heading2"],
        fontName=FONT_BOLD, fontSize=14, alignment=TA_CENTER, spaceAfter=4 * mm,
    )))

    # ---- Employee Info + Pay Period ----
    emp_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}"
    info_data = [
        ["Employee:", emp_name, "Employee No.:", employee.get("employee_no", "")],
        ["Position:", employee.get("position", "") or "—", "Tax Status:", employee.get("tax_status", "")],
        ["Pay Period:", f"{pay_period['period_start']} to {pay_period['period_end']}", "Payment Date:", pay_period.get("payment_date", "")],
    ]
    info_table = Table(info_data, colWidths=[70, 170, 80, 140])
    info_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTNAME", (0, 0), (0, -1), FONT_BOLD),
        ("FONTNAME", (2, 0), (2, -1), FONT_BOLD),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 4 * mm))

    # ---- Earnings & Deductions Side by Side ----
    # Build earnings column
    earnings_rows = [
        ["EARNINGS", ""],
        ["Basic Pay", _fmt(entry.get("basic_pay", 0))],
        ["Overtime Pay", _fmt(entry.get("overtime_pay", 0))],
        ["Holiday Pay", _fmt(entry.get("holiday_pay", 0))],
        ["Night Differential", _fmt(entry.get("night_differential", 0))],
        ["Non-Taxable Allowances", _fmt(entry.get("allowances_nontaxable", 0))],
        ["Taxable Allowances", _fmt(entry.get("allowances_taxable", 0))],
        ["Commission", _fmt(entry.get("commission", 0))],
        ["13th Month Accrual", _fmt(entry.get("thirteenth_month_accrual", 0))],
        ["", ""],
        ["GROSS PAY", _fmt(entry.get("gross_pay", 0))],
    ]

    # Build deductions column
    deductions_rows = [
        ["DEDUCTIONS", ""],
        ["SSS (Employee)", _fmt(entry.get("sss_employee", 0))],
        ["PhilHealth (Employee)", _fmt(entry.get("philhealth_employee", 0))],
        ["Pag-IBIG (Employee)", _fmt(entry.get("pagibig_employee", 0))],
        ["Withholding Tax", _fmt(entry.get("withholding_tax", 0))],
        ["SSS Loan", _fmt(entry.get("sss_loan", 0))],
        ["Pag-IBIG Loan", _fmt(entry.get("pagibig_loan", 0))],
        ["Cash Advance", _fmt(entry.get("cash_advance", 0))],
        ["Other Deductions", _fmt(entry.get("other_deductions", 0))],
        ["", ""],
        ["TOTAL DEDUCTIONS", _fmt(entry.get("total_deductions", 0))],
    ]

    # Create earnings table
    earn_table = Table(earnings_rows, colWidths=[140, 80])
    earn_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("FONTNAME", (0, -1), (-1, -1), FONT_BOLD),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("LINEBELOW", (0, 0), (-1, 0), 1, colors.black),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
        ("LINEBELOW", (0, -1), (-1, -1), 1, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f0f0f0")),
    ]))

    # Create deductions table
    ded_table = Table(deductions_rows, colWidths=[140, 80])
    ded_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("FONTNAME", (0, -1), (-1, -1), FONT_BOLD),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("LINEBELOW", (0, 0), (-1, 0), 1, colors.black),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
        ("LINEBELOW", (0, -1), (-1, -1), 1, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f0f0f0")),
    ]))

    # Side-by-side layout
    combined = Table([[earn_table, ded_table]], colWidths=[230, 230])
    combined.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(combined)
    elements.append(Spacer(1, 6 * mm))

    # ---- Net Pay Box ----
    net_pay = entry.get("net_pay", 0)
    net_data = [["NET PAY", _fmt(net_pay)]]
    net_table = Table(net_data, colWidths=[360, 100])
    net_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 14),
        ("FONTNAME", (0, 0), (-1, -1), FONT_BOLD),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#2563eb")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#1e40af")),
    ]))
    elements.append(net_table)
    elements.append(Spacer(1, 6 * mm))

    # ---- Employer Contributions (for reference) ----
    elements.append(Paragraph("Employer Contributions (for reference only — not deducted from pay)", section_style))
    er_data = [
        ["SSS (Employer)", _fmt(entry.get("sss_employer", 0))],
        ["PhilHealth (Employer)", _fmt(entry.get("philhealth_employer", 0))],
        ["Pag-IBIG (Employer)", _fmt(entry.get("pagibig_employer", 0))],
    ]
    er_total = entry.get("sss_employer", 0) + entry.get("philhealth_employer", 0) + entry.get("pagibig_employer", 0)
    er_data.append(["Total Employer Cost", _fmt(er_total)])

    er_table = Table(er_data, colWidths=[160, 80])
    er_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.grey),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("FONTNAME", (0, -1), (-1, -1), FONT_BOLD),
        ("LINEABOVE", (0, -1), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(er_table)

    # ---- Footer ----
    elements.append(Paragraph(
        "This is a system-generated payslip. If you have questions, contact your HR department.",
        note_style,
    ))

    # Build PDF
    doc.build(elements)
    return buffer.getvalue()


def generate_all_payslips_pdf(
    company: dict,
    employees: list[dict],
    pay_period: dict,
    entries: dict,
) -> bytes:
    """
    Generate a combined PDF with all employees' payslips (one per page).

    Args:
        company: Company record.
        employees: List of employee records.
        pay_period: Pay period record.
        entries: Dict of payroll entries keyed by employee_id.

    Returns:
        Combined PDF as bytes.
    """
    from pypdf import PdfWriter

    writer = PdfWriter()

    for emp in employees:
        if emp["id"] not in entries:
            continue
        single = generate_payslip_pdf(company, emp, pay_period, entries[emp["id"]])
        writer.append(io.BytesIO(single))

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()
