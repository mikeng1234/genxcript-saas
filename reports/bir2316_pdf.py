"""
BIR Form 2316 — Certificate of Compensation Payment / Tax Withheld
September 2021 (ENCS) official format recreation using ReportLab canvas.

Layout (portrait A4):
  Left column  : Part I (Employee) → Part II (Present Employer)
               → Part III (Previous Employer) → Part IVA (Summary)
  Right column : Part IV-B compensation table (items 29-52), full height
  Full-width   : Signature block at bottom
"""

import io
from datetime import date

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reports.pdf_fonts import FONT, FONT_BOLD


# ── Page constants (Portrait A4) ──────────────────────────────────────────────
PAGE_W, PAGE_H = A4           # 595.28 × 841.89 pt
ML, MR, MT, MB = 18, 18, 14, 14
BODY_W   = PAGE_W - ML - MR  # ≈ 559.28
BODY_TOP = PAGE_H - MT        # ≈ 827.89

# Column split (left ≈ 42%, right ≈ 58%)
LCOL_X = ML
LCOL_W = 235
RCOL_X = ML + LCOL_W
RCOL_W = BODY_W - LCOL_W     # ≈ 324.28

# Compensation table sub-column widths (right column)
R_NUM  = 15
R_AMT  = 65
R_DESC = RCOL_W - R_NUM - R_AMT  # ≈ 244.28

# Colors
BIR_BLUE = colors.Color(0.20, 0.36, 0.60)
GRAY_BG  = colors.Color(0.87, 0.87, 0.87)
TOTAL_BG = colors.Color(0.78, 0.78, 0.78)


# ── Low-level helpers ─────────────────────────────────────────────────────────

def _p(centavos, blank_zero=True):
    """Format centavos → peso display. Returns '' for zero when blank_zero=True."""
    if centavos is None:
        return ""
    v = centavos / 100
    if blank_zero and v == 0:
        return ""
    return f"{v:,.2f}"


def _safe(val, default=""):
    return val if val else default


def _fill(c, x, y, w, h, color):
    c.saveState()
    c.setFillColor(color)
    c.rect(x, y, w, h, fill=1, stroke=0)
    c.restoreState()


def _bar(c, x, y, w, h, text, fs=6.5, bg=None, fg=None):
    """Solid-color section header bar with left-aligned text."""
    bg = bg or BIR_BLUE
    fg = fg or colors.white
    _fill(c, x, y, w, h, bg)
    c.rect(x, y, w, h, fill=0, stroke=1)
    c.saveState()
    c.setFont(FONT_BOLD, fs)
    c.setFillColor(fg)
    c.drawString(x + 3, y + (h - fs) / 2 + 0.5, text)
    c.restoreState()


def _subbar(c, x, y, w, h, text, fs=5.5):
    _bar(c, x, y, w, h, text, fs=fs, bg=GRAY_BG, fg=colors.black)


def _field(c, x, y, w, h, num, label, value="", lsz=4.8, vsz=7.5, bold=False):
    """Labeled form field box: tiny number top-left, label beside it, value at bottom."""
    c.rect(x, y, w, h, fill=0, stroke=1)
    c.saveState()
    if num:
        c.setFont(FONT, 4.3)
        c.setFillColor(colors.Color(0.35, 0.35, 0.35))
        c.drawString(x + 1.5, y + h - 5.8, str(num))
    c.setFont(FONT, lsz)
    c.setFillColor(colors.black)
    c.drawString(x + (7.5 if num else 2), y + h - 5.8, label)
    if value:
        c.setFont(FONT_BOLD if bold else FONT, vsz)
        c.drawString(x + 2, y + 2.5, str(value))
    c.restoreState()


def _mfield(c, x, y, h, fields):
    """Draw multiple adjacent _field boxes on one row.
    fields: list of (width, num, label, value) tuples.
    """
    cx = x
    for w, num, label, value in fields:
        _field(c, cx, y, w, h, num, label, value)
        cx += w


def _crow(c, y, rh, num, desc, amt="", shaded=False, bold=False, dsz=5.3):
    """One row in the right-column IV-B compensation table."""
    if shaded:
        _fill(c, RCOL_X, y, RCOL_W, rh, TOTAL_BG)
    c.rect(RCOL_X,                  y, R_NUM,  rh, fill=0, stroke=1)
    c.rect(RCOL_X + R_NUM,          y, R_DESC, rh, fill=0, stroke=1)
    c.rect(RCOL_X + R_NUM + R_DESC, y, R_AMT,  rh, fill=0, stroke=1)
    c.saveState()
    c.setFont(FONT_BOLD if bold else FONT, 5.5)
    if num:
        c.drawCentredString(RCOL_X + R_NUM / 2, y + (rh - 5.5) / 2, str(num))
    c.setFont(FONT_BOLD if bold else FONT, dsz)
    c.drawString(RCOL_X + R_NUM + 2, y + (rh - dsz) / 2, desc)
    if amt:
        c.setFont(FONT, 6.5)
        c.drawRightString(RCOL_X + R_NUM + R_DESC + R_AMT - 2, y + (rh - 6.5) / 2, amt)
    c.restoreState()


def _srow(c, x, y, w, rh, num, label, amt="", shaded=False, lsz=5.3, bold=False):
    """One row for Part IVA summary: number | description | amount."""
    num_w  = 20
    amt_w  = 68
    desc_w = w - num_w - amt_w
    if shaded:
        _fill(c, x, y, w, rh, TOTAL_BG)
    c.rect(x,               y, num_w,  rh, fill=0, stroke=1)
    c.rect(x + num_w,       y, desc_w, rh, fill=0, stroke=1)
    c.rect(x + num_w + desc_w, y, amt_w, rh, fill=0, stroke=1)
    c.saveState()
    c.setFont(FONT, 5.5)
    if num:
        c.drawCentredString(x + num_w / 2, y + (rh - 5.5) / 2, str(num))
    c.setFont(FONT_BOLD if bold else FONT, lsz)
    c.drawString(x + num_w + 2, y + (rh - lsz) / 2, label)
    if amt:
        c.setFont(FONT, 7)
        c.drawRightString(x + w - 2, y + (rh - 7) / 2, amt)
    c.restoreState()


# ── Main generator ────────────────────────────────────────────────────────────

def generate_bir2316_pdf(
    company: dict,
    employee: dict,
    annual: dict,
    year: int,
) -> bytes:
    """
    Generate BIR Form 2316 (September 2021 ENCS) as a portrait A4 PDF.

    Args:
        company:  companies row — name, bir_tin (or tin), address
        employee: employees row — first_name, last_name, middle_name,
                  bir_tin, tax_status, date_hired, address, rdo_code,
                  date_of_birth, contact_number  (all optional, handled gracefully)
        annual:   centavo totals for the calendar year:
                  basic_pay, overtime_pay, holiday_pay, night_differential,
                  allowances_nontaxable, allowances_taxable, commission,
                  thirteenth_month_accrual,
                  sss_employee, philhealth_employee, pagibig_employee,
                  withholding_tax
        year:     calendar year (int) this certificate covers

    Returns:
        PDF bytes (portrait A4).
    """

    # ── Derived computations ──────────────────────────────────────────────────
    g = lambda k: annual.get(k) or 0

    contributions = g("sss_employee") + g("philhealth_employee") + g("pagibig_employee")

    thirteenth = g("thirteenth_month_accrual")
    th_nt = min(thirteenth, 9_000_000)   # ≤ P90,000 in centavos — non-taxable
    th_tx = max(0, thirteenth - 9_000_000)  # excess — taxable

    # Non-taxable items (29-37)
    i29 = 0                          # MWE basic (n/a for regular EE)
    i30 = 0; i31 = 0; i32 = 0; i33 = 0   # MWE holiday/OT/NSD/hazard
    i34 = th_nt                      # 13th month ≤ P90k
    i35 = g("allowances_nontaxable") # de minimis benefits
    i36 = contributions              # SSS + PhilHealth + PagIBIG (EE share)
    i37 = 0                          # other non-taxable
    i38 = i29 + i30 + i31 + i32 + i33 + i34 + i35 + i36 + i37

    # Taxable items (39-52)
    i39  = g("basic_pay")
    i40  = 0; i41 = 0; i42 = 0; i43 = 0   # Representation/Transport/COLA/Housing
    i44  = g("allowances_taxable")
    i45  = g("overtime_pay") + g("holiday_pay") + g("night_differential")
    i46  = g("commission")
    i47  = 0; i48 = 0                  # Profit sharing / Director's fees
    i49  = th_tx                       # Taxable 13th month
    i50  = 0; i51a = 0; i51b = 0      # Hazard / Others
    i52  = (i39 + i40 + i41 + i42 + i43 + i44 + i45 + i46
            + i47 + i48 + i49 + i50 + i51a + i51b)

    # Part IVA summary
    i19  = i38 + i52
    i20  = i38
    i21  = i52
    i22  = 0
    i23  = i21 + i22
    i24  = g("withholding_tax")
    i25a = i24
    i25b = 0
    i28  = i25a + i25b

    # ── Layout pre-computation ────────────────────────────────────────────────
    HDR_H  = 38   # page header height
    YR_H   = 16   # year / period row
    SH_H   = 10   # section header bars

    CONTENT_TOP    = BODY_TOP - HDR_H - YR_H - SH_H   # ≈ 763.89
    SIG_TOP        = MB + 74                            # top of signature block
    CONTENT_HEIGHT = CONTENT_TOP - SIG_TOP              # ≈ 675.89

    # Right column: NT_HDR(10) + 9*RH + NT_TOT(RH+1) + TX_HDR(10) + 14*RH + TX_TOT(RH+1)
    #             = 22 + 25*RH
    RH     = (CONTENT_HEIGHT - 22) / 25
    RH_TOT = RH + 1

    # Left column: 3 section bars (Part II, III, IVA) × 10 = 30
    #              + IVA column sub-header (NT_H) = 10
    #              + (6 + 3 + 3 + 9) = 21 field rows
    LRH    = (CONTENT_HEIGHT - 40) / 21  # left row height

    NT_H   = 10   # sub-section header bars (A / B)

    # ── Canvas ────────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)

    # Page border
    c.rect(ML, MB, BODY_W, PAGE_H - MT - MB, fill=0, stroke=1)

    # ══ HEADER ════════════════════════════════════════════════════════════════
    HDR_Y = BODY_TOP - HDR_H

    c.saveState()
    c.setFont(FONT, 6.5)
    c.drawString(ML + 3, HDR_Y + HDR_H - 11, "Republic of the Philippines")
    c.drawString(ML + 3, HDR_Y + HDR_H - 19, "Department of Finance")
    c.setFont(FONT_BOLD, 6.5)
    c.drawString(ML + 3, HDR_Y + HDR_H - 27, "Bureau of Internal Revenue")
    c.restoreState()

    # BIR Form No. box (top-right)
    FN_W = 95; FN_X = ML + BODY_W - FN_W
    c.rect(FN_X, HDR_Y, FN_W, HDR_H, fill=0, stroke=1)
    c.saveState()
    c.setFont(FONT, 5.5)
    c.drawString(FN_X + 3, HDR_Y + HDR_H - 9, "BIR Form No.")
    c.setFont(FONT_BOLD, 18)
    c.drawString(FN_X + 5, HDR_Y + HDR_H - 27, "2316")
    c.setFont(FONT, 5.5)
    c.drawString(FN_X + 3, HDR_Y + 7, "September 2021 (ENCS)")
    c.restoreState()

    # Center title
    CTR_X = ML + 80; CTR_W = BODY_W - 80 - FN_W
    c.saveState()
    c.setFont(FONT_BOLD, 9.5)
    c.drawCentredString(CTR_X + CTR_W / 2, HDR_Y + HDR_H - 11,
                        "Certificate of Compensation Payment / Tax Withheld")
    c.setFont(FONT, 7)
    c.drawCentredString(CTR_X + CTR_W / 2, HDR_Y + HDR_H - 20,
                        "For Compensation Payment With or Without Tax Withheld")
    c.setFont(FONT, 6)
    c.drawCentredString(CTR_X + CTR_W / 2, HDR_Y + HDR_H - 29,
                        'Fill in all applicable spaces. Mark all appropriate boxes with an "X".')
    c.restoreState()

    c.line(ML, HDR_Y, ML + BODY_W, HDR_Y)

    # ══ YEAR / PERIOD ROW ════════════════════════════════════════════════════
    YR_Y = HDR_Y - YR_H
    _field(c, ML, YR_Y, 65, YR_H, "1", "For the Year (YYYY)", str(year), bold=True)
    _field(c, ML + 65, YR_Y, 120, YR_H, "2",
           "For the Period    From (MM/DD)          To (MM/DD)",
           "01/01                        12/31")
    _subbar(c, ML + 185, YR_Y, 105, YR_H, "  For BIR Use Only  BCS / Item:")
    c.rect(ML + 290, YR_Y, BODY_W - 290, YR_H, fill=0, stroke=1)

    # ══ TOP SECTION HEADER ROW (Part I | Part IV-B) ═══════════════════════════
    SH_Y = YR_Y - SH_H   # = CONTENT_TOP
    _bar(c, LCOL_X, SH_Y, LCOL_W, SH_H,
         "Part I  -  Employee Information")
    _bar(c, RCOL_X, SH_Y, RCOL_W, SH_H,
         "Part IV-B  Details of Compensation Income & Tax Withheld from Present Employer",
         fs=5.8)

    # ══ RIGHT COLUMN: PART IV-B (full height) ═════════════════════════════════
    ry = SH_Y   # tracks bottom of last-drawn element in right column

    # — A. Non-Taxable sub-header —
    ry -= NT_H
    _fill(c, RCOL_X, ry, RCOL_W, NT_H, GRAY_BG)
    c.rect(RCOL_X, ry, RCOL_W, NT_H, fill=0, stroke=1)
    c.saveState()
    c.setFont(FONT_BOLD, 5.5)
    c.drawString(RCOL_X + R_NUM + 2, ry + 2.8,
                 "A.  NON-TAXABLE / EXEMPT COMPENSATION INCOME")
    c.drawRightString(RCOL_X + RCOL_W - 2, ry + 2.8, "Amount")
    c.restoreState()

    NT_ROWS = [
        ("29", "Basic Salary (incl. exempt P250,000 & below) or Statutory Min. Wage of MWE", i29),
        ("30", "Holiday Pay (MWE)", i30),
        ("31", "Overtime Pay (MWE)", i31),
        ("32", "Night Shift Differential (MWE)", i32),
        ("33", "Hazard Pay (MWE)", i33),
        ("34", "13th Month Pay and Other Benefits (maximum of P90,000)", i34),
        ("35", "De Minimis Benefits", i35),
        ("36", "SSS, GSIS, PHIC & PAG-IBIG Contributions and Union Dues (EE share only)", i36),
        ("37", "Salaries and Other Forms of Compensation", i37),
    ]
    for num, desc, amt in NT_ROWS:
        ry -= RH
        _crow(c, ry, RH, num, desc, _p(amt))

    ry -= RH_TOT
    _crow(c, ry, RH_TOT, "38",
          "Total Non-Taxable/Exempt Compensation Income (Sum of Items 29 to 37)",
          _p(i38, blank_zero=False), shaded=True, bold=True)

    # — B. Taxable sub-header —
    ry -= NT_H
    _fill(c, RCOL_X, ry, RCOL_W, NT_H, GRAY_BG)
    c.rect(RCOL_X, ry, RCOL_W, NT_H, fill=0, stroke=1)
    c.saveState()
    c.setFont(FONT_BOLD, 5.5)
    c.drawString(RCOL_X + R_NUM + 2, ry + 2.8,
                 "B.  TAXABLE COMPENSATION INCOME                REGULAR")
    c.restoreState()

    TX_ROWS = [
        ("39",  "Basic Salary",                                    i39),
        ("40",  "Representation",                                  i40),
        ("41",  "Transportation",                                  i41),
        ("42",  "Cost of Living Allowance (COLA)",                 i42),
        ("43",  "Fixed Housing Allowance",                         i43),
        ("44",  "Others (specify)",                                i44),
        ("45",  "Overtime Pay",                                    i45),
        ("46",  "Commission",                                      i46),
        ("47",  "Profit Sharing",                                  i47),
        ("48",  "Fees Including Director's Fees",                  i48),
        ("49",  "Taxable 13th Month Pay and Other Benefits",       i49),
        ("50",  "Hazard Pay",                                      i50),
        ("51A", "Others (specify)",                                i51a),
        ("51B", "",                                                i51b),
    ]
    for num, desc, amt in TX_ROWS:
        ry -= RH
        _crow(c, ry, RH, num, desc, _p(amt))

    ry -= RH_TOT
    _crow(c, ry, RH_TOT, "52",
          "Total Taxable Compensation Income (Sum of Items 39 to 51B)",
          _p(i52, blank_zero=False), shaded=True, bold=True)

    # ══ LEFT COLUMN ═══════════════════════════════════════════════════════════
    # Part I → Part II → Part III → Part IVA  (all stacked, fills same height as right)

    ly = SH_Y   # tracks bottom of last-drawn element in left column

    last  = _safe(employee.get("last_name",  "")).upper()
    first = _safe(employee.get("first_name", "")).upper()
    mid   = _safe(employee.get("middle_name") or "").upper()
    emp_name = f"{last}, {first} {mid}".strip().rstrip(",").strip()

    tin_val = _safe(employee.get("bir_tin"))
    rdo_val = _safe(employee.get("rdo_code"))
    addr    = _safe(employee.get("address"))

    dob = employee.get("date_of_birth") or employee.get("birth_date") or ""
    if hasattr(dob, "strftime"):
        dob = dob.strftime("%m/%d/%Y")
    contact = _safe(employee.get("contact_number"))

    # ── Part I rows (6 rows) ──
    ly -= LRH
    _mfield(c, LCOL_X, ly, LRH, [
        (105,          "3",  "Taxpayer Identification Number (TIN)", tin_val),
        (LCOL_W - 148, "4",  "Employee's Name (Last, First, Middle)", emp_name),
        (43,           "5",  "RDO Code",                             rdo_val),
    ])

    ly -= LRH
    _mfield(c, LCOL_X, ly, LRH, [
        (LCOL_W - 44, "6",  "Registered Address", addr),
        (44,          "6A", "ZIP Code",            ""),
    ])

    ly -= LRH
    _mfield(c, LCOL_X, ly, LRH, [
        (LCOL_W - 44, "6B", "Local Home Address", ""),
        (44,          "6C", "ZIP Code",            ""),
    ])

    ly -= LRH
    _field(c, LCOL_X, ly, LCOL_W, LRH, "6D", "Foreign Address", "")

    ly -= LRH
    _mfield(c, LCOL_X, ly, LRH, [
        (115,          "7", "Date of Birth (MM/DD/YYYY)", str(dob) if dob else ""),
        (LCOL_W - 115, "8", "Contact Number",             contact),
    ])

    ly -= LRH
    _mfield(c, LCOL_X, ly, LRH, [
        (95,           "9",  "Stat. Min. Wage Rate / Day",   ""),
        (95,           "10", "Stat. Min. Wage Rate / Month", ""),
        (LCOL_W - 190, "11", "[ ]  Min. Wage Earner (MWE)", ""),
    ])

    # ── Part II — Present Employer (header + 3 rows) ──
    ly -= SH_H
    _bar(c, LCOL_X, ly, LCOL_W, SH_H,
         "Part II  -  Employer Information (Present)")

    co_tin  = _safe(company.get("bir_tin") or company.get("tin"))
    co_name = _safe(company.get("name"))
    co_addr = _safe(company.get("address"))

    ly -= LRH
    _mfield(c, LCOL_X, ly, LRH, [
        (105,          "12", "TIN",             co_tin),
        (LCOL_W - 105, "13", "Employer's Name", co_name),
    ])

    ly -= LRH
    _mfield(c, LCOL_X, ly, LRH, [
        (LCOL_W - 44, "14",  "Registered Address", co_addr),
        (44,          "14A", "ZIP Code",            ""),
    ])

    ly -= LRH
    _field(c, LCOL_X, ly, LCOL_W, LRH, "15",
           "Type of Employer:  [X] Main    [ ] Secondary", "")

    # ── Part III — Previous Employer (header + 3 rows) ──
    ly -= SH_H
    _bar(c, LCOL_X, ly, LCOL_W, SH_H,
         "Part III  -  Employer Information (Previous)")

    ly -= LRH
    _mfield(c, LCOL_X, ly, LRH, [
        (105,          "16", "TIN",             ""),
        (LCOL_W - 105, "17", "Employer's Name", ""),
    ])

    ly -= LRH
    _mfield(c, LCOL_X, ly, LRH, [
        (LCOL_W - 44, "18",  "Registered Address", ""),
        (44,          "18A", "ZIP Code",            ""),
    ])

    ly -= LRH
    _field(c, LCOL_X, ly, LCOL_W, LRH, "",
           "SUPPLEMENTARY - Previous Employer details (attach if applicable)", "")

    # ── Part IVA — Summary (header + 9 rows) ──
    ly -= SH_H
    _bar(c, LCOL_X, ly, LCOL_W, SH_H, "Part IVA  -  Summary")

    # Column sub-header for IVA
    ly -= NT_H
    _fill(c, LCOL_X, ly, LCOL_W, NT_H, GRAY_BG)
    c.rect(LCOL_X, ly, LCOL_W, NT_H, fill=0, stroke=1)
    c.saveState()
    c.setFont(FONT_BOLD, 5.3)
    c.drawString(LCOL_X + 3, ly + 2.8, "  No.    Description")
    c.drawRightString(LCOL_X + LCOL_W - 2, ly + 2.8, "Amount")
    c.restoreState()

    IVA_ROWS = [
        ("19",  "Gross Compensation Income — Present Employer (Items 38+52)", i19,  False),
        ("20",  "Less: Non-Taxable/Exempt Compensation Income (Item 38)",       i20,  False),
        ("21",  "Taxable Compensation Income — Present Employer",               i21,  False),
        ("22",  "Add: Taxable Compensation — Previous Employer, if any",        i22,  False),
        ("23",  "Gross Taxable Compensation Income (Items 21+22)",              i23,  True),
        ("24",  "Tax Due",                                                      i24,  True),
        ("25A", "Taxes Withheld - Present Employer",                           i25a, False),
        ("25B", "Taxes Withheld - Previous Employer, if applicable",           i25b, False),
        ("28",  "Total Taxes Withheld (Items 25A + 25B)",                      i28,  True),
    ]
    for num, label, amt, shaded in IVA_ROWS:
        ly -= LRH
        _srow(c, LCOL_X, ly, LCOL_W, LRH, num, label,
              _p(amt, blank_zero=(not shaded)), shaded=shaded, bold=shaded)

    # ══ SIGNATURE BLOCK ═══════════════════════════════════════════════════════
    SIG_H = SIG_TOP - MB
    c.rect(ML, MB, BODY_W, SIG_H, fill=0, stroke=1)

    # Declaration text
    decl = [
        ("I/We declare, under the penalties of perjury, that this certificate has been made in good faith, verified by me/us, and to the best of my/our"),
        ("knowledge and belief, is true and correct pursuant to the provisions of the National Internal Revenue Code, as amended, and the regulations"),
        ("issued under authority thereof. I/we give consent to the processing of my/our information under the Data Privacy Act of 2012 (R.A. No. 10173)."),
    ]
    c.saveState()
    c.setFont(FONT, 4.7)
    for i, line in enumerate(decl):
        c.drawString(ML + 3, MB + SIG_H - 8 - i * 5.5, line)
    c.restoreState()

    # Vertical divider splitting sig area in half
    MID_SIG_X = ML + BODY_W / 2
    c.line(MID_SIG_X, MB, MID_SIG_X, MB + SIG_H)

    # Left half — Present Employer
    EMP_LINE_Y = MB + 28
    c.line(ML + 8, EMP_LINE_Y, MID_SIG_X - 8, EMP_LINE_Y)
    c.saveState()
    c.setFont(FONT, 5)
    c.drawCentredString(ML + (MID_SIG_X - ML) / 2, EMP_LINE_Y - 7,
                        "Present Employer / Authorized Agent Signature over Printed Name")
    c.drawString(ML + 8, EMP_LINE_Y - 14,
                 "(Head of Accounting / Human Resource or Authorized Representative)")
    c.setFont(FONT, 5.5)
    c.drawString(ML + 8, EMP_LINE_Y - 22, "Date Signed: _____________________")
    c.restoreState()

    # Right half — Conforme / Employee
    c.saveState()
    c.setFont(FONT_BOLD, 6)
    c.drawString(MID_SIG_X + 5, MB + SIG_H - 11, "CONFORME:")
    c.restoreState()
    EE_LINE_Y = MB + 28
    c.line(MID_SIG_X + 8, EE_LINE_Y, ML + BODY_W - 8, EE_LINE_Y)
    c.saveState()
    c.setFont(FONT, 5)
    c.drawCentredString(MID_SIG_X + (BODY_W / 2) / 2, EE_LINE_Y - 7,
                        "Employee Signature over Printed Name             Date Signed")
    c.setFont(FONT, 4.7)
    c.drawString(MID_SIG_X + 8, EE_LINE_Y - 16,
                 "To be accomplished under substituted filing (BIR Form No. 1700).")
    c.restoreState()

    # BIR note
    c.saveState()
    c.setFont(FONT, 4.5)
    c.drawString(ML + 3, MB + 3,
                 "*NOTE: The BIR Data Privacy notice is available at the BIR website (www.bir.gov.ph)")
    c.restoreState()

    # ══ SAVE ══════════════════════════════════════════════════════════════════
    c.save()
    buf.seek(0)
    return buf.read()
