# Build a Personal Daily Tech Digest Agent
## A Hands-On Workshop with Google's Managed Agents API

**Duration:** 3 hours
**Level:** Intermediate Python developers
**What you'll build:** A managed agent that fetches news from sources you choose, summarizes them in a voice you design, and produces a polished daily-brief PDF.

**What you'll learn:**
- The two modes of Managed Agents — *inline* and *saved*
- How `AGENTS.md` and `SKILL.md` files shape agent behavior without orchestration code
- Streaming, multi-turn sessions, and environment reuse
- When this stack pays off and — just as important — when it doesn't

---

## Prerequisites

1. Python 3.10+
2. A Gemini API key from [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
3. ~$5 of API credit per participant (each run is roughly $0.30–$1)
4. Install the SDK:

```bash
pip install -U google-genai requests
export GEMINI_API_KEY="your-key-here"
```

Sanity-check:

```python
from google import genai
client = genai.Client()
print("OK")
```

---

## The arc

| Stage | Teaches | Time |
|---|---|---|
| 1. Hello, Agent | Single inline call | 20 min |
| 2. Multi-source digest | The autonomous loop, streaming | 30 min |
| 3. Add a voice | `system_instruction` | 20 min |
| 4. Generate a PDF | Skills via `SKILL.md` | 40 min |
| 5. Save it | `agents.create()` — production pattern | 30 min |
| 6. Multi-turn refinement | `previous_interaction_id`, env reuse | 20 min |
| 7. Stretch goals | Open-ended | 20+ min |

---

## Stage 1 — Hello, Agent

**Goal:** Make one call. See the loop happen.

```python
# stage1_hello.py
from google import genai

client = genai.Client()

interaction = client.interactions.create(
    agent="antigravity-preview-05-2026",
    input="Fetch news.ycombinator.com and list the top 3 story titles.",
    environment="remote",
)

print(interaction.output_text)
print(f"\nEnvironment ID: {interaction.environment_id}")
print(f"Interaction ID: {interaction.id}")
```

Run it. Wait 30–90 seconds.

**Teaching moments:**
- You never told the agent *how* to fetch — it picked the tool itself (URL context or code execution).
- It's running in a real Ubuntu sandbox right now. If you'd asked it to install a package, it could.
- Cost: ~$0.20.

**Common pitfalls:**
- "Permission denied" → check `GEMINI_API_KEY` is exported in the same shell.
- Output looks empty → use streaming (next stage).

---

## Stage 2 — Multi-source digest with streaming

**Goal:** Hand the agent multiple sources. Watch it plan and act.

```python
# stage2_stream.py
from google import genai

client = genai.Client()

sources = [
    "https://news.ycombinator.com",
    "https://techcrunch.com",
    "https://www.theverge.com",
]

prompt = f"""
You're building a daily tech digest.

For each source below:
{chr(10).join(f"- {s}" for s in sources)}

1. Fetch the homepage.
2. Pull the top 3 headlines.
3. Summarize each in one sentence.
4. Group output by source.
"""

stream = client.interactions.create(
    agent="antigravity-preview-05-2026",
    input=prompt,
    environment="remote",
    stream=True,
)

for event in stream:
    print(event)
```

**Teaching moments:**
- The stream shows reasoning steps, tool calls, observations. Pause it and read a step aloud — that's the agent loop made visible.
- Token count will land in the 100k–500k range. This is Google's "research and information synthesis" cost band.
- Cost: ~$0.50.

**Demo tip:** Run this side-by-side with Stage 1's non-streaming version. The "what is the agent actually doing in there" question gets answered the moment they see the stream.

---

## Stage 3 — Add a voice

**Goal:** Same task, different personality.

```python
# stage3_voice.py
EDITORIAL_VOICE = """
You are the editor of a sharp, slightly skeptical tech newsletter.
Short sentences. Funny but never silly.
Highlight what matters. Call out hype.
Always finish with a 'Skip This' callout — one story that's just noise.
"""

interaction = client.interactions.create(
    agent="antigravity-preview-05-2026",
    input=prompt,                        # from Stage 2
    system_instruction=EDITORIAL_VOICE,
    environment="remote",
)
print(interaction.output_text)
```

**Demo:** Run with two different voices (e.g., "skeptical editor" vs. "earnest researcher") on the same prompt. The contrast lands immediately. Attendees realize how much personality lives in the system instruction.

---

## Stage 4 — Generate a PDF with a `SKILL.md`

**This is the showcase stage. Plan an extra 10 minutes here.**

**Goal:** Mount a markdown skill file. Watch the agent discover it, follow it, and produce a real PDF.

```python
# stage4_pdf.py
from google import genai

client = genai.Client()

PDF_SKILL = """---
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

EDITORIAL_VOICE = """..."""  # from Stage 3

interaction = client.interactions.create(
    agent="antigravity-preview-05-2026",
    input="Build today's digest as a PDF. Sources: HN, Verge, TechCrunch.",
    system_instruction=EDITORIAL_VOICE,
    environment={
        "type": "remote",
        "sources": [
            {
                "type": "inline",
                "target": ".agents/skills/digest-pdf/SKILL.md",
                "content": PDF_SKILL,
            }
        ],
    },
)

print(interaction.output_text)
print(f"\nEnvironment ID (save for Stage 6): {interaction.environment_id}")
```

**Then download the PDF:**

```python
# download_pdf.py
import os, requests, tarfile

env_id = "PASTE_FROM_OUTPUT"
api_key = os.environ["GEMINI_API_KEY"]

r = requests.get(
    f"https://generativelanguage.googleapis.com/v1beta/files/environment-{env_id}:download",
    params={"alt": "media"},
    headers={"x-goog-api-key": api_key},
    allow_redirects=True,
)
open("snapshot.tar", "wb").write(r.content)

with tarfile.open("snapshot.tar") as tar:
    tar.extractall(path="./output")

print("Open ./output/workspace/digest.pdf")
```

**Teaching moments:**
- The agent read a markdown file, installed a library, wrote Python, generated the PDF, and confirmed the file exists — all from a description, no orchestration code.
- This is the "configuration as files" pitch in action.
- The same skill works in any agent. Reusable by design.

**Backup plan:** Have a pre-rendered `digest.pdf` on disk in case the live run misbehaves. The sandbox is two weeks old as of this workshop's writing.

---

## Stage 5 — Save it as a Managed Agent

**Goal:** Stop pasting the voice and the skill into every call.

```python
# stage5_save.py
from google import genai

client = genai.Client()

agent = client.agents.create(
    id="my-tech-digest",
    base_agent="antigravity-preview-05-2026",
    description="Daily tech news digest as a PDF.",
    system_instruction=EDITORIAL_VOICE,
    base_environment={
        "type": "remote",
        "sources": [
            {
                "type": "inline",
                "target": ".agents/skills/digest-pdf/SKILL.md",
                "content": PDF_SKILL,
            },
            {
                "type": "inline",
                "target": ".agents/AGENTS.md",
                "content": """
                Always include exactly 3 stories per source.
                Always include a 'Skip This' callout.
                Always finish by generating a PDF using the digest-pdf skill.
                """,
            },
        ],
    },
)

print(f"Saved: {agent.id}")
```

Now invoke it with six lines instead of thirty:

```python
result = client.interactions.create(
    agent="my-tech-digest",
    input="Today's digest. Sources: HN, Verge, TechCrunch.",
    environment="remote",
)
print(result.output_text)
```

**Teaching moments:**
- Each invocation forks a fresh sandbox from the saved base.
- This is the production pattern. Inline mode is for iteration; saved mode is for shipping.
- Iterate the agent definition by updating it (REST `PATCH` for now — SDK update isn't shipped yet).

---

## Stage 6 — Multi-turn refinement

**Goal:** Same conversation, same files, follow-up edits.

```python
# stage6_refine.py
from google import genai

client = genai.Client()

# Initial run
first = client.interactions.create(
    agent="my-tech-digest",
    input="Today's digest. Sources: HN, Verge, TechCrunch.",
    environment="remote",
)

# Refine — same env, same conversation
second = client.interactions.create(
    agent="my-tech-digest",
    input="Make the AI section twice as long. Add an 'Editor's Note' at the top.",
    environment=first.environment_id,
    previous_interaction_id=first.id,
)

print(second.output_text)
```

**Teaching moments:**
- The PDF from turn 1 still exists in the sandbox. The agent can read it, edit it, regenerate it.
- Conversation context carries — you don't repeat "today's digest, sources are…"
- This unlocks the draft → review → refine workflow.

---

## Stage 7 — Stretch goals

Pick one based on your interests. Times are rough.

**Lighter weight:**
- Add a `--topics` CLI flag that biases the digest toward specific areas ("AI, robotics, climate tech").
- Offer two voices via a flag and let the agent pick based on the day of the week.

**Medium:**
- Email the PDF to yourself with `smtplib` once the agent finishes.
- Add a second `SKILL.md` that also generates a plain-text email summary alongside the PDF.
- Mount a GCS bucket containing your favorite RSS feed URLs as the source list.

**Heavy:**
- Schedule the agent daily via cron, hitting your saved agent each morning.
- Add a feedback loop: store thumbs-up/down ratings in a JSON file the agent reads next time to learn your taste.
- Build a TUI that renders the agent's reasoning stream as it works (with `rich` or `textual`).

---

## Cost cheat sheet

| Stage | Cost / run |
|---|---|
| 1 — Single fetch | ~$0.20 |
| 2 — Multi-source | ~$0.50 |
| 3 — Voice | ~$0.50 |
| 4 — PDF | ~$0.80 |
| 5 — Saved + invoke | ~$0.80 |
| 6 — Refinement | ~$0.50 |

Budget ~$5 per participant including re-runs. The agent caches 50–70% of input tokens, so subsequent runs in the same environment are cheaper than the first.

---

## What this workshop deliberately does NOT teach

Be honest with attendees:

- This isn't a replacement for a real RSS reader. Per-call costs make daily personal use viable; high-frequency processing isn't.
- Output is non-deterministic. Two runs of the same prompt produce different digests.
- The Managed Agents API is in Public Preview. Schemas may change.
- Token usage is largely opaque to the caller. Add monitoring before any production deployment.
- This is *not* a tutorial in agentic security. Network defaults, credential handling, and least-privilege design are separate sessions.

---

## Instructor notes

- **Stage 4 is the showpiece.** Give it extra air. The "I handed it a markdown file and it built a PDF" moment is the entire pitch of the product.
- **Bring a backup `digest.pdf`** in case the live run hiccups.
- **Don't promise timings.** Same prompt can take 30 seconds or 3 minutes. Use the variance as a teaching moment about agentic latency.
- **Encourage personalization in Stage 7.** The best workshop projects are the ones attendees keep using after the workshop. Aim for "they have a working PDF in their inbox by next morning."
- **Open a side channel for questions during runs.** A 90-second run is too short to context-switch but too long to wait silently. Discord/Slack channel works well.

---

## Reference links

- Managed Agents Quickstart — https://ai.google.dev/gemini-api/docs/managed-agents-quickstart
- Antigravity Agent docs — https://ai.google.dev/gemini-api/docs/antigravity-agent
- Building custom agents — https://ai.google.dev/gemini-api/docs/custom-agents
- Environments — https://ai.google.dev/gemini-api/docs/agent-environment
- Pricing — https://ai.google.dev/gemini-api/docs/pricing
