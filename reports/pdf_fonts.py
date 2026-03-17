"""
Shared font registration for ReportLab PDF generation.

ReportLab's built-in fonts (Helvetica, Times-Roman) only cover Latin-1
(ISO-8859-1) and do NOT include the Philippine Peso sign ₱ (U+20B1).
This module registers a Unicode-capable TTF at import time so all PDF
generators can use it.

Usage:
    from reports.pdf_fonts import FONT, FONT_BOLD, peso

    # Use in TableStyle:
    ("FONTNAME", (0, 0), (-1, -1), FONT)
    ("FONTNAME", (0, 0), (-1, -1), FONT_BOLD)

    # Format amounts:
    peso(15000_00)   → "₱15,000.00"  (unicode font loaded)
                     → "PHP 15,000.00"  (fallback to Helvetica)
"""

import os
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Defaults — overwritten below if a Unicode font is found
FONT      = "Helvetica"
FONT_BOLD = "Helvetica-Bold"

def _register() -> None:
    global FONT, FONT_BOLD

    # (regular_path, bold_path, regular_name, bold_name)
    candidates = [
        # Windows (always present on any Windows install)
        ("C:/Windows/Fonts/arial.ttf",    "C:/Windows/Fonts/arialbd.ttf",
         "Arial",      "Arial-Bold"),
        # Ubuntu / Debian
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
         "DejaVuSans", "DejaVuSans-Bold"),
        # RHEL / CentOS / Fedora
        ("/usr/share/fonts/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
         "DejaVuSans", "DejaVuSans-Bold"),
        # macOS system Arial
        ("/Library/Fonts/Arial.ttf",    "/Library/Fonts/Arial Bold.ttf",
         "Arial",      "Arial-Bold"),
        ("/System/Library/Fonts/Supplemental/Arial.ttf",
         "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
         "Arial",      "Arial-Bold"),
    ]

    for reg_path, bold_path, reg_name, bold_name in candidates:
        if not os.path.exists(reg_path):
            continue
        try:
            pdfmetrics.registerFont(TTFont(reg_name, reg_path))
            FONT = reg_name
            if os.path.exists(bold_path):
                pdfmetrics.registerFont(TTFont(bold_name, bold_path))
                FONT_BOLD = bold_name
            else:
                FONT_BOLD = reg_name  # use regular as bold fallback
            return
        except Exception:
            continue  # try next candidate


_register()

_USE_PESO_SIGN = FONT != "Helvetica"


def peso(centavos: int) -> str:
    """
    Format centavos as a currency string.
    Uses ₱ prefix when a Unicode font is registered, else falls back to "PHP ".
    """
    pesos = centavos / 100
    prefix = "₱" if _USE_PESO_SIGN else "PHP "
    return f"{prefix}{pesos:,.2f}"
