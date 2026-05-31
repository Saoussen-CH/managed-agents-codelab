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
    + "\n\n1. Fetch the homepage.\n2. Pull the top 3 headlines.\n"
    "3. Summarize each in one sentence.\n4. Group output by source."
)

EDITORIAL_VOICE = """
You are the editor of a sharp, slightly skeptical tech newsletter.
Short sentences. Funny but never silly.
Highlight what matters. Call out hype.
Always finish with a 'Skip This' callout — one story that's just noise.
"""

PDF_SKILL = """\
---
name: digest-pdf
description: Convert a tech news digest into a clean PDF.
---

# Digest PDF Skill

When the user asks for a PDF, follow this exact procedure:

1. If reportlab isn't installed, run `pip install reportlab`.
2. Build the PDF at `/workspace/digest.pdf` using ReportLab.
3. Structure:
   - Cover line: "Daily Tech Digest — {today's date}"
   - For each source: a bold header, then 3 stories (title + 1-line summary).
   - Final section titled "Skip This" with one item.
4. Typography: Helvetica 11pt body, 14pt bold source headers, 18pt bold cover.
5. Margins: 1 inch all sides.
6. After writing, run `ls -la /workspace/digest.pdf` to verify.
7. Tell the user the file path.
"""

AGENTS_MD = """\
Always include exactly 3 stories per source.
Always include a 'Skip This' callout.
Always finish by generating a PDF using the digest-pdf skill.
"""
