"""
BIR Form 1604-C — Annual Information Return of Income Taxes Withheld on Compensation
January 2018 (ENCS) official layout recreation using ReportLab canvas.

Two deliverables
────────────────
  generate_bir1604c_pdf()        → Main return, Page 1 (portrait A4)
  generate_bir1604c_alphalist()  → Annex A, Schedule 1 (landscape A4, multi-page)

Data contract
─────────────
  company       : dict with keys  name, bir_tin, address, zip_code,
                                  contact_number, email, rdo_code
  year          : int             (e.g. 2025)
  monthly_taxes : dict            {1..12: total_withholding_centavos}
  employees     : list[dict]      already sorted A-Z by last_name
  annual_entries: dict            {employee_id: aggregated_payroll_dict}
                                  keys: gross_pay, basic_pay, overtime_pay,
                                        holiday_pay, night_differential,
                                        allowances_nontaxable, allowances_taxable,
                                        commission, thirteenth_month_accrual,
                                        sss_employee, philhealth_employee,
                                        pagibig_employee, withholding_tax
                                  all values in centavos (int)
"""

import io
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit


# ── Page constants — Portrait (main form) ─────────────────────────────────────
PAGE_W, PAGE_H = A4             # 595.28 × 841.89 pt
ML, MR, MT, MB = 18, 18, 14, 14
BODY_W   = PAGE_W - ML - MR    # 559.28 pt
BODY_TOP = PAGE_H - MT          # 827.89 pt

# ── Colors ────────────────────────────────────────────────────────────────────
BIR_BLUE = colors.Color(0.18, 0.35, 0.60)
GRAY_BG  = colors.Color(0.85, 0.85, 0.85)
HDR_BG   = colors.Color(0.78, 0.78, 0.78)
LIGHT_BG = colors.Color(0.94, 0.94, 0.94)
TOT_BG   = colors.Color(0.70, 0.70, 0.70)

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

# 13th-month non-taxable threshold (PHP 90,000 in centavos)
_13TH_THRESHOLD = 9_000_000


# ── Shared drawing primitives ─────────────────────────────────────────────────

def _fill(c, x, y, w, h, color):
    c.saveState()
    c.setFillColor(color)
    c.rect(x, y, w, h, stroke=0, fill=1)
    c.restoreState()


def _box(c, x, y, w, h, lw=0.4):
    c.saveState()
    c.setStrokeColor(colors.black)
    c.setLineWidth(lw)
    c.rect(x, y, w, h, stroke=1, fill=0)
    c.restoreState()


def _text(c, x, y, s, size=7, bold=False, align="L",
          col=colors.black, clip_w=None):
    if s is None:
        s = ""
    s = str(s)
    c.saveState()
    c.setFillColor(col)
    fn = "Helvetica-Bold" if bold else "Helvetica"
    c.setFont(fn, size)
    if clip_w:
        while s and c.stringWidth(s, fn, size) > clip_w - 1:
            s = s[:-1]
    if align == "C":
        c.drawCentredString(x, y, s)
    elif align == "R":
        c.drawRightString(x, y, s)
    else:
        c.drawString(x, y, s)
    c.restoreState()


def _hline(c, x1, y, x2, lw=0.4):
    c.saveState(); c.setLineWidth(lw); c.line(x1, y, x2, y); c.restoreState()


def _vline(c, x, y1, y2, lw=0.4):
    c.saveState(); c.setLineWidth(lw); c.line(x, y1, x, y2); c.restoreState()


def _p(centavos, blank_zero=True):
    """Format centavos → peso string."""
    if centavos is None:
        return ""
    v = centavos / 100
    if blank_zero and v == 0:
        return ""
    return f"{v:,.2f}"


def _safe(val, default=""):
    return val if val else default


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN FORM  (Page 1, Portrait A4)
# ─────────────────────────────────────────────────────────────────────────────

def generate_bir1604c_pdf(company: dict, year: int, monthly_taxes: dict) -> bytes:
    """
    Generate BIR Form 1604-C main return (Page 1).

    monthly_taxes: {month_number 1-12: total_withholding_centavos}
    """
    buf = io.BytesIO()
    c   = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"BIR Form 1604-C ({year})")

    y  = BODY_TOP
    x0 = ML
    W  = BODY_W
    RH = 16     # standard row height
    SH = 11     # section-header height

    # ── BIR page header ───────────────────────────────────────────────────────
    # "For BIR Use Only" box — top left
    bcs_w, bcs_h = 70, 30
    _box(c, x0, y - bcs_h, bcs_w, bcs_h)
    _text(c, x0 + 3, y - 9,  "For BIR Use Only", size=6)
    _text(c, x0 + 3, y - 18, "BCS/Item:", size=6)

    # Republic / DOF / BIR centred
    cx = x0 + W / 2
    _text(c, cx, y - 8,  "REPUBLIC OF THE PHILIPPINES",  size=7, bold=True,  align="C")
    _text(c, cx, y - 17, "DEPARTMENT OF FINANCE",         size=7,              align="C")
    _text(c, cx, y - 26, "BUREAU OF INTERNAL REVENUE",   size=7,              align="C")
    y -= 32

    # Form-number box (left) + title (centre-right)
    fn_w, fn_h = 90, 28
    _box(c, x0, y - fn_h, fn_w, fn_h, lw=0.6)
    _text(c, x0 + 4, y - 9,  "BIR Form No.",          size=6)
    _text(c, x0 + 4, y - 21, "1604-C",                size=17, bold=True)
    _text(c, x0 + 4, y - 27, "January 2018 (ENCS)  Page 1", size=5.5)

    tx = x0 + fn_w + 4
    tw = W - fn_w - 4
    _text(c, tx + tw / 2, y - 9,
          "Annual Information Return",
          size=11, bold=True, align="C")
    _text(c, tx + tw / 2, y - 19,
          "of Income Taxes Withheld on Compensation",
          size=9, bold=True, align="C")
    _text(c, tx + tw / 2, y - 27,
          "Enter all required information in CAPITAL LETTERS using BLACK ink.",
          size=5.5, align="C")
    y -= fn_h

    # ── Fields 1-3 ────────────────────────────────────────────────────────────
    f1w, f2w = 118, 200
    f3w = W - f1w - f2w
    _box(c, x0,           y - RH, f1w, RH)
    _box(c, x0 + f1w,     y - RH, f2w, RH)
    _box(c, x0 + f1w + f2w, y - RH, f3w, RH)

    _text(c, x0 + 3, y - 10, "1  For the Year (20YY)", size=7)
    yr = str(year)
    for i, d in enumerate(yr):
        bx = x0 + 76 + i * 11
        _box(c, bx, y - RH + 3, 9, RH - 6)
        _text(c, bx + 2, y - 11, d, size=8, bold=True)

    _text(c, x0 + f1w + 4, y - 7,  "2  Amended Return?", size=7)
    _box(c, x0 + f1w + 82,  y - RH + 5, 7, 7)
    _text(c, x0 + f1w + 91, y - 10, "Yes", size=7)
    _box(c, x0 + f1w + 110, y - RH + 5, 7, 7)
    _text(c, x0 + f1w + 119, y - 10, "No",  size=7)

    _text(c, x0 + f1w + f2w + 4, y - 10, "3  Number of Sheet/s Attached", size=7)
    y -= RH

    # ── Part I header ─────────────────────────────────────────────────────────
    _fill(c, x0, y - SH, W, SH, HDR_BG)
    _box(c,  x0, y - SH, W, SH, lw=0.6)
    _text(c, x0 + W / 2, y - SH + 3,
          "Part I - Background Information", size=8, bold=True, align="C")
    y -= SH

    # ── Field 4 (TIN) + 5 (RDO) ───────────────────────────────────────────────
    f4w, f5w = 325, W - 325
    _box(c, x0,        y - RH, f4w, RH)
    _box(c, x0 + f4w,  y - RH, f5w, RH)
    _text(c, x0 + 3, y - 5,  "4  Taxpayer Identification Number (TIN)", size=6.5)
    tin_raw = _safe(company.get("bir_tin", "")).replace("-", "").replace(" ", "")
    parts   = [tin_raw[i:i+3] for i in range(0, min(12, len(tin_raw)), 3)]
    _text(c, x0 + 148, y - 13, "  /  ".join(parts), size=8, bold=True)
    _text(c, x0 + f4w + 4, y - 5,  "5  RDO Code", size=6.5)
    _text(c, x0 + f4w + 52, y - 13, _safe(company.get("rdo_code")), size=8, bold=True)
    y -= RH

    # ── Field 6 (Name) ────────────────────────────────────────────────────────
    _box(c, x0, y - RH, W, RH)
    _text(c, x0 + 3, y - 5,  "6  Withholding Agent's Name", size=6.5)
    _text(c, x0 + 6, y - 13, _safe(company.get("name")), size=8, bold=True, clip_w=W - 12)
    y -= RH

    # ── Field 7 (Address) — 2 rows ────────────────────────────────────────────
    addr = _safe(company.get("address"))
    for i in range(2):
        _box(c, x0, y - RH, W, RH)
        if i == 0:
            _text(c, x0 + 3, y - 5,  "7  Registered Address", size=6.5)
            _text(c, x0 + 6, y - 13, addr, size=8, bold=True, clip_w=W - 12)
        y -= RH

    # ── Field 7A (ZIP) ────────────────────────────────────────────────────────
    zipw = 125
    _box(c, x0,        y - RH, W - zipw, RH)
    _box(c, x0 + W - zipw, y - RH, zipw, RH)
    _text(c, x0 + W - zipw + 4, y - 5,  "7A  ZIP Code", size=6.5)
    _text(c, x0 + W - zipw + 55, y - 13,
          _safe(company.get("zip_code")), size=8, bold=True)
    y -= RH

    # ── Field 8 (Category) + 8A ───────────────────────────────────────────────
    _box(c, x0, y - RH, W, RH)
    _text(c, x0 + 3, y - 10, "8  Category of Withholding Agent", size=7)
    _fill(c, x0 + 122, y - RH + 5, 7, 7, colors.black)   # private checked
    _box(c,  x0 + 122, y - RH + 5, 7, 7)
    _text(c, x0 + 131, y - 10, "Private", size=7)
    _box(c,  x0 + 172, y - RH + 5, 7, 7)
    _text(c, x0 + 181, y - 10, "Government", size=7)
    _text(c, x0 + 248, y - 10, "8A  If private, top withholding agent?", size=7)
    _box(c,  x0 + 398, y - RH + 5, 7, 7)
    _text(c, x0 + 407, y - 10, "Yes", size=7)
    _box(c,  x0 + 425, y - RH + 5, 7, 7)
    _text(c, x0 + 434, y - 10, "No",  size=7)
    y -= RH

    # ── Fields 9-10 (Contact / Email) ─────────────────────────────────────────
    hw = W / 2
    _box(c, x0,      y - RH, hw,     RH)
    _box(c, x0 + hw, y - RH, W - hw, RH)
    _text(c, x0 + 3,       y - 5,  "9  Contact Number",  size=6.5)
    _text(c, x0 + 6,       y - 13, _safe(company.get("contact_number")), size=8, bold=True)
    _text(c, x0 + hw + 4,  y - 5,  "10  Email Address",  size=6.5)
    _text(c, x0 + hw + 7,  y - 13, _safe(company.get("email")), size=8, bold=True,
          clip_w=W - hw - 10)
    y -= RH

    # ── Field 11 (overwithholding) + 11A ──────────────────────────────────────
    f11w = round(W * 0.66)
    _box(c, x0,       y - RH, f11w,    RH)
    _box(c, x0 + f11w, y - RH, W - f11w, RH)
    _text(c, x0 + 3, y - 5,
          "11  In case of overwithholding/overremittance after year-end adjustments,", size=6)
    _text(c, x0 + 3, y - 12,
          "      have you released the refund/s to your employee/s?", size=6)
    _box(c,  x0 + 300, y - RH + 5, 7, 7)
    _text(c, x0 + 309, y - 10, "Yes", size=7)
    _box(c,  x0 + 326, y - RH + 5, 7, 7)
    _text(c, x0 + 335, y - 10, "No",  size=7)
    _text(c, x0 + f11w + 4, y - 5,  "11A  If Yes, specify date",    size=6)
    _text(c, x0 + f11w + 4, y - 12, "       of refund (MM/DD/YYYY)", size=6)
    y -= RH

    # ── Fields 12-13 ──────────────────────────────────────────────────────────
    f12w = round(W * 0.60)
    _box(c, x0,       y - RH, f12w,    RH)
    _box(c, x0 + f12w, y - RH, W - f12w, RH)
    _text(c, x0 + 3, y - 5,
          "12  Total amount of overremittance on Tax withheld under compensation", size=6)
    _text(c, x0 + f12w + 4, y - 9,
          "13  Month of First Crediting of Overremittance (MM)", size=6)
    y -= RH

    # ── Part II header ────────────────────────────────────────────────────────
    _fill(c, x0, y - SH, W, SH, HDR_BG)
    _box(c,  x0, y - SH, W, SH, lw=0.6)
    _text(c, x0 + W / 2, y - SH + 3,
          "Part II - Summary of Remittances per BIR Form No. 1601-C",
          size=8, bold=True, align="C")
    y -= SH

    # ── Part II two-section table ─────────────────────────────────────────────
    # Left  : Month | Date | Bank | TRA/eROR | Taxes Withheld
    # Right : Month | Adjustment | Penalties | Total Amount Remitted
    GAP   = 6
    L1_WS = [40, 50, 62, 62, 55]          # left section col widths
    L1_W  = sum(L1_WS)                    # 269
    L2_W  = W - L1_W - GAP                # ≈ 284.28
    L2_WS = [40, 56, 56, L2_W - 40 - 56 - 56]

    # Cumulative x positions
    L1_X = [x0]
    for w in L1_WS[:-1]:
        L1_X.append(L1_X[-1] + w)
    L2_X = [x0 + L1_W + GAP]
    for w in L2_WS[:-1]:
        L2_X.append(L2_X[-1] + w)

    HDR_H = 24      # column-header row height
    MR_H  = 13      # month row height

    # Left header row
    _fill(c, x0,        y - HDR_H, L1_W, HDR_H, GRAY_BG)
    _box(c,  x0,        y - HDR_H, L1_W, HDR_H)
    hdrs1 = ["Month", "Date of\nRemittance\n(MM/DD/YYYY)",
             "Drawee Bank/\nBank Code/\nAgency",
             "TRA/eROR/\neAR Number", "Taxes\nWithheld"]
    for i, (hx, hw2, hl) in enumerate(zip(L1_X, L1_WS, hdrs1)):
        if i > 0:
            _vline(c, hx, y, y - HDR_H)
        for li, ln in enumerate(hl.split("\n")):
            _text(c, hx + hw2 / 2, y - 7 - li * 7, ln, size=6, align="C")

    # Right header row
    _fill(c, L2_X[0], y - HDR_H, L2_W, HDR_H, GRAY_BG)
    _box(c,  L2_X[0], y - HDR_H, L2_W, HDR_H)
    _text(c, L2_X[0] + L2_W / 2, y - 8,
          "Continuation of Part II", size=7, bold=True, align="C")
    hdrs2 = ["Month", "Adjustment", "Penalties", "Total Amount\nRemitted"]
    for i, (hx, hw2, hl) in enumerate(zip(L2_X, L2_WS, hdrs2)):
        if i > 0:
            _vline(c, hx, y - HDR_H / 2, y - HDR_H)
        for li, ln in enumerate(hl.split("\n")):
            _text(c, hx + hw2 / 2, y - HDR_H / 2 - 5 - li * 7, ln, size=6, align="C")
    y -= HDR_H

    # Month rows
    total_tw = 0
    for mi, month in enumerate(MONTHS):
        tw  = monthly_taxes.get(mi + 1, 0)
        total_tw += tw
        alt = LIGHT_BG if mi % 2 == 1 else colors.white

        # Left section
        if alt != colors.white:
            _fill(c, x0, y - MR_H, L1_W, MR_H, alt)
        _box(c, x0, y - MR_H, L1_W, MR_H)
        for i, (hx, hw2) in enumerate(zip(L1_X, L1_WS)):
            if i > 0:
                _vline(c, hx, y, y - MR_H)
        _text(c, L1_X[0] + L1_WS[0] / 2, y - MR_H + 4, month, size=7, align="C")
        if tw:
            _text(c, L1_X[4] + L1_WS[4] - 3, y - MR_H + 4,
                  _p(tw, False), size=7, align="R")

        # Right section
        if alt != colors.white:
            _fill(c, L2_X[0], y - MR_H, L2_W, MR_H, alt)
        _box(c, L2_X[0], y - MR_H, L2_W, MR_H)
        for i, (hx, hw2) in enumerate(zip(L2_X, L2_WS)):
            if i > 0:
                _vline(c, hx, y, y - MR_H)
        _text(c, L2_X[0] + L2_WS[0] / 2, y - MR_H + 4, month, size=7, align="C")
        y -= MR_H

    # TOTAL row
    _fill(c, x0,      y - MR_H, L1_W, MR_H, HDR_BG)
    _box(c,  x0,      y - MR_H, L1_W, MR_H)
    for hx in L1_X[1:]:
        _vline(c, hx, y, y - MR_H)
    _text(c, L1_X[0] + L1_WS[0] / 2, y - MR_H + 4, "TOTAL", size=7, bold=True, align="C")
    _text(c, L1_X[4] + L1_WS[4] - 3, y - MR_H + 4,
          _p(total_tw, False), size=7, bold=True, align="R")

    _fill(c, L2_X[0], y - MR_H, L2_W, MR_H, HDR_BG)
    _box(c,  L2_X[0], y - MR_H, L2_W, MR_H)
    for hx in L2_X[1:]:
        _vline(c, hx, y, y - MR_H)
    _text(c, L2_X[0] + L2_WS[0] / 2, y - MR_H + 4, "TOTAL", size=7, bold=True, align="C")
    y -= MR_H

    # ── Perjury statement + signature block ───────────────────────────────────
    y -= 6
    perjury = (
        "I/We declare under the penalties of perjury that this return, and all its "
        "attachments, has been made in good faith, verified by me/us, and to the best of "
        "my/our knowledge and belief, is true and correct, pursuant to the provisions of "
        "the National Internal Revenue Code, as amended, and the regulations issued under "
        "authority thereof."
    )
    for ln in simpleSplit(perjury, "Helvetica", 5.5, W - 6)[:3]:
        _text(c, x0 + 3, y, ln, size=5.5)
        y -= 7

    y -= 4
    sig_h = 38
    sig_lw = W / 2 - 5
    for bx, bw2, label in [
        (x0,          sig_lw, "For Individual:"),
        (x0 + sig_lw + 10, W - sig_lw - 10, "For Non-Individual:"),
    ]:
        _text(c, bx, y, label, size=7, bold=True)
        _box(c, bx, y - sig_h, bw2, sig_h)
        _hline(c, bx, y - sig_h + 12, bx + bw2)
        sub = ("Signature over Printed Name of Taxpayer/Authorized Representative/Tax Agent"
               if "Individual:" == label else
               "Signature over Printed Name of President/VP/Authorized Officer")
        _text(c, bx + bw2 / 2, y - sig_h + 4, sub, size=4.5, align="C")

    # Accreditation row
    acc_y = MB + 4
    for bx2, bw2, lbl in [
        (x0,               W * 0.40, "Tax Agent Accreditation No./Attorney's Roll No."),
        (x0 + W * 0.40,    W * 0.30, "Date of Issue (MM/DD/YYYY)"),
        (x0 + W * 0.70,    W * 0.30, "Date of Expiry (MM/DD/YYYY)"),
    ]:
        _box(c, bx2, acc_y, bw2, 11)
        _text(c, bx2 + 3, acc_y + 2, lbl, size=5.5)

    _text(c, x0, acc_y - 6,
          "*NOTE: The BIR Data Privacy is in the BIR website (www.bir.gov.ph)", size=5)

    c.save()
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
#  ALPHALIST  (Annex A — Schedule 1, Landscape A4, multi-page)
# ─────────────────────────────────────────────────────────────────────────────

# Column definitions: (header_text, col_width_pt)
# Header text uses \n for line breaks inside the cell.
_ALPHA_COLS = [
    ("Seq\nNo",                14),
    ("Last Name",              68),
    ("First Name",             54),
    ("Middle\nName",           40),
    ("Stat",                   16),
    ("From\nMM/DD",            24),
    ("To\nMM/DD",              24),
    ("Gross\nComp\nIncome",    52),
    # NON-TAXABLE
    ("13th Mo\n+Ben\n(NT)",    38),
    ("De\nMini\nmis",          26),
    ("SSS/PHIC\nHDMF\n(EE)",   40),
    ("Sal\n<=250K\n(NT)",      34),
    ("Total\nNon-\nTax",       40),
    # TAXABLE
    ("Basic\nSal\n(Tax)",      40),
    ("13th Mo\nExcess\n(Tax)", 36),
    ("Other\nComp\n(Tax)",     40),
    ("Total\nTaxable",         40),
    # TAX
    ("Tax\nWith-\nheld",       42),
    ("Sub\nFil",               20),
]
# Total col width: 14+68+54+40+16+24+24+52+38+26+40+34+40+40+36+40+40+42+20 = 698pt
# Landscape BODY_W ≈ 812pt  → 114pt of slack (use for margins)

# Landscape page constants
_LPW, _LPH   = landscape(A4)    # 841.89 × 595.28
_LML, _LMR   = 22, 22
_LMT, _LMB   = 14, 14
_LBODY_W     = _LPW - _LML - _LMR    # 797.89
_LBODY_TOP   = _LPH - _LMT            # 581.28

_COL_WS  = [w for _, w in _ALPHA_COLS]
_COL_HDR = [h for h, _ in _ALPHA_COLS]
_TOTAL_W = sum(_COL_WS)               # 698pt

# Centre the table in the available body width
_TABLE_X = _LML + (_LBODY_W - _TOTAL_W) / 2   # ≈ 71.9 — nicely centred

# Col X positions
def _col_x_positions():
    xs = [_TABLE_X]
    for w in _COL_WS[:-1]:
        xs.append(xs[-1] + w)
    return xs

_COL_XS = _col_x_positions()

_HDR_ROW_H = 30     # column-header area height
_DATA_ROW_H = 11    # data row height
_PAGE_HDR_H = 28    # top-of-page company / form info area
_SCHED_HDR_H = 12   # "Schedule 1 - Alphalist..." bar height


def _alpha_page_header(c, company, year, page_num, total_pages):
    """Draw the per-page header (company info + form title)."""
    y = _LBODY_TOP
    cx = _LML + _LBODY_W / 2

    _text(c, cx, y - 7,
          "ALPHABETICAL LIST OF EMPLOYEES FROM WHOM TAXES WERE WITHHELD",
          size=8, bold=True, align="C")
    _text(c, cx, y - 15, "Annex A  -  BIR Form 1604-C", size=7, align="C")
    _text(c, _LML, y - 7, f"TIN: {_safe(company.get('bir_tin'))}", size=7)
    _text(c, _LML, y - 15,
          f"Withholding Agent: {_safe(company.get('name'))}", size=7)
    _text(c, _LML + _LBODY_W - 3, y - 7,
          f"Tax Year: {year}", size=7, align="R")
    _text(c, _LML + _LBODY_W - 3, y - 15,
          f"Page {page_num} of {total_pages}", size=7, align="R")
    return y - _PAGE_HDR_H


def _alpha_schedule_header(c, y, label):
    """Draw the Schedule N coloured bar."""
    _fill(c, _TABLE_X, y - _SCHED_HDR_H, _TOTAL_W, _SCHED_HDR_H, BIR_BLUE)
    _text(c, _TABLE_X + _TOTAL_W / 2, y - _SCHED_HDR_H + 4,
          label, size=7, bold=True, align="C", col=colors.white)
    return y - _SCHED_HDR_H


def _alpha_col_headers(c, y):
    """Draw the column-header row and return new y."""
    _fill(c, _TABLE_X, y - _HDR_ROW_H, _TOTAL_W, _HDR_ROW_H, GRAY_BG)
    _box(c,  _TABLE_X, y - _HDR_ROW_H, _TOTAL_W, _HDR_ROW_H)
    for i, (cx2, cw, hdr) in enumerate(zip(_COL_XS, _COL_WS, _COL_HDR)):
        if i > 0:
            _vline(c, cx2, y, y - _HDR_ROW_H)
        lines = hdr.split("\n")
        lh = _HDR_ROW_H / (len(lines) + 0.5)
        for li, ln in enumerate(lines):
            _text(c, cx2 + cw / 2, y - 5 - li * lh, ln, size=5.5, align="C")
    return y - _HDR_ROW_H


def _alpha_data_row(c, y, row_data: list, shade: bool):
    """Draw one data row. row_data must have same length as _ALPHA_COLS."""
    if shade:
        _fill(c, _TABLE_X, y - _DATA_ROW_H, _TOTAL_W, _DATA_ROW_H, LIGHT_BG)
    _box(c, _TABLE_X, y - _DATA_ROW_H, _TOTAL_W, _DATA_ROW_H)
    for i, (cx2, cw, val) in enumerate(zip(_COL_XS, _COL_WS, row_data)):
        if i > 0:
            _vline(c, cx2, y, y - _DATA_ROW_H)
        s = str(val) if val is not None else ""
        # Numeric columns (index >= 7) right-aligned; others left-aligned
        if i >= 7 and i != 18:
            _text(c, cx2 + cw - 2, y - _DATA_ROW_H + 3, s, size=6, align="R", clip_w=cw - 2)
        elif i == 0:   # seq no — centre
            _text(c, cx2 + cw / 2, y - _DATA_ROW_H + 3, s, size=6, align="C")
        else:
            _text(c, cx2 + 2, y - _DATA_ROW_H + 3, s, size=6, clip_w=cw - 3)


def _alpha_total_row(c, y, totals: dict):
    """Draw the TOTAL row at end of schedule."""
    _fill(c, _TABLE_X, y - _DATA_ROW_H, _TOTAL_W, _DATA_ROW_H, TOT_BG)
    _box(c,  _TABLE_X, y - _DATA_ROW_H, _TOTAL_W, _DATA_ROW_H)
    for i, (cx2, cw) in enumerate(zip(_COL_XS, _COL_WS)):
        if i > 0:
            _vline(c, cx2, y, y - _DATA_ROW_H)
    _text(c, _TABLE_X + _COL_WS[0] + 3, y - _DATA_ROW_H + 3,
          "TOTALS", size=6.5, bold=True)
    # sum columns 7-17 (index 7..17)
    for col_idx in range(7, 18):
        key = f"c{col_idx}"
        val = totals.get(key, 0)
        if val:
            cx2 = _COL_XS[col_idx]
            cw  = _COL_WS[col_idx]
            _text(c, cx2 + cw - 2, y - _DATA_ROW_H + 3,
                  _p(val, False), size=6, bold=True, align="R")


def _compute_employee_row(seq_no: int, emp: dict, agg: dict) -> tuple:
    """
    Return (row_data_list, totals_dict_contribution).

    row_data has 19 elements matching _ALPHA_COLS.
    totals_dict has keys c7..c17 in centavos.
    """
    # ── Non-taxable amounts ────────────────────────────────────────────────────
    nt_13th      = min(agg.get("thirteenth_month_accrual", 0), _13TH_THRESHOLD)
    nt_deminis   = agg.get("allowances_nontaxable", 0)
    nt_statutory = (
        agg.get("sss_employee", 0)
        + agg.get("philhealth_employee", 0)
        + agg.get("pagibig_employee", 0)
    )
    nt_total = nt_13th + nt_deminis + nt_statutory

    # ── Taxable amounts ────────────────────────────────────────────────────────
    tx_13th   = max(0, agg.get("thirteenth_month_accrual", 0) - _13TH_THRESHOLD)
    tx_other  = (
        agg.get("overtime_pay", 0)
        + agg.get("holiday_pay", 0)
        + agg.get("night_differential", 0)
    )
    tx_basic  = (
        agg.get("basic_pay", 0)
        - nt_statutory
        + agg.get("allowances_taxable", 0)
        + agg.get("commission", 0)
    )
    tx_total  = tx_basic + tx_13th + tx_other

    gross        = agg.get("gross_pay", 0)
    tax_withheld = agg.get("withholding_tax", 0)

    # ── Row data ──────────────────────────────────────────────────────────────
    row = [
        seq_no,
        (emp.get("last_name") or "").upper(),
        (emp.get("first_name") or "").upper(),
        (emp.get("middle_name") or "").upper(),
        "R",                              # status: Regular (default)
        "01/01",                          # from (default full year)
        "12/31",                          # to   (default full year)
        _p(gross,        blank_zero=False),
        # non-taxable
        _p(nt_13th,      blank_zero=True),
        _p(nt_deminis,   blank_zero=True),
        _p(nt_statutory, blank_zero=True),
        "",                               # Sal <=250K (MWE only)
        _p(nt_total,     blank_zero=False),
        # taxable
        _p(tx_basic,     blank_zero=True),
        _p(tx_13th,      blank_zero=True),
        _p(tx_other,     blank_zero=True),
        _p(tx_total,     blank_zero=False),
        # tax
        _p(tax_withheld, blank_zero=False),
        "Y" if tax_withheld > 0 else "",  # substituted filing indicator
    ]

    contrib = {
        "c7":  gross,
        "c8":  nt_13th,
        "c9":  nt_deminis,
        "c10": nt_statutory,
        "c11": 0,
        "c12": nt_total,
        "c13": tx_basic,
        "c14": tx_13th,
        "c15": tx_other,
        "c16": tx_total,
        "c17": tax_withheld,
    }
    return row, contrib


def generate_bir1604c_alphalist(
    company: dict,
    employees: list[dict],
    annual_entries: dict,
    year: int,
) -> bytes:
    """
    Generate 1604-C Alphalist (Annex A, Schedule 1).
    Employees should be pre-sorted alphabetically by last_name.
    Only employees present in annual_entries are included.
    """
    buf = io.BytesIO()
    c   = canvas.Canvas(buf, pagesize=landscape(A4))
    c.setTitle(f"BIR Form 1604-C Alphalist ({year})")

    # Filter to employees that have payroll data, maintain sort order
    emp_with_data = [e for e in employees if e["id"] in annual_entries]

    # Calculate total pages needed
    # First page: header + schedule-bar + col-headers, then rows
    usable_first = (_LBODY_TOP - _PAGE_HDR_H - _SCHED_HDR_H - _HDR_ROW_H
                    - _DATA_ROW_H - _LMB)    # reserve 1 row for TOTAL
    rows_first   = max(1, int(usable_first / _DATA_ROW_H))

    usable_next  = (_LBODY_TOP - _PAGE_HDR_H - _HDR_ROW_H
                    - _DATA_ROW_H - _LMB)
    rows_per_next = max(1, int(usable_next / _DATA_ROW_H))

    n = len(emp_with_data)
    if n <= rows_first:
        total_pages = 1
    else:
        total_pages = 1 + -((-(n - rows_first)) // rows_per_next)

    # ── Draw pages ────────────────────────────────────────────────────────────
    page_num   = 1
    emp_idx    = 0
    running_totals = {f"c{i}": 0 for i in range(7, 18)}

    while emp_idx < n or page_num == 1:
        y = _alpha_page_header(c, company, year, page_num, total_pages)

        if page_num == 1:
            y = _alpha_schedule_header(
                c, y,
                "Schedule 1 - Alphalist of Employees "
                "(Declared and Certified using BIR Form No. 2316)"
            )

        y = _alpha_col_headers(c, y)

        # How many rows fit on this page?
        rows_available = int((y - _LMB - _DATA_ROW_H) / _DATA_ROW_H)
        # Reserve last row for TOTAL on final page
        is_last_page = (emp_idx + rows_available) >= n
        if is_last_page:
            rows_available = min(rows_available, n - emp_idx)

        # Draw data rows
        for ri in range(rows_available):
            if emp_idx >= n:
                break
            emp = emp_with_data[emp_idx]
            agg = annual_entries[emp["id"]]
            row_data, contrib = _compute_employee_row(emp_idx + 1, emp, agg)
            _alpha_data_row(c, y, row_data, shade=(emp_idx % 2 == 1))
            for k, v in contrib.items():
                running_totals[k] += v
            y -= _DATA_ROW_H
            emp_idx += 1

        # Draw TOTAL on the last page
        if emp_idx >= n:
            _alpha_total_row(c, y, running_totals)
            y -= _DATA_ROW_H
            break

        c.showPage()
        page_num += 1

    # ── Legend / footer on last page ─────────────────────────────────────────
    legend_y = _LMB + 20
    _text(c, _LML, legend_y + 10,
          "Status codes:  R = Regular   C = Casual   CP = Contractual/Project-Based   "
          "S = Seasonal   P = Probationary   AL = Apprentices/Learners",
          size=5.5)
    _text(c, _LML, legend_y + 3,
          "Sub Fil: Substituted Filing?  Y = Yes (qualifies)   "
          "Note: 13th-month non-taxable threshold = PHP 90,000",
          size=5.5)

    c.save()
    return buf.getvalue()
