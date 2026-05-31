# Daily Tech Digest

A local web app built on the [Google Managed Agents API](https://ai.google.dev/gemini-api/docs/managed-agents-quickstart). Configure your news sources and editorial voice in the browser, trigger a run, and watch a Google-hosted AI agent fetch the web, write summaries, and produce a polished PDF — live on screen. Refine the output in a follow-up turn, save your configuration as a named agent, and re-download any past PDF from history.

## Prerequisites

- Python 3.10+ and [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Node.js 18+
- A Gemini API key — [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
- ~$0.50–$1.00 per run in API credit

## Setup

```bash
# Backend
uv sync
cp .env.example .env        # then edit .env and paste your API key

# Frontend
cd frontend
npm install
```

## Run

```bash
# Terminal 1 — backend (port 8000)
uv run uvicorn backend.main:app --reload

# Terminal 2 — frontend (port 5173)
cd frontend && npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

## What you can do

| Page | What it does |
|---|---|
| **Dashboard** | Trigger a digest run, pick a saved agent, see recent runs |
| **Run view** | Watch the agent work live (streamed steps), download the PDF, refine the output |
| **Sources** | Add and remove news URLs |
| **Voice** | Edit the editorial persona (`system_instruction`) |
| **Skills** | Edit the `SKILL.md` that controls how the PDF is built |
| **Agents** | Save the current config as a named managed agent, delete old ones |
| **History** | Browse past runs, re-download any PDF |

## Cost reference

Each run calls a Google-hosted agent that autonomously fetches URLs, runs code, and writes files. Token usage varies by task complexity.

| Task | Typical cost |
|---|---|
| Fetch + summarize 3 sources | ~$0.50 |
| Fetch + summarize + PDF | ~$0.80 |
| Refinement turn | ~$0.30–$0.50 |

50–70% of input tokens are typically cached on repeated runs.

## API limitations (preview)

- Parameters `temperature`, `top_p`, `max_output_tokens` are not supported
- Tools `function_calling`, `mcp`, `computer_use` are not yet available
- Sandbox environments idle after 15 minutes, retained for 7 days
- Output is non-deterministic — two identical prompts produce different digests

## Workshop reference

The original step-by-step workshop scripts are in [`workshop/`](workshop/). They demonstrate the same API calls this app makes under the hood.
