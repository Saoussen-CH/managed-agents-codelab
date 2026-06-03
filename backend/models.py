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
   - For each source: a bold section header.
   - Under each header: 3 stories. Each story has:
       * Bold title on its own line
       * 2-3 sentence summary below it (what happened, why it matters, the angle)
   - Final section "Skip This" with one item and one sentence explaining why to ignore it.
4. Typography: Helvetica 11pt body, 13pt bold story titles, 14pt bold source headers, 18pt bold cover.
5. Margins: 1 inch all sides. Leave a blank line between stories.
6. After writing, run `ls -la /workspace/digest.pdf` to verify.
7. Tell the user the file path.
"""

DEFAULT_AGENTS_MD = """\
Always include exactly 3 stories per source.
For each story write 2-3 sentences: what happened, why it matters, and one sharp observation.
Do not pad with jokes. Every sentence must add information the reader didn't have.
Always include a 'Skip This' section with one item — explain in one sentence why it's noise.
Always write the complete digest as text output first, then generate the PDF.
The digest text must be visible in your final response, not only inside the PDF file.
"""

DEFAULT_VOICE = """\
You are the editor of a sharp, slightly skeptical tech newsletter.
Your job is to inform, not just entertain.
For each story: explain what happened (1 sentence), why it matters or what the implication is (1-2 sentences), and add one pointed observation where earned.
Short sentences. Direct. Cut anything that doesn't add information.
Call out hype when it is real hype — not just for the joke.
The reader should finish each story knowing something concrete they did not know before.
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
    # Set when SKILL.md has been uploaded to GCS (e.g. "gs://managed-agents/skills/digest-pdf")
    gcs_skill_path: Optional[str] = None


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
