# Daily Digest App — Design Spec

**Date:** 2026-05-31  
**Status:** Approved

---

## Overview

A single-user local web application that exposes the full Google Managed Agents API surface as a usable product. The user configures news sources, an editorial voice, and a PDF skill; triggers digest runs; watches the agent work live; downloads the PDF; and refines the output in a multi-turn conversation — all from a browser UI.

The app runs entirely on localhost. No auth, no cloud deployment, no database — persistence is flat JSON files in `data/`.

---

## Example Use Cases

- Open the app, hit "Run Digest", watch the agent fetch HN + TechCrunch + The Verge, summarize them in a sharp editorial voice, and generate a PDF — all live in the browser.
- Edit the voice persona in the Voice view, save a new named agent, invoke it directly from the Dashboard.
- After a run completes, type "Make the AI section twice as long" in the refinement box and watch the agent revise the PDF in the same sandbox.
- Open History, find yesterday's run, re-download its PDF.

---

## Architecture

Two processes:

```
frontend/   React + Vite          → localhost:5173
                ↕ HTTP + SSE
backend/    FastAPI + uvicorn     → localhost:8000
                ↕ google-genai SDK
        Google Managed Agents API
                ↕
        Remote Ubuntu sandbox
```

Vite proxies `/api/*` to `localhost:8000` during development so the frontend never handles CORS.

### Repo layout

The app lives at the repo root. Existing workshop scripts move to `workshop/`.

```
/                             # repo root
├── backend/
│   ├── main.py               # FastAPI app, mounts routers
│   ├── routes/
│   │   ├── config.py         # GET/PUT /api/config
│   │   ├── agents.py         # /api/agents CRUD
│   │   └── runs.py           # /api/runs + SSE streams
│   ├── services/
│   │   ├── agent_client.py   # wraps google-genai client
│   │   └── storage.py        # reads/writes data/ JSON files
│   └── models.py             # Pydantic request/response models
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── RunView.tsx
│   │   │   ├── Sources.tsx
│   │   │   ├── Voice.tsx
│   │   │   ├── Skills.tsx
│   │   │   ├── Agents.tsx
│   │   │   └── History.tsx
│   │   └── components/
│   │       ├── StreamFeed.tsx    # SSE event renderer
│   │       ├── RefinePanel.tsx   # multi-turn follow-up box
│   │       └── RunCard.tsx       # shared run summary card
│   ├── package.json
│   └── vite.config.ts
├── workshop/                 # original stage scripts (moved from root)
├── data/
│   ├── config.json
│   └── runs/                 # one <run-id>.json per run
├── pyproject.toml            # backend deps
└── README.md
```

---

## Backend API Routes

| Method | Path | Description |
|---|---|---|
| GET | `/api/config` | Return current config |
| PUT | `/api/config` | Update any config fields |
| GET | `/api/agents` | List saved agents from Managed Agents API |
| POST | `/api/agents` | Create agent from current config |
| GET | `/api/agents/{id}` | Get one agent |
| DELETE | `/api/agents/{id}` | Delete agent |
| POST | `/api/runs` | Start a run `{ agent_id?: string }` — uses current config; returns `{ run_id }` immediately |
| GET | `/api/runs/{id}/stream` | SSE: stream agent events |
| GET | `/api/runs` | List all past runs |
| GET | `/api/runs/{id}` | Get run detail |
| GET | `/api/runs/{id}/pdf` | Download PDF: backend fetches snapshot tar from Managed Agents API, extracts `/workspace/digest.pdf`, streams it to the browser as `application/pdf` |
| POST | `/api/runs/{id}/refine` | Start a refinement turn |
| GET | `/api/runs/{id}/refine/stream` | SSE: stream refinement events |

### Run object (`data/runs/<id>.json`)

```json
{
  "id": "uuid4",
  "started_at": "2026-05-31T08:00:00Z",
  "status": "running | completed | failed",
  "agent_id": "my-tech-digest | null",
  "environment_id": "env_abc123",
  "interaction_id": "int_xyz",
  "refine_interaction_id": "int_xyz2 | null",
  "output_text": "...",
  "refine_output_text": "... | null",
  "pdf_available": true,
  "error": "null | string"
}
```

### Config object (`data/config.json`)

```json
{
  "sources": ["https://news.ycombinator.com", "..."],
  "voice": "You are the editor of a sharp, slightly skeptical tech newsletter...",
  "agents_md": "Always include exactly 3 stories per source...",
  "skill_md": "---\nname: digest-pdf\n..."
}
```

### SSE event format

Each event sent over the stream is a JSON line:

```json
{ "type": "step", "content": "Fetching https://news.ycombinator.com..." }
{ "type": "output", "content": "Final digest text..." }
{ "type": "done", "pdf_available": true }
{ "type": "error", "message": "..." }
```

`POST /api/runs` launches the interaction as an `asyncio.Task` (not `BackgroundTask`). The `google-genai` streaming API is synchronous; it runs inside `asyncio.get_event_loop().run_in_executor(None, ...)` so it doesn't block the event loop. The executor thread pushes events into an `asyncio.Queue` keyed by run ID using `loop.call_soon_threadsafe(queue.put_nowait, event)`. The SSE handler is an async generator that drains the queue and forwards events. A sentinel value `None` signals the stream is done.

---

## Frontend Views

### Dashboard
Home screen. Shows:
- Active config summary (source count, first 60 chars of voice persona as a preview)
- "Run Digest" button — optionally select a saved agent from a dropdown, or use inline config
- Last 3 runs as `RunCard` components (status badge, timestamp, download link if PDF ready)

### Run view (`/runs/:id`)
Opened automatically after triggering a run. Two-column layout:
- **Left:** `StreamFeed` — scrolling list of SSE events rendered as labeled steps (tool call, observation, output). Auto-scrolls. Shows a spinner while `status === "running"`.
- **Right:** Final output text (appears once `type: output` event arrives). "Download PDF" button (active once `pdf_available`). Below: `RefinePanel` — textarea + submit; sends `POST /api/runs/:id/refine` then opens the refine SSE stream, appending to the same `StreamFeed`.

### Sources (`/sources`)
Editable list of news URLs. Add (text input + button), remove (× per row). `PUT /api/config` on every change.

### Voice (`/voice`)
`<textarea>` for the system instruction. Character count. Save button calls `PUT /api/config`.

### Skills (`/skills`)
Two fields: `name` and `description` as text inputs (parsed from SKILL.md frontmatter). Full SKILL.md body in a `<textarea>`. Save button.

### Agents (`/agents`)
Table: agent ID, description, base agent, actions (delete). "Save Current Config as Agent" form at top: ID input + description input + submit. Calls `POST /api/agents`.

### History (`/history`)
Paginated list of all past runs, newest first. Columns: date, agent used, status, PDF download. Click a row → navigates to its Run view (shows stored output, no live stream).

---

## Data Flow: Run Lifecycle

```
User clicks "Run Digest"
  → POST /api/runs  { agent_id?: string }
  ← { run_id }

Client opens EventSource("/api/runs/:id/stream")

BackgroundTask:
  1. Calls client.interactions.create(..., stream=True)
  2. For each stream event → pushes to async queue
  3. On completion → updates run JSON, sets status=completed

SSE handler:
  → drains queue → forwards events to browser
  → sends { type: "done" } and closes

User clicks "Refine"
  → POST /api/runs/:id/refine  { message }
  ← 202 Accepted

Client opens EventSource("/api/runs/:id/refine/stream")
  → same pattern, uses environment_id + interaction_id from stored run
```

---

## Error Handling

- If the Managed Agents API call fails, the background task pushes `{ type: "error", message: "..." }` to the queue and sets `run.status = "failed"`.
- If `GEMINI_API_KEY` is missing, FastAPI checks at startup (`@app.on_event("startup")`) and exits with a clear error before accepting any requests.
- SSE stream closes gracefully if the client disconnects mid-run (run continues in background, result stored).

---

## Tech Stack

**Backend**
- FastAPI + uvicorn
- `google-genai` SDK
- `sse-starlette` for SSE responses
- `pydantic` v2 (bundled with FastAPI)

**Frontend**
- React 18 + TypeScript
- Vite
- React Router v6
- TanStack Query v5
- Native `EventSource` API (no library)
- Tailwind CSS

---

## Running Locally

```bash
# Backend
uv sync
export GEMINI_API_KEY="..."
uv run uvicorn backend.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

---

## Known Constraints

- **One refinement turn per run.** `refine_interaction_id` stores only the last refinement. The `RefinePanel` replaces its output on each submit rather than threading unlimited turns. This matches the workshop scope.

---

## Constraints & Non-Goals

- No user authentication — single user, localhost only
- No email delivery (stretch goal from workshop, out of scope here)
- No GCS or private Git source mounting (API supports it, not exposed in UI)
- No agent versioning (API limitation — not yet available)
- Unsupported API params (`temperature`, `top_p`, etc.) are never sent
