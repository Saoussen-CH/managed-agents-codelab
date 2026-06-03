"""Shared constants for all codelab stages. No TODOs here — pre-filled."""
from dotenv import load_dotenv
load_dotenv()

BASE_AGENT = "antigravity-preview-05-2026"

SOURCES = [
    "https://news.ycombinator.com",
    "https://techcrunch.com",
    "https://www.theverge.com",
]

DIGEST_PROMPT = (
    "You're building a daily tech digest.\n\n"
    "For each source below:\n"
    + "\n".join(f"- {s}" for s in SOURCES)
    + "\n\n"
    "1. Fetch the homepage.\n"
    "2. Extract the top 3 headlines.\n"
    "3. Write a 2-3 sentence summary per story: what happened, why it matters.\n"
    "4. Group output by source.\n"
    "5. Add a 'Skip This' section with one story that is noise.\n"
    "6. Output the complete written digest, then generate the PDF using the digest-pdf skill."
)

EDITORIAL_VOICE = """\
You are the editor of a sharp, slightly skeptical tech newsletter.
Your job is to inform, not just entertain.
For each story: explain what happened (1 sentence), why it matters (1-2 sentences),
and add one pointed observation where earned.
Short sentences. Direct. Cut anything that doesn't add information.
"""

AGENTS_MD = """\
Always include exactly 3 stories per source.
For each story write 2-3 sentences: what happened, why it matters, and one sharp observation.
Always include a 'Skip This' section at the end.
Always write the complete digest as text output first, then generate the PDF.
"""

PDF_SKILL_MD = """\
---
name: digest-pdf
description: Convert a tech news digest into a clean PDF.
---

# Digest PDF Skill

When the user asks for a PDF, follow this exact procedure:

1. If reportlab isn't installed, run `pip install reportlab`.
2. Build the PDF at `/workspace/digest.pdf` using ReportLab.
3. Structure:
   - Cover line: "Daily Tech Digest - {today's date}"
   - For each source: a bold section header, then 3 stories with bold title + summary.
   - Final section "Skip This" with one item.
4. Typography: Helvetica 11pt body, 14pt bold headers, 18pt bold cover.
5. Margins: 1 inch all sides.
6. After writing, run `ls -la /workspace/digest.pdf` to verify.
7. Tell the user the file path.
"""
