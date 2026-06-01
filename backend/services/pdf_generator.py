from __future__ import annotations
import re


def text_to_pdf(text: str, title: str = "Daily Digest") -> bytes:
    """Convert the digest output text to a PDF using fpdf2."""
    from fpdf import FPDF

    MARGIN = 25.4  # 1 inch in mm

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=MARGIN)
    pdf.add_page()
    pdf.set_margins(MARGIN, MARGIN, MARGIN)
    # Re-set position after margins
    pdf.set_xy(MARGIN, MARGIN)

    W = pdf.w - 2 * MARGIN  # usable width

    def _clean(s: str) -> str:
        s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
        s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
        return s.encode("latin-1", errors="replace").decode("latin-1")

    # Cover line
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(W, 10, _clean(title), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(6)

    for line in text.splitlines():
        stripped = line.strip()

        if stripped.startswith("### ") or stripped.startswith("## "):
            n = 4 if stripped.startswith("### ") else 3
            pdf.set_font("Helvetica", "B", 14)
            pdf.multi_cell(W, 7, _clean(stripped[n:]))
            pdf.ln(2)

        elif stripped.startswith("# "):
            pdf.set_font("Helvetica", "B", 16)
            pdf.multi_cell(W, 8, _clean(stripped[2:]))
            pdf.ln(3)

        elif stripped.startswith("---"):
            pdf.ln(2)
            y = pdf.get_y()
            pdf.set_draw_color(180, 180, 180)
            pdf.line(MARGIN, y, MARGIN + W, y)
            pdf.ln(3)

        elif stripped.startswith(("* ", "- ")):
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(W, 6, f"- {_clean(stripped[2:])}")

        elif stripped:
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(W, 6, _clean(stripped))
            pdf.ln(1)

        else:
            pdf.ln(3)

    return bytes(pdf.output())
