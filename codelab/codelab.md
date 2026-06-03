# Build a Daily Tech Digest Agent — Codelab

## What you will build

A full-stack web app powered by the **Google Managed Agents API**. One API call provisions
a Linux sandbox where an AI agent fetches real news, writes summaries in your editorial voice,
and generates a polished PDF — streamed live to your browser.

The app already exists. Your job is to wire in the **Managed Agents API calls** at the five
places marked with `TODO` comments inside the real application code.

---

## Prerequisites

- Python 3.10+ and [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Node.js 18+
- Gemini API key with billing — [aistudio.google.com/api-keys](https://aistudio.google.com/api-keys)
- ~$5 of API credit

---

## Setup

```bash
cd codelab/starter

# Install backend dependencies
uv sync

# Install frontend dependencies
cd frontend && npm install && cd ..

# Configure your API key
cp .env.example .env
# Edit .env → paste GEMINI_API_KEY=your-key
```

### Run the app

```bash
# Terminal 1 — backend
uv run uvicorn backend.main:app --reload

# Terminal 2 — frontend
cd frontend && npm run dev
```

Open http://localhost:5173. The app loads but **Run Digest** will fail until you
complete the TODOs below.

---

## Architecture

```
Browser (React)
    ↕  HTTP + Server-Sent Events (SSE)
FastAPI backend
    ↕  google-genai SDK
Google Managed Agents API
    ↕
Ubuntu sandbox (Python 3.12, Node 22, 4 CPU / 16 GB RAM)
```

The backend uses SSE to stream agent events to the browser in real time. The
`agent_client.py` file is where the Managed Agents API calls live — and where
all the TODOs are.

---

## TODO 1 — Create the client

**File:** `backend/services/agent_client.py` → `_make_client()`

The `genai.Client()` is the entry point to all Managed Agents API operations.
It reads `GEMINI_API_KEY` from the environment automatically.

```python
from google import genai

log.info("Creating Gemini API client")
_client_singleton = genai.Client()
```

The singleton pattern ensures the client is created once and reused across all requests,
avoiding the overhead of re-authenticating on every run.

**Verify:** restart the server — the `RuntimeError` should disappear from the logs.

---

## TODO 2 — Build the interaction kwargs

**File:** `backend/services/agent_client.py` → `_stream_sync()`

Every agent call uses `client.interactions.create()`. The minimum required fields are
`agent`, `input`, and `stream=True`.

```python
kwargs: dict = {
    "agent": agent_id or BASE_AGENT,
    "input": prompt,
    "stream": True,
}
```

`BASE_AGENT = "antigravity-preview-05-2026"` is the general-purpose Antigravity agent
that can browse the web, run Python, manage files, and use skills.

`stream=True` returns an iterable of events instead of waiting for the full result.
Each event carries a step label, text chunk, or tool result as it happens.

---

## TODO 3 — Add environment and system_instruction

**File:** `backend/services/agent_client.py` → `_stream_sync()`, directly below TODO 2

The `environment` parameter provisions the Linux sandbox and mounts your config files.

**Case A — Saved agent** (user selected one from the dropdown):
```python
kwargs["environment"] = "remote"
```
`"remote"` forks a fresh sandbox from the agent's `base_environment` (set when you created it).
Your AGENTS.md and SKILL.md are already baked in.

**Case B — Inline config** (no saved agent selected):
```python
if agent_id:
    kwargs["environment"] = "remote"
else:
    kwargs["system_instruction"] = config["voice"]
    kwargs["environment"] = {
        "type": "remote",
        "sources": _inline_sources(config["agents_md"], config["skill_md"]),
    }
```

`system_instruction` sets the agent's persona — the editorial voice.

`sources` mounts your files into the sandbox at startup:
- `.agents/AGENTS.md` → persistent behavioural rules the agent reads automatically
- `.agents/skills/digest-pdf/SKILL.md` → the PDF skill the agent discovers and follows

**Verify:** click **Run Digest** — you should see `⚡ Interaction started` in the stream feed.

---

## TODO 4 — Extract env_id and interaction_id from the completed event

**File:** `backend/services/agent_client.py` → `_handle_event()`, inside `elif event_type == "interaction.completed":`

When the agent finishes, the API sends an `interaction.completed` event containing
the `environment_id` (the sandbox that persisted all files) and the `id` (this
conversation turn). Both are needed for multi-turn and file download.

```python
interaction = getattr(event, "interaction", None)
if interaction:
    env_id = getattr(interaction, "environment_id", None)
    iid    = getattr(interaction, "id", None)
    usage  = getattr(interaction, "usage", None)
    if usage:
        log.info(
            "Usage — input=%s output=%s total=%s",
            getattr(usage, "total_input_tokens", "?"),
            getattr(usage, "total_output_tokens", "?"),
            getattr(usage, "total_tokens", "?"),
        )
```

The text output itself does NOT come from this event — it accumulates in `text_parts`
from `StepDelta(type="text")` events. The `interaction.completed` event carries
empty output to reduce payload size (per the API reference).

**Verify:** after a successful run, check `data/runs/<id>.json` — `environment_id`
and `interaction_id` should now be populated. The **Download PDF** button will appear.

---

## TODO 5 — Multi-turn refinement

**File:** `backend/services/agent_client.py` → `_refine_sync()`

The Interactions API tracks two independent dimensions:

| Parameter | What it resumes |
|---|---|
| `environment=environment_id` | Files, installed packages, sandbox state |
| `previous_interaction_id=interaction_id` | Conversation context, reasoning trace |

Pass both to continue exactly where the previous turn left off:

```python
stream = client.interactions.create(
    agent=agent_id or BASE_AGENT,
    input=message,
    environment=environment_id,
    previous_interaction_id=interaction_id,
    stream=True,
)
```

The agent has access to everything it did before: the scraped HTML, the generated PDF
at `/workspace/digest.pdf`, the full conversation history.

**Verify:** run a digest, then type a refinement ("make the HN section longer") in the
Refine panel — it should update the digest without re-fetching the web.

---

## TODO 6 — Save and list managed agents

**File:** `backend/routes/agents.py`

### TODO 6a — List agents

```python
result = _get_client().agents.list()
agents = result.agents or []
return [
    {
        "id": a.id,
        "description": getattr(a, "description", ""),
        "base_agent": getattr(a, "base_agent", BASE_AGENT),
    }
    for a in agents
]
```

### TODO 6b — Create (save) an agent

Once you have iterated on your configuration, `agents.create()` bakes it in permanently.
Every future invocation with `environment="remote"` forks a fresh sandbox that already
has your AGENTS.md and SKILL.md — no inline config needed.

```python
agent = _get_client().agents.create(
    id=req.id,
    base_agent=BASE_AGENT,
    description=req.description,
    system_instruction=config.voice,
    tools=[
        {"type": "code_execution"},
        {"type": "google_search"},
        {"type": "url_context"},
    ],
    base_environment={
        "type": "remote",
        "sources": _inline_sources(config.agents_md, config.skill_md),
    },
)
log.info("Agent created — id=%s", getattr(agent, "id", req.id))
return {"id": getattr(agent, "id", req.id), "description": getattr(agent, "description", req.description)}
```

**Verify:** go to the **Agents** page, enter an ID (e.g. `my-digest`), click Save.
The agent should appear in the list. Select it from the Dashboard dropdown and run —
notice there is no `system_instruction` in the request payload because it is baked in.

---

## What happens end to end

```
1. Browser → POST /api/runs
2. FastAPI spawns asyncio.Task → runs _stream_sync() in thread executor
3. _stream_sync() calls client.interactions.create(..., stream=True)
4. Google provisions Ubuntu sandbox, starts agent loop
5. Agent: fetches homepages, parses headlines, writes digest, generates PDF
6. Each event → pushed to asyncio.Queue → SSE endpoint → browser StreamFeed
7. interaction.completed → env_id + interaction_id saved to data/runs/<id>.json
8. Browser: Download PDF → GET /api/runs/{id}/pdf
9. Backend: downloads snapshot tar from Files API, extracts digest.pdf, streams to browser
```

---

## Stretch goals

- **Different voice**: edit the Voice page and compare output tone
- **New skill**: add a second SKILL.md (e.g. a markdown report skill) and mount it alongside the PDF skill
- **New source**: add a fourth URL to Sources and see the agent handle it
- **Fork from environment**: after a successful run, call `agents.create(base_environment=env_id)` to fork the live sandbox into a new saved agent
