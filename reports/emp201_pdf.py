"""
Employee 201 File PDF Generator.

Generates a comprehensive Employee 201 (personnel file) PDF on A4 paper
with all standard HR sections: employment info, compensation, government IDs,
personal information, address, emergency contact, education, and spouse info.
Uses reportlab for PDF creation.
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
from reports.pdf_fonts import FONT, FONT_BOLD, peso as _fmt


# ── Brand colours (consistent with other report PDFs) ─────────────────────────
_BRAND_DARK  = colors.HexColor("#1e3a5f")   # dark navy — header / section titles
_BRAND_MID   = colors.HexColor("#2563eb")   # blue accent — horizontal rules
_SECTION_BG  = colors.HexColor("#eff6ff")   # very light blue — section header bg
_TEXT_MAIN   = colors.HexColor("#1f2937")
_TEXT_MUTED  = colors.HexColor("#6b7280")
_TEXT_LABEL  = colors.HexColor("#374151")
_BORDER      = colors.HexColor("#d1d5db")


def _val(v) -> str:
    """Return the value as string, or '—' if None/empty."""
    if v is None:
        return "\u2014"
    s = str(v).strip()
    return s if s else "\u2014"


def _fmt_date(raw) -> str:
    """Parse an ISO date string and return a human-readable date, or '—'."""
    if not raw:
        return "\u2014"
    try:
        d = date.fromisoformat(str(raw))
        return d.strftime("%B %d, %Y")
    except Exception:
        return _val(raw)


def _fmt_salary(centavos) -> str:
    """Format a centavo integer as a peso string."""
    if centavos is None:
        return "\u2014"
    try:
        return _fmt(int(centavos))
    except Exception:
        return _val(centavos)


def generate_emp201_pdf(emp: dict, profile: dict, department: str) -> bytes:
    """
    Generate an Employee 201 File as a PDF.

    Args:
        emp:        Employee record dict (employee_no, first_name, last_name,
                    position, employment_type, date_hired, resignation_date,
                    basic_salary, salary_type, tax_status, sss_no,
                    philhealth_no, pagibig_no, bir_tin, bank_account, email).
        profile:    Employee profile dict (middle_name, suffix, date_of_birth,
                    place_of_birth, sex, civil_status, nationality, religion,
                    mobile_no, regularization_date, present_address_street,
                    present_address_barangay, present_address_city,
                    present_address_province, present_address_zip,
                    perm_address_same, perm_address_street,
                    perm_address_barangay, perm_address_city,
                    perm_address_province, perm_address_zip,
                    emergency_name, emergency_relationship, emergency_phone,
                    emergency_address, spouse_name, spouse_occupation,
                    spouse_employer, spouse_contact, education_degree,
                    education_school, education_year).
        department: Department name string.

    Returns:
        PDF file contents as bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
    )

    # ── Paragraph styles ──────────────────────────────────────────────────────
    doc_title_style = ParagraphStyle(
        "DocTitle",
        fontSize=16,
        leading=20,
        textColor=_BRAND_DARK,
        fontName=FONT_BOLD,
        alignment=TA_CENTER,
        spaceAfter=2,
    )
    emp_name_style = ParagraphStyle(
        "EmpName",
        fontSize=13,
        leading=17,
        textColor=_BRAND_DARK,
        fontName=FONT_BOLD,
        alignment=TA_CENTER,
        spaceAfter=2,
    )
    emp_sub_style = ParagraphStyle(
        "EmpSub",
        fontSize=9,
        leading=13,
        textColor=_TEXT_MUTED,
        fontName=FONT,
        alignment=TA_CENTER,
        spaceAfter=0,
    )
    section_title_style = ParagraphStyle(
        "SectionTitle",
        fontSize=9,
        leading=12,
        textColor=_BRAND_DARK,
        fontName=FONT_BOLD,
        alignment=TA_LEFT,
        spaceBefore=0,
        spaceAfter=0,
    )
    label_style = ParagraphStyle(
        "FieldLabel",
        fontSize=7.5,
        leading=11,
        textColor=_TEXT_MUTED,
        fontName=FONT_BOLD,
        alignment=TA_LEFT,
        spaceAfter=0,
    )
    value_style = ParagraphStyle(
        "FieldValue",
        fontSize=9,
        leading=13,
        textColor=_TEXT_MAIN,
        fontName=FONT,
        alignment=TA_LEFT,
        spaceAfter=0,
    )
    footer_style = ParagraphStyle(
        "Footer",
        fontSize=7.5,
        textColor=_TEXT_MUTED,
        fontName=FONT,
        alignment=TA_CENTER,
    )

    # ── Helper: build a section header row ────────────────────────────────────
    def _section_row(title: str, col_widths):
        """Return a single-row Table that acts as a coloured section header."""
        cell = Paragraph(title, section_title_style)
        tbl = Table([[cell]], colWidths=[sum(col_widths)])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), _SECTION_BG),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, _BRAND_MID),
        ]))
        return tbl

    # ── Helper: build a two-column field grid ─────────────────────────────────
    def _field_grid(pairs, col_widths, cols_per_row=2):
        """
        Build a Table of label+value pairs arranged in a grid.

        pairs      : list of (label, value) tuples
        col_widths : [left_col_w, right_col_w] for a 2-col grid, or
                     [c0, c1, c2, c3] for a 4-col grid (label, val, label, val)
        cols_per_row: 1 or 2 pairs per table row
        """
        page_w = sum(col_widths)

        if cols_per_row == 1:
            # Full-width: each pair occupies an entire row (label + value stacked)
            lw = page_w * 0.30
            vw = page_w * 0.70
            rows = []
            for lbl, val in pairs:
                rows.append([
                    Paragraph(lbl, label_style),
                    Paragraph(_val(val), value_style),
                ])
            tbl = Table(rows, colWidths=[lw, vw])
            tbl.setStyle(TableStyle([
                ("VALIGN",        (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING",   (0, 0), (-1, -1), 6),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
                ("TOPPADDING",    (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LINEBELOW", (0, 0), (-1, -1), 0.25, _BORDER),
            ]))
            return tbl

        # Two pairs per row: [label0 | value0 | label1 | value1]
        half = page_w / 2
        lw = half * 0.38
        vw = half * 0.62
        widths = [lw, vw, lw, vw]

        rows = []
        for i in range(0, len(pairs), 2):
            left_lbl, left_val = pairs[i]
            if i + 1 < len(pairs):
                right_lbl, right_val = pairs[i + 1]
            else:
                right_lbl, right_val = "", ""
            rows.append([
                Paragraph(left_lbl,          label_style),
                Paragraph(_val(left_val),    value_style),
                Paragraph(right_lbl,         label_style),
                Paragraph(_val(right_val),   value_style),
            ])

        tbl = Table(rows, colWidths=widths)
        tbl.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
            ("TOPPADDING",    (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LINEBELOW",     (0, 0), (-1, -1), 0.25, _BORDER),
            # Vertical divider between left and right pair
            ("LINEBEFORE",    (2, 0), (2, -1), 0.5,  _BORDER),
        ]))
        return tbl

    # ── Data extraction ───────────────────────────────────────────────────────
    first       = emp.get("first_name", "") or ""
    last        = emp.get("last_name",  "") or ""
    middle      = profile.get("middle_name", "") or ""
    suffix      = profile.get("suffix", "") or ""
    full_name   = " ".join(filter(None, [first, middle, last, suffix])).strip() or "\u2014"

    emp_no      = _val(emp.get("employee_no"))
    position    = _val(emp.get("position"))
    dept        = _val(department)
    emp_type    = _val(emp.get("employment_type"))
    date_hired  = _fmt_date(emp.get("date_hired"))
    sep_date    = _fmt_date(emp.get("resignation_date"))
    reg_date    = _fmt_date(profile.get("regularization_date"))

    salary_str  = _fmt_salary(emp.get("basic_salary"))
    sal_type    = _val(emp.get("salary_type"))
    tax_status  = _val(emp.get("tax_status"))

    sss         = _val(emp.get("sss_no"))
    philhealth  = _val(emp.get("philhealth_no"))
    pagibig     = _val(emp.get("pagibig_no"))
    bir_tin     = _val(emp.get("bir_tin"))
    bank_acct   = _val(emp.get("bank_account"))

    dob         = _fmt_date(profile.get("date_of_birth"))
    pob         = _val(profile.get("place_of_birth"))
    sex         = _val(profile.get("sex"))
    civil       = _val(profile.get("civil_status"))
    nationality = _val(profile.get("nationality"))
    religion    = _val(profile.get("religion"))
    mobile      = _val(profile.get("mobile_no"))

    pres_street   = _val(profile.get("present_address_street"))
    pres_brgy     = _val(profile.get("present_address_barangay"))
    pres_city     = _val(profile.get("present_address_city"))
    pres_prov     = _val(profile.get("present_address_province"))
    pres_zip      = _val(profile.get("present_address_zip"))
    pres_address  = ", ".join(
        p for p in [pres_street, pres_brgy, pres_city, pres_prov, pres_zip]
        if p and p != "\u2014"
    ) or "\u2014"

    perm_same   = profile.get("perm_address_same", True)
    if perm_same:
        perm_address = "Same as present address"
    else:
        pm_street = _val(profile.get("perm_address_street"))
        pm_brgy   = _val(profile.get("perm_address_barangay"))
        pm_city   = _val(profile.get("perm_address_city"))
        pm_prov   = _val(profile.get("perm_address_province"))
        pm_zip    = _val(profile.get("perm_address_zip"))
        perm_address = ", ".join(
            p for p in [pm_street, pm_brgy, pm_city, pm_prov, pm_zip]
            if p and p != "\u2014"
        ) or "\u2014"

    ec_name     = _val(profile.get("emergency_name"))
    ec_rel      = _val(profile.get("emergency_relationship"))
    ec_phone    = _val(profile.get("emergency_phone"))
    ec_address  = _val(profile.get("emergency_address"))

    edu_degree  = _val(profile.get("education_degree"))
    edu_school  = _val(profile.get("education_school"))
    edu_year    = _val(profile.get("education_year"))

    today_str   = date.today().strftime("%B %d, %Y")

    # Content width (A4 width minus margins)
    page_w = A4[0] - 40 * mm
    cw = [page_w]   # single-column full width (used for section headers)

    # ── Build story ───────────────────────────────────────────────────────────
    story = []

    # ── Document Header ───────────────────────────────────────────────────────
    story.append(Paragraph("EMPLOYEE 201 FILE", doc_title_style))
    story.append(Spacer(1, 2 * mm))
    story.append(HRFlowable(width="100%", thickness=2, color=_BRAND_MID, spaceAfter=0))
    story.append(Spacer(1, 3 * mm))

    # Employee name + meta
    story.append(Paragraph(full_name, emp_name_style))
    story.append(Paragraph(
        f"Employee No.: {emp_no}  &nbsp;&nbsp;|&nbsp;&nbsp;  "
        f"Position: {position}  &nbsp;&nbsp;|&nbsp;&nbsp;  "
        f"Department: {dept}",
        emp_sub_style,
    ))
    story.append(Paragraph(f"Date Generated: {today_str}", emp_sub_style))
    story.append(Spacer(1, 4 * mm))

    # ── Section 1: Employment Information ─────────────────────────────────────
    story.append(_section_row("EMPLOYMENT INFORMATION", cw))
    story.append(_field_grid([
        ("Employee No.",      emp_no),
        ("Full Name",         full_name),
        ("Position",          position),
        ("Department",        dept),
        ("Employment Type",   emp_type),
        ("Date Hired",        date_hired),
        ("Separation Date",   sep_date),
        ("Regularization Date", reg_date),
    ], cw, cols_per_row=2))
    story.append(Spacer(1, 4 * mm))

    # ── Section 2: Compensation ───────────────────────────────────────────────
    story.append(_section_row("COMPENSATION", cw))
    story.append(_field_grid([
        ("Basic Salary",  salary_str),
        ("Salary Type",   sal_type),
        ("Tax Status",    tax_status),
        ("Email",         _val(emp.get("email"))),
    ], cw, cols_per_row=2))
    story.append(Spacer(1, 4 * mm))

    # ── Section 3: Government IDs ─────────────────────────────────────────────
    story.append(_section_row("GOVERNMENT IDs", cw))
    story.append(_field_grid([
        ("SSS No.",         sss),
        ("PhilHealth No.",  philhealth),
        ("Pag-IBIG No.",    pagibig),
        ("BIR TIN",         bir_tin),
    ], cw, cols_per_row=2))
    story.append(Spacer(1, 4 * mm))

    # ── Section 4: Disbursement Account ──────────────────────────────────────
    story.append(_section_row("DISBURSEMENT ACCOUNT", cw))
    story.append(_field_grid([
        ("Bank / Account No.", bank_acct),
        ("", ""),
    ], cw, cols_per_row=2))
    story.append(Spacer(1, 4 * mm))

    # ── Section 5: Personal Information ──────────────────────────────────────
    story.append(_section_row("PERSONAL INFORMATION", cw))
    story.append(_field_grid([
        ("Date of Birth",  dob),
        ("Place of Birth", pob),
        ("Sex",            sex),
        ("Civil Status",   civil),
        ("Nationality",    nationality),
        ("Religion",       religion),
        ("Mobile No.",     mobile),
        ("", ""),
    ], cw, cols_per_row=2))
    story.append(Spacer(1, 4 * mm))

    # ── Section 6: Address ────────────────────────────────────────────────────
    story.append(_section_row("ADDRESS", cw))
    story.append(_field_grid([
        ("Present Address", pres_address),
        ("Permanent Address", perm_address),
    ], cw, cols_per_row=1))
    story.append(Spacer(1, 4 * mm))

    # ── Section 7: Emergency Contact ──────────────────────────────────────────
    story.append(_section_row("EMERGENCY CONTACT", cw))
    story.append(_field_grid([
        ("Name",         ec_name),
        ("Relationship", ec_rel),
        ("Phone",        ec_phone),
        ("Address",      ec_address),
    ], cw, cols_per_row=2))
    story.append(Spacer(1, 4 * mm))

    # ── Section 8: Educational Background ────────────────────────────────────
    story.append(_section_row("EDUCATIONAL BACKGROUND", cw))
    story.append(_field_grid([
        ("Degree / Course",  edu_degree),
        ("School / University", edu_school),
        ("Year Graduated",   edu_year),
        ("", ""),
    ], cw, cols_per_row=2))

    # ── Section 9: Spouse Information (if married) ────────────────────────────
    civil_raw = (profile.get("civil_status") or "").strip().lower()
    if civil_raw == "married":
        story.append(Spacer(1, 4 * mm))
        story.append(_section_row("SPOUSE INFORMATION", cw))
        story.append(_field_grid([
            ("Spouse Name",       _val(profile.get("spouse_name"))),
            ("Occupation",        _val(profile.get("spouse_occupation"))),
            ("Employer",          _val(profile.get("spouse_employer"))),
            ("Contact No.",       _val(profile.get("spouse_contact"))),
        ], cw, cols_per_row=2))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 8 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=_TEXT_MUTED))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        f"Document generated on {today_str} via GenXcript Payroll System. "
        "This document is system-generated and contains confidential HR information. "
        "Handle in accordance with your company's data privacy policy.",
        footer_style,
    ))

    doc.build(story)
    return buffer.getvalue()
