from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel

DEFAULT_SKILL_MD = """\
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

DEFAULT_AGENTS_MD = """\
Always include exactly 3 stories per source.
Always include a 'Skip This' callout.
Always finish by generating a PDF using the digest-pdf skill.
"""

DEFAULT_VOICE = """\
You are the editor of a sharp, slightly skeptical tech newsletter.
Short sentences. Funny but never silly.
Highlight what matters. Call out hype.
Always finish with a 'Skip This' callout — one story that's just noise.
"""

DEFAULT_SOURCES = [
    "https://news.ycombinator.com",
    "https://techcrunch.com",
    "https://www.theverge.com",
]


class RunStatus(str, Enum):
    running = "running"
    completed = "completed"
    failed = "failed"


class AppConfig(BaseModel):
    sources: list[str] = DEFAULT_SOURCES
    voice: str = DEFAULT_VOICE
    agents_md: str = DEFAULT_AGENTS_MD
    skill_md: str = DEFAULT_SKILL_MD
    # Set when the skill has been published to the Vertex AI Skill Registry
    skill_registry_name: Optional[str] = None


class RunRecord(BaseModel):
    id: str
    started_at: str
    status: RunStatus = RunStatus.running
    agent_id: Optional[str] = None
    environment_id: Optional[str] = None
    interaction_id: Optional[str] = None
    refine_interaction_id: Optional[str] = None
    output_text: Optional[str] = None
    refine_output_text: Optional[str] = None
    pdf_available: bool = False
    error: Optional[str] = None


class StartRunRequest(BaseModel):
    agent_id: Optional[str] = None


class CreateAgentRequest(BaseModel):
    id: str
    description: str = ""


class RefineRequest(BaseModel):
    message: str
