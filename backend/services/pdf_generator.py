from __future__ import annotations
import re

# Common unicode chars outside latin-1 → readable ASCII equivalents
_UNICODE_MAP = {
    "—": "-",   # em dash —
    "–": "-",   # en dash –
    "'": "'",   # right single quote '
    "'": "'",   # left single quote '
    "“": '"',   # left double quote "
    "”": '"',   # right double quote "
    "•": "-",   # bullet •
    "…": "...", # ellipsis …
    "é": "e",   # é
    "è": "e",   # è
    "ê": "e",   # ê
    "à": "a",   # à
    "â": "a",   # â
    "ô": "o",   # ô
    "û": "u",   # û
    "ü": "u",   # ü
    "ç": "c",   # ç
}


def _trim_to_digest(text: str) -> str:
    """
    Keep only the actual digest content.
    Strip leading agent preamble (before the first ### or ---) and
    trailing sections like '## PDF Generation' or '## Summary of Work'.
    """
    lines = text.splitlines()

    # Find where the real content starts (first section header or HR)
    start = 0
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("###") or s.startswith("---") or s.startswith("***") or s.startswith("# "):
            start = i
            break

    # Find where it ends — stop at agent meta-sections
    end = len(lines)
    for i, line in enumerate(lines[start:], start):
        s = line.strip().lower()
        if any(s.startswith(p) for p in ("## pdf", "## summary", "## turn", "## work", "## generated", "## verification")):
            end = i
            break

    return "\n".join(lines[start:end]).strip()


def text_to_pdf(text: str, title: str = "Daily Digest") -> bytes:
    """Convert the digest output text to a PDF using fpdf2."""
    from fpdf import FPDF

    MARGIN = 25.4  # 1 inch in mm

    text = _trim_to_digest(text)
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=MARGIN)
    # Set margins BEFORE add_page so fpdf2 applies them to the page layout
    pdf.set_margins(MARGIN, MARGIN, MARGIN)
    pdf.add_page()

    W = pdf.w - 2 * MARGIN  # usable width ≈ 159 mm

    def _clean(s: str) -> str:
        """Strip markdown and convert to latin-1-safe text."""
        s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
        s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
        for char, replacement in _UNICODE_MAP.items():
            s = s.replace(char, replacement)
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

        elif stripped.startswith("---") or stripped.startswith("***"):
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
