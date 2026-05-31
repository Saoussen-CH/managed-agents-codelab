# Daily Tech Digest Agent

A hands-on workshop project that builds a managed agent using the [Google Managed Agents API](https://ai.google.dev/gemini-api/docs/managed-agents-quickstart). The agent fetches tech news from multiple sources, applies an editorial voice, and produces a daily-brief PDF — all from a single API call.

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) installed
- A Gemini API key from [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
- ~$5 of API credit (each full run costs $0.20–$0.80)

## Setup

```bash
uv sync
export GEMINI_API_KEY="your-key-here"
```

Verify the key works:

```bash
uv run -c "from google import genai; genai.Client(); print('OK')"
```

## Stages

Run stages in order. Each is a standalone script.

### Stage 1 — Hello, Agent (~$0.20, 30–90 sec)

```bash
uv run stage1_hello.py
```

Makes one call. Prints the top 3 HN story titles. Save the printed `Interaction ID` and `Environment ID` if you want to reuse the sandbox later.

---

### Stage 2 — Multi-source streaming (~$0.50)

```bash
uv run stage2_stream.py
```

Fetches HN, TechCrunch, and The Verge. Streams the agent's reasoning steps as they happen.

---

### Stage 3 — Editorial voice (~$0.50)

```bash
uv run stage3_voice.py
```

Same digest, but shaped by a skeptical newsletter editor persona via `system_instruction`.

---

### Stage 4 — Generate a PDF (~$0.80, 1–3 min)

```bash
uv run stage4_pdf.py
```

Mounts a `SKILL.md` that instructs the agent to build a ReportLab PDF at `/workspace/digest.pdf`. Prints the `Environment ID` at the end — copy it for the next step.

**Download the PDF:**

```bash
uv run download_pdf.py <environment_id>
# Opens at: ./output/workspace/digest.pdf
```

Keep a pre-rendered PDF as backup in case the live run takes too long.

---

### Stage 5 — Save as a managed agent (~$0.80)

```bash
uv run stage5_save.py
```

Registers `my-tech-digest` as a saved agent (bakes in the voice, skill, and AGENTS.md). Re-runnable — deletes and recreates the agent on each run. Immediately invokes the saved agent to verify.

**Manage saved agents:**

```bash
uv run manage_agents.py list
uv run manage_agents.py get my-tech-digest
uv run manage_agents.py delete my-tech-digest
```

---

### Stage 6 — Multi-turn refinement (~$0.50)

```bash
uv run stage6_refine.py
```

Requires stage 5 to have run first. Runs the digest, then refines it in a second turn using the same environment (`environment_id` + `previous_interaction_id`).

---

## Customization

All shared constants live in `config.py`:

| Constant | What it controls |
|---|---|
| `SOURCES` | News URLs fetched in stages 2–3 |
| `EDITORIAL_VOICE` | System instruction persona |
| `PDF_SKILL` | SKILL.md mounted in stages 4–5 |
| `AGENTS_MD` | Behavioral rules for the saved agent |

Edit `config.py` to change sources, persona, or PDF layout — changes propagate to all stages.

## Cost reference

| Stage | Typical cost |
|---|---|
| 1 — single fetch | ~$0.20 |
| 2–3 — multi-source / voice | ~$0.50 |
| 4–5 — PDF generation | ~$0.80 |
| 6 — refinement | ~$0.50 |

Token caching covers 50–70% of input on repeated runs in the same environment.

## Limitations (API preview)

- Output is non-deterministic — two identical prompts produce different digests
- Parameters `temperature`, `top_p`, `max_output_tokens` are not supported
- Tools `function_calling`, `mcp`, `computer_use` are not yet available
- Sandbox environments idle after 15 minutes and are retained for 7 days
