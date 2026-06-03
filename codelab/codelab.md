# Build a Daily Tech Digest Agent on the Gemini API

## Overview

**Duration:** ~2 hours  
**Level:** Intermediate  
**What you will build:** A managed agent that fetches tech news, summarises it in a sharp editorial voice, and generates a polished PDF — powered by a single Gemini API call.

The app is pre-built. Your job is to wire in the **Managed Agents API calls** at the TODO sections inside `backend/services/agent_client.py` and `backend/routes/agents.py`.

### Prerequisites

- Python 3.10+ and [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Node.js 18+
- Gemini API key with billing enabled — [aistudio.google.com/api-keys](https://aistudio.google.com/api-keys)

---

## 1. Setup

```bash
cd codelab/starter
cp .env.example .env
# Edit .env — paste your GEMINI_API_KEY

uv sync
cd frontend && npm install && cd ..
```

**Run the app:**

```bash
# Terminal 1
uv run uvicorn backend.main:app --reload

# Terminal 2
cd frontend && npm run dev
```

Open http://localhost:5173. The UI loads but **Run Digest** fails — that is expected until you complete the TODOs.

---

## 2. TODO 1 — Create the client

**File:** `backend/services/agent_client.py` → `_make_client()`

`genai.Client()` is the entry point for all Managed Agents API operations. It reads `GEMINI_API_KEY` from the environment automatically.

```python
from google import genai
log.info("Creating Gemini API client")
_client_singleton = genai.Client()
```

**Verify:** restart the server — the `RuntimeError: TODO 1 not implemented` should disappear from the logs.

---

## 3. TODO 2 — First streaming call

**File:** `backend/services/agent_client.py` → `_stream_sync()`, section marked TODO 2

Every agent call uses `client.interactions.create()`. The three required fields are `agent`, `input`, and `stream=True`.

```python
kwargs: dict = {
    "agent": agent_id or BASE_AGENT,
    "input": prompt,
    "stream": True,
}
```

`BASE_AGENT = "antigravity-preview-05-2026"` is the Antigravity agent — it can browse the web, run Python, manage files, and use skills mounted into the sandbox.

`stream=True` returns an iterable of events. You see each tool call, code execution result, and text chunk as the agent produces it — that is what appears in the browser stream feed.

---

## 4. TODO 3 — Add environment and system_instruction

**File:** `backend/services/agent_client.py` → `_stream_sync()`, section marked TODO 3

The `environment` parameter provisions the Linux sandbox. `system_instruction` sets the agent's persona.

**Case A — Saved agent** (user picked one from the dropdown):
```python
kwargs["environment"] = "remote"
```
`"remote"` forks a fresh sandbox from the agent's saved `base_environment`.

**Case B — Inline config** (no saved agent):
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

`sources` mounts two files into the sandbox filesystem at startup:

| Source file | Sandbox path | What it does |
|---|---|---|
| `config["agents_md"]` | `.agents/AGENTS.md` | Persistent rules — the harness loads this automatically |
| `config["skill_md"]` | `.agents/skills/digest-pdf/SKILL.md` | PDF skill — the agent discovers and follows it |

**Verify:** click **Run Digest** — you should see `⚡ Interaction started` in the stream feed and tool calls appearing one by one.

---

## 5. TODO 4 — Extract environment_id and interaction_id

**File:** `backend/services/agent_client.py` → `_handle_event()`, inside `elif event_type == "interaction.completed":`

When the agent finishes, the API sends an `interaction.completed` event. Extract both IDs from it:

```python
interaction = getattr(event, "interaction", None)
if interaction:
    env_id = getattr(interaction, "environment_id", None)
    iid    = getattr(interaction, "id", None)
    usage  = getattr(interaction, "usage", None)
    if usage:
        log.info("Usage — input=%s output=%s total=%s",
            getattr(usage, "total_input_tokens", "?"),
            getattr(usage, "total_output_tokens", "?"),
            getattr(usage, "total_tokens", "?"))
```

> **Important:** The text output does NOT come from `interaction.completed` — it accumulates in `text_parts` from `StepDelta(type="text")` events. The completed event carries empty outputs by design to reduce payload size.

`environment_id` identifies the sandbox where `digest.pdf` was saved. `interaction_id` is this conversation turn — needed for multi-turn in the next step.

**Verify:** after a successful run, check `data/runs/<id>.json` — `environment_id` and `interaction_id` should now be populated. The **Download PDF** button will appear.

---

## 6. TODO 5 — Multi-turn refinement

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

The agent still has `digest.pdf` at `/workspace/digest.pdf`, the full conversation history, and all installed packages. A refinement like "make the HN section twice as long" edits the existing digest without re-fetching the web.

**Verify:** run a digest, then type a refinement in the Refine panel — the agent should respond using context from the first turn.

---

## 7. TODO 6 — List managed agents

**File:** `backend/routes/agents.py` → `list_agents()`

```python
result = _make_client().agents.list()
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

**Verify:** the **Agents** page should load without the empty list.

---

## 8. TODO 7 — Save a managed agent

**File:** `backend/routes/agents.py` → `create_agent()`

`agents.create()` bakes your voice, AGENTS.md, and SKILL.md into a saved agent. Every future invocation with `environment="remote"` forks a fresh sandbox that already has your configuration — no inline `sources` needed.

```python
agent = _make_client().agents.create(
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

**Verify:** go to the **Agents** page, enter an ID like `my-digest`, click Save. The agent should appear in the list. Select it from the Dashboard dropdown and run a digest — notice no `system_instruction` or `sources` appear in the logs because they are baked in.

---

## 9. What happens end to end

```
Browser → POST /api/runs
FastAPI → asyncio.Task → _stream_sync() in thread executor
_stream_sync() → client.interactions.create(..., stream=True)
Google → provisions Ubuntu sandbox, starts agent reasoning loop
Agent: fetches homepages → parses headlines → writes digest → generates PDF
Each event → asyncio.Queue → SSE endpoint → browser StreamFeed
interaction.completed → env_id + interaction_id saved to data/runs/<id>.json
Browser: Download PDF → GET /api/runs/{id}/pdf
Backend: downloads snapshot tar from Files API → extracts digest.pdf → streams to browser
```

---

## 10. Stretch goals

- **New voice:** edit the Voice page and compare how the same headlines read differently
- **New source:** add a fourth URL to Sources — no code change needed
- **Fork from environment:** after a run, call `agents.create(base_environment=env_id)` to fork the live sandbox into a new saved agent with all packages pre-installed
- **New skill:** add a second SKILL.md (e.g. a markdown report) and mount it alongside the PDF skill
