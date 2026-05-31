# Daily Digest App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a FastAPI + React web app that wraps the Google Managed Agents API into a full product — configure sources/voice, trigger runs, stream live output, download PDFs, refine in multi-turn sessions.

**Architecture:** FastAPI backend on :8000 with SSE streaming (sync google-genai bridged to async via run_in_executor + asyncio.Queue). React/Vite frontend on :5173 proxied to backend. Flat JSON files in data/ for persistence.

**Tech Stack:** Python 3.13, FastAPI, uvicorn, sse-starlette, google-genai, pydantic v2, React 18, TypeScript, Vite, TanStack Query v5, React Router v6, Tailwind CSS.

---

## File Map

```
backend/
  __init__.py
  main.py              — FastAPI app, CORS, startup key check, router mounts
  models.py            — all Pydantic models (AppConfig, RunRecord, requests)
  routes/
    __init__.py
    config.py          — GET/PUT /api/config
    agents.py          — GET/POST/GET/{id}/DELETE /api/agents
    runs.py            — POST/GET/GET/{id}/stream/pdf/refine /api/runs
  services/
    __init__.py
    storage.py         — data/config.json + data/runs/ read/write
    agent_client.py    — google-genai wrapper, streaming bridge
data/
  config.json          — created on first startup
  runs/                — one UUID.json per run
frontend/
  index.html
  package.json
  tsconfig.json
  vite.config.ts       — /api proxy to :8000
  tailwind.config.js
  postcss.config.js
  src/
    main.tsx
    App.tsx            — Router + QueryClient + Layout
    types.ts           — TypeScript interfaces
    api.ts             — fetch wrappers for all endpoints
    components/
      Layout.tsx       — sidebar nav
      StreamFeed.tsx   — SSE event renderer
      RefinePanel.tsx  — multi-turn follow-up
      RunCard.tsx      — reusable run summary card
    pages/
      Dashboard.tsx
      RunView.tsx
      Sources.tsx
      Voice.tsx
      Skills.tsx
      Agents.tsx
      History.tsx
tests/
  test_storage.py
  test_config_routes.py
  test_agents_routes.py
```

---

## Task 1: Project scaffolding

**Files:**
- Modify: `pyproject.toml`
- Create: `backend/__init__.py`, `backend/routes/__init__.py`, `backend/services/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Update pyproject.toml with all backend deps**

```toml
[project]
name = "managedagents"
version = "0.1.0"
description = "Daily tech digest agent — Google Managed Agents API"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.29.0",
    "sse-starlette>=2.1.0",
    "google-genai>=2.7.0",
    "requests>=2.34.0",
    "aiofiles>=23.2.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.27.0",
]
```

- [ ] **Step 2: Create package init files and test conftest**

`backend/__init__.py` — empty  
`backend/routes/__init__.py` — empty  
`backend/services/__init__.py` — empty  
`tests/__init__.py` — empty  

```python
# tests/conftest.py
import os
# Satisfy the GEMINI_API_KEY startup check without hitting the real API
os.environ.setdefault("GEMINI_API_KEY", "test-api-key")
```

- [ ] **Step 3: Sync dependencies**

```bash
uv sync
```

Expected: lock file updated, all packages installed.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock backend/ tests/
git commit -m "feat: scaffold backend package structure"
```

---

## Task 2: Pydantic models

**Files:**
- Create: `backend/models.py`

- [ ] **Step 1: Write models**

```python
# backend/models.py
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
```

- [ ] **Step 2: Commit**

```bash
git add backend/models.py
git commit -m "feat: add Pydantic models"
```

---

## Task 3: Storage service

**Files:**
- Create: `backend/services/storage.py`
- Create: `tests/test_storage.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_storage.py
import pytest
from pathlib import Path
from backend.services.storage import Storage
from backend.models import AppConfig, RunRecord, RunStatus


@pytest.fixture
def tmp_storage(tmp_path):
    return Storage(data_dir=tmp_path)


def test_read_config_returns_default_when_missing(tmp_storage):
    config = tmp_storage.read_config()
    assert config.sources == AppConfig().sources
    assert config.voice == AppConfig().voice


def test_write_and_read_config(tmp_storage):
    cfg = AppConfig(sources=["https://example.com"], voice="Be terse.")
    tmp_storage.write_config(cfg)
    loaded = tmp_storage.read_config()
    assert loaded.sources == ["https://example.com"]
    assert loaded.voice == "Be terse."


def test_write_and_read_run(tmp_storage):
    run = RunRecord(id="abc123", started_at="2026-05-31T00:00:00Z")
    tmp_storage.write_run(run)
    loaded = tmp_storage.read_run("abc123")
    assert loaded.id == "abc123"
    assert loaded.status == RunStatus.running


def test_list_runs_returns_newest_first(tmp_storage):
    tmp_storage.write_run(RunRecord(id="a", started_at="2026-05-31T08:00:00Z"))
    tmp_storage.write_run(RunRecord(id="b", started_at="2026-05-31T09:00:00Z"))
    runs = tmp_storage.list_runs()
    assert runs[0].id == "b"
    assert runs[1].id == "a"


def test_read_missing_run_returns_none(tmp_storage):
    assert tmp_storage.read_run("nonexistent") is None
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
uv run pytest tests/test_storage.py -v
```

Expected: `ImportError` or `ModuleNotFoundError`

- [ ] **Step 3: Implement storage service**

```python
# backend/services/storage.py
from __future__ import annotations
import json
from pathlib import Path
from backend.models import AppConfig, RunRecord

DATA_DIR = Path(__file__).parent.parent.parent / "data"


class Storage:
    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir
        self.runs_dir = data_dir / "runs"
        self.config_path = data_dir / "config.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def read_config(self) -> AppConfig:
        if not self.config_path.exists():
            return AppConfig()
        return AppConfig.model_validate_json(self.config_path.read_text())

    def write_config(self, config: AppConfig) -> None:
        self.config_path.write_text(config.model_dump_json(indent=2))

    def write_run(self, run: RunRecord) -> None:
        path = self.runs_dir / f"{run.id}.json"
        path.write_text(run.model_dump_json(indent=2))

    def read_run(self, run_id: str) -> RunRecord | None:
        path = self.runs_dir / f"{run_id}.json"
        if not path.exists():
            return None
        return RunRecord.model_validate_json(path.read_text())

    def list_runs(self) -> list[RunRecord]:
        runs = [
            RunRecord.model_validate_json(p.read_text())
            for p in self.runs_dir.glob("*.json")
        ]
        return sorted(runs, key=lambda r: r.started_at, reverse=True)


storage = Storage()
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
uv run pytest tests/test_storage.py -v
```

Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/services/storage.py tests/test_storage.py
git commit -m "feat: add storage service with tests"
```

---

## Task 4: Agent client service

**Files:**
- Create: `backend/services/agent_client.py`

- [ ] **Step 1: Write agent client**

```python
# backend/services/agent_client.py
from __future__ import annotations
import asyncio
import os
import tarfile
import tempfile
from pathlib import Path

import requests as http_requests

BASE_AGENT = "antigravity-preview-05-2026"


def _build_prompt(sources: list[str]) -> str:
    return (
        "You're building a daily tech digest.\n\n"
        "For each source below:\n"
        + "\n".join(f"- {s}" for s in sources)
        + "\n\n"
        "1. Fetch the homepage.\n"
        "2. Pull the top 3 headlines.\n"
        "3. Summarize each in one sentence.\n"
        "4. Group output by source.\n"
        "5. Generate a PDF using the digest-pdf skill."
    )


def _stream_sync(
    agent_id: str | None,
    config: dict,
    queue: asyncio.Queue,
    loop: asyncio.AbstractEventLoop,
) -> None:
    """Runs in a thread executor. Pushes SSE event dicts into the asyncio queue."""
    from google import genai

    client = genai.Client()
    put = lambda event: loop.call_soon_threadsafe(queue.put_nowait, event)

    try:
        prompt = _build_prompt(config["sources"])
        kwargs: dict = {"agent": agent_id or BASE_AGENT, "input": prompt, "stream": True}

        if agent_id:
            kwargs["environment"] = "remote"
        else:
            kwargs["system_instruction"] = config["voice"]
            kwargs["environment"] = {
                "type": "remote",
                "sources": [
                    {
                        "type": "inline",
                        "target": ".agents/AGENTS.md",
                        "content": config["agents_md"],
                    },
                    {
                        "type": "inline",
                        "target": ".agents/skills/digest-pdf/SKILL.md",
                        "content": config["skill_md"],
                    },
                ],
            }

        stream = client.interactions.create(**kwargs)

        last = None
        for event in stream:
            last = event
            put({"type": "step", "content": str(event)})

        env_id = getattr(stream, "environment_id", None) or getattr(last, "environment_id", None)
        iid = getattr(stream, "id", None) or getattr(last, "id", None)
        output = getattr(stream, "output_text", None) or getattr(last, "output_text", None)

        put({"type": "output", "content": output or "", "environment_id": env_id, "interaction_id": iid})
        put({"type": "done", "pdf_available": True})

    except Exception as exc:
        put({"type": "error", "message": str(exc)})
    finally:
        put(None)  # sentinel — signals stream end


def _refine_sync(
    environment_id: str,
    interaction_id: str,
    message: str,
    agent_id: str | None,
    queue: asyncio.Queue,
    loop: asyncio.AbstractEventLoop,
) -> None:
    """Runs in a thread executor. Streams a refinement turn."""
    from google import genai

    client = genai.Client()
    put = lambda event: loop.call_soon_threadsafe(queue.put_nowait, event)

    try:
        stream = client.interactions.create(
            agent=agent_id or BASE_AGENT,
            input=message,
            environment=environment_id,
            previous_interaction_id=interaction_id,
            stream=True,
        )

        last = None
        for event in stream:
            last = event
            put({"type": "step", "content": str(event)})

        output = getattr(stream, "output_text", None) or getattr(last, "output_text", None)
        iid = getattr(stream, "id", None) or getattr(last, "id", None)

        put({"type": "output", "content": output or "", "interaction_id": iid})
        put({"type": "done", "pdf_available": True})

    except Exception as exc:
        put({"type": "error", "message": str(exc)})
    finally:
        put(None)


def download_pdf(environment_id: str) -> bytes:
    """Download the PDF from the environment snapshot and return its bytes."""
    api_key = os.environ["GEMINI_API_KEY"]
    r = http_requests.get(
        f"https://generativelanguage.googleapis.com/v1beta/files/environment-{environment_id}:download",
        params={"alt": "media"},
        headers={"x-goog-api-key": api_key},
        allow_redirects=True,
    )
    r.raise_for_status()

    with tempfile.TemporaryDirectory() as tmp:
        tar_path = Path(tmp) / "snapshot.tar"
        tar_path.write_bytes(r.content)
        with tarfile.open(tar_path) as tar:
            tar.extractall(path=tmp, filter="data")
        pdf_path = Path(tmp) / "workspace" / "digest.pdf"
        if not pdf_path.exists():
            raise FileNotFoundError("digest.pdf not found in environment snapshot")
        return pdf_path.read_bytes()
```

- [ ] **Step 2: Commit**

```bash
git add backend/services/agent_client.py
git commit -m "feat: add agent client service with streaming bridge"
```

---

## Task 5: Config routes

**Files:**
- Create: `backend/routes/config.py`
- Create: `tests/test_config_routes.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_config_routes.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from backend.models import AppConfig


@pytest.fixture
def client(tmp_path):
    from backend.services.storage import Storage
    mock_storage = Storage(data_dir=tmp_path)

    with patch("backend.routes.config.storage", mock_storage):
        from backend.main import app
        yield TestClient(app)


def test_get_config_returns_defaults(client):
    resp = client.get("/api/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "sources" in data
    assert "voice" in data
    assert "agents_md" in data
    assert "skill_md" in data


def test_put_config_updates_sources(client):
    resp = client.put("/api/config", json={"sources": ["https://example.com"]})
    assert resp.status_code == 200
    assert resp.json()["sources"] == ["https://example.com"]


def test_put_config_partial_update_preserves_other_fields(client):
    client.put("/api/config", json={"voice": "Be brief."})
    resp = client.get("/api/config")
    assert resp.json()["voice"] == "Be brief."
    assert len(resp.json()["sources"]) > 0
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
uv run pytest tests/test_config_routes.py -v
```

Expected: ImportError (main.py doesn't exist yet, that's fine — we'll create it in Task 11)

- [ ] **Step 3: Implement config routes**

```python
# backend/routes/config.py
from fastapi import APIRouter
from backend.models import AppConfig
from backend.services.storage import storage

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("", response_model=AppConfig)
def get_config():
    return storage.read_config()


@router.put("", response_model=AppConfig)
def update_config(updates: dict):
    current = storage.read_config().model_dump()
    current.update({k: v for k, v in updates.items() if k in current})
    new_config = AppConfig.model_validate(current)
    storage.write_config(new_config)
    return new_config
```

- [ ] **Step 4: Commit**

```bash
git add backend/routes/config.py tests/test_config_routes.py
git commit -m "feat: add config routes"
```

---

## Task 6: Agents routes

**Files:**
- Create: `backend/routes/agents.py`
- Create: `tests/test_agents_routes.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_agents_routes.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch


def make_mock_agent(id="test-agent", description="A test agent"):
    a = MagicMock()
    a.id = id
    a.description = description
    a.base_agent = "antigravity-preview-05-2026"
    return a


@pytest.fixture
def client():
    mock_client = MagicMock()
    mock_client.agents.list.return_value.agents = [make_mock_agent()]
    mock_client.agents.get.return_value = make_mock_agent()

    with patch("backend.routes.agents.genai_client", mock_client), \
         patch("backend.routes.agents.storage"):
        from backend.main import app
        yield TestClient(app)


def test_list_agents(client):
    resp = client.get("/api/agents")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert resp.json()[0]["id"] == "test-agent"


def test_delete_agent(client):
    resp = client.delete("/api/agents/test-agent")
    assert resp.status_code == 204


def test_get_agent(client):
    resp = client.get("/api/agents/test-agent")
    assert resp.status_code == 200
    assert resp.json()["id"] == "test-agent"
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
uv run pytest tests/test_agents_routes.py -v
```

Expected: ImportError

- [ ] **Step 3: Implement agents routes**

```python
# backend/routes/agents.py
from fastapi import APIRouter, HTTPException
from google import genai
from backend.models import AppConfig, CreateAgentRequest
from backend.services.storage import storage
from backend.services.agent_client import BASE_AGENT

router = APIRouter(prefix="/api/agents", tags=["agents"])

genai_client = genai.Client()


@router.get("")
def list_agents():
    result = genai_client.agents.list()
    agents = result.agents or []
    return [
        {"id": a.id, "description": getattr(a, "description", ""), "base_agent": getattr(a, "base_agent", BASE_AGENT)}
        for a in agents
    ]


@router.post("", status_code=201)
def create_agent(req: CreateAgentRequest):
    config = storage.read_config()
    agent = genai_client.agents.create(
        id=req.id,
        base_agent=BASE_AGENT,
        description=req.description,
        system_instruction=config.voice,
        base_environment={
            "type": "remote",
            "sources": [
                {"type": "inline", "target": ".agents/AGENTS.md", "content": config.agents_md},
                {"type": "inline", "target": ".agents/skills/digest-pdf/SKILL.md", "content": config.skill_md},
            ],
        },
    )
    return {"id": agent.id, "description": getattr(agent, "description", req.description)}


@router.get("/{agent_id}")
def get_agent(agent_id: str):
    try:
        a = genai_client.agents.get(id=agent_id)
        return {"id": a.id, "description": getattr(a, "description", ""), "base_agent": getattr(a, "base_agent", BASE_AGENT)}
    except Exception:
        raise HTTPException(status_code=404, detail="Agent not found")


@router.delete("/{agent_id}", status_code=204)
def delete_agent(agent_id: str):
    try:
        genai_client.agents.delete(id=agent_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Agent not found")
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
uv run pytest tests/test_agents_routes.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/routes/agents.py tests/test_agents_routes.py
git commit -m "feat: add agents routes"
```

---

## Task 7: Runs routes — core (create, list, get)

**Files:**
- Create: `backend/routes/runs.py`

- [ ] **Step 1: Write runs route — core**

```python
# backend/routes/runs.py
from __future__ import annotations
import asyncio
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, StreamingResponse

from backend.models import RefineRequest, RunRecord, RunStatus, StartRunRequest
from backend.services import agent_client
from backend.services.storage import storage

router = APIRouter(prefix="/api/runs", tags=["runs"])

# In-memory queues keyed by run_id
_run_queues: dict[str, asyncio.Queue] = {}
_refine_queues: dict[str, asyncio.Queue] = {}


@router.post("", status_code=202)
async def start_run(req: StartRunRequest):
    run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    run = RunRecord(id=run_id, started_at=now, agent_id=req.agent_id)
    storage.write_run(run)

    queue: asyncio.Queue = asyncio.Queue()
    _run_queues[run_id] = queue
    config = storage.read_config().model_dump()

    loop = asyncio.get_event_loop()

    async def background():
        await loop.run_in_executor(
            None,
            agent_client._stream_sync,
            req.agent_id,
            config,
            queue,
            loop,
        )

    asyncio.create_task(background())
    return {"run_id": run_id}


@router.get("")
def list_runs():
    return storage.list_runs()


@router.get("/{run_id}", response_model=RunRecord)
def get_run(run_id: str):
    run = storage.read_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run
```

- [ ] **Step 2: Commit**

```bash
git add backend/routes/runs.py
git commit -m "feat: add runs routes (create, list, get)"
```

---

## Task 8: SSE streaming endpoint

**Files:**
- Modify: `backend/routes/runs.py`

- [ ] **Step 1: Add SSE stream endpoint to runs.py**

Add this function after `get_run` in `backend/routes/runs.py`:

```python
from sse_starlette.sse import EventSourceResponse


@router.get("/{run_id}/stream")
async def stream_run(run_id: str):
    run = storage.read_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    queue = _run_queues.get(run_id)

    async def event_generator():
        # If run already completed (reconnect case), replay stored result
        if run.status != RunStatus.running:
            if run.output_text:
                yield {"data": json.dumps({"type": "output", "content": run.output_text})}
            yield {"data": json.dumps({"type": "done", "pdf_available": run.pdf_available})}
            return

        if not queue:
            yield {"data": json.dumps({"type": "error", "message": "Stream not available"})}
            return

        while True:
            event = await queue.get()
            if event is None:
                # Stream complete — update run record
                current = storage.read_run(run_id)
                if current:
                    current.status = RunStatus.completed
                    storage.write_run(current)
                _run_queues.pop(run_id, None)
                break

            # Persist output and IDs as they arrive
            if event.get("type") == "output":
                current = storage.read_run(run_id)
                if current:
                    current.output_text = event.get("content")
                    current.environment_id = event.get("environment_id")
                    current.interaction_id = event.get("interaction_id")
                    current.pdf_available = True
                    storage.write_run(current)

            if event.get("type") == "error":
                current = storage.read_run(run_id)
                if current:
                    current.status = RunStatus.failed
                    current.error = event.get("message")
                    storage.write_run(current)

            yield {"data": json.dumps(event)}

    return EventSourceResponse(event_generator())
```

- [ ] **Step 2: Commit**

```bash
git add backend/routes/runs.py
git commit -m "feat: add SSE streaming endpoint"
```

---

## Task 9: PDF download endpoint

**Files:**
- Modify: `backend/routes/runs.py`

- [ ] **Step 1: Add PDF download endpoint to runs.py**

Add after `stream_run` in `backend/routes/runs.py`:

```python
@router.get("/{run_id}/pdf")
def download_pdf(run_id: str):
    run = storage.read_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if not run.pdf_available or not run.environment_id:
        raise HTTPException(status_code=404, detail="PDF not available")
    try:
        pdf_bytes = agent_client.download_pdf(run.environment_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="PDF not found in snapshot")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=digest-{run_id[:8]}.pdf"},
    )
```

- [ ] **Step 2: Commit**

```bash
git add backend/routes/runs.py
git commit -m "feat: add PDF download endpoint"
```

---

## Task 10: Refinement endpoints

**Files:**
- Modify: `backend/routes/runs.py`

- [ ] **Step 1: Add refinement endpoints to runs.py**

Add after `download_pdf` in `backend/routes/runs.py`:

```python
@router.post("/{run_id}/refine", status_code=202)
async def start_refine(run_id: str, req: RefineRequest):
    run = storage.read_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if not run.environment_id or not run.interaction_id:
        raise HTTPException(status_code=400, detail="Run has no environment to refine")

    queue: asyncio.Queue = asyncio.Queue()
    _refine_queues[run_id] = queue
    loop = asyncio.get_event_loop()

    async def background():
        await loop.run_in_executor(
            None,
            agent_client._refine_sync,
            run.environment_id,
            run.interaction_id,
            req.message,
            run.agent_id,
            queue,
            loop,
        )

    asyncio.create_task(background())
    return {"run_id": run_id}


@router.get("/{run_id}/refine/stream")
async def stream_refine(run_id: str):
    run = storage.read_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    queue = _refine_queues.get(run_id)

    async def event_generator():
        if not queue:
            yield {"data": json.dumps({"type": "error", "message": "No refinement in progress"})}
            return

        while True:
            event = await queue.get()
            if event is None:
                current = storage.read_run(run_id)
                if current:
                    current.pdf_available = True
                    storage.write_run(current)
                _refine_queues.pop(run_id, None)
                break

            if event.get("type") == "output":
                current = storage.read_run(run_id)
                if current:
                    current.refine_output_text = event.get("content")
                    current.refine_interaction_id = event.get("interaction_id")
                    storage.write_run(current)

            yield {"data": json.dumps(event)}

    return EventSourceResponse(event_generator())
```

- [ ] **Step 2: Commit**

```bash
git add backend/routes/runs.py
git commit -m "feat: add refinement endpoints"
```

---

## Task 11: FastAPI main app

**Files:**
- Create: `backend/main.py`

- [ ] **Step 1: Write main app**

```python
# backend/main.py
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes import agents, config, runs


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.environ.get("GEMINI_API_KEY"):
        raise RuntimeError("GEMINI_API_KEY environment variable is not set")
    yield


app = FastAPI(title="Daily Digest API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(config.router)
app.include_router(agents.router)
app.include_router(runs.router)
```

- [ ] **Step 2: Run config route tests (now that main.py exists)**

```bash
uv run pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 3: Smoke-test the server starts**

```bash
GEMINI_API_KEY=test uv run uvicorn backend.main:app --port 8000
```

Expected: `Application startup complete.`  
Stop with Ctrl-C.

- [ ] **Step 4: Commit**

```bash
git add backend/main.py
git commit -m "feat: add FastAPI main app with CORS and startup key check"
```

---

## Task 12: Frontend scaffold

**Files:**
- Create: `frontend/` (Vite project)

- [ ] **Step 1: Scaffold React + TypeScript + Vite project**

```bash
cd /mnt/c/Users/saous/OneDrive/Desktop/ManagedAgents
npm create vite@latest frontend -- --template react-ts
cd frontend && npm install
```

- [ ] **Step 2: Install dependencies**

```bash
npm install react-router-dom @tanstack/react-query
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

- [ ] **Step 3: Configure Tailwind — update `frontend/tailwind.config.js`**

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: { extend: {} },
  plugins: [],
}
```

- [ ] **Step 4: Add Tailwind directives to `frontend/src/index.css`**

Replace the entire file with:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 5: Configure Vite proxy — `frontend/vite.config.ts`**

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
```

- [ ] **Step 6: Commit**

```bash
cd ..
git add frontend/
git commit -m "feat: scaffold React + Vite + Tailwind frontend"
```

---

## Task 13: TypeScript types and API client

**Files:**
- Create: `frontend/src/types.ts`
- Create: `frontend/src/api.ts`

- [ ] **Step 1: Write TypeScript types**

```ts
// frontend/src/types.ts
export interface AppConfig {
  sources: string[];
  voice: string;
  agents_md: string;
  skill_md: string;
}

export type RunStatus = "running" | "completed" | "failed";

export interface RunRecord {
  id: string;
  started_at: string;
  status: RunStatus;
  agent_id: string | null;
  environment_id: string | null;
  interaction_id: string | null;
  refine_interaction_id: string | null;
  output_text: string | null;
  refine_output_text: string | null;
  pdf_available: boolean;
  error: string | null;
}

export interface AgentRecord {
  id: string;
  description: string;
  base_agent: string;
}

export type SSEEventType = "step" | "output" | "done" | "error";

export interface SSEEvent {
  type: SSEEventType;
  content?: string;
  message?: string;
  pdf_available?: boolean;
  environment_id?: string;
  interaction_id?: string;
}
```

- [ ] **Step 2: Write API client**

```ts
// frontend/src/api.ts
import type { AppConfig, AgentRecord, RunRecord } from "./types";

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  if (res.status === 204) return undefined as T;
  return res.json();
}

// Config
export const getConfig = () => request<AppConfig>("/config");
export const updateConfig = (updates: Partial<AppConfig>) =>
  request<AppConfig>("/config", { method: "PUT", body: JSON.stringify(updates) });

// Agents
export const listAgents = () => request<AgentRecord[]>("/agents");
export const createAgent = (body: { id: string; description: string }) =>
  request<AgentRecord>("/agents", { method: "POST", body: JSON.stringify(body) });
export const getAgent = (id: string) => request<AgentRecord>(`/agents/${id}`);
export const deleteAgent = (id: string) =>
  request<void>(`/agents/${id}`, { method: "DELETE" });

// Runs
export const startRun = (agent_id?: string) =>
  request<{ run_id: string }>("/runs", {
    method: "POST",
    body: JSON.stringify({ agent_id: agent_id ?? null }),
  });
export const listRuns = () => request<RunRecord[]>("/runs");
export const getRun = (id: string) => request<RunRecord>(`/runs/${id}`);
export const startRefine = (run_id: string, message: string) =>
  request<{ run_id: string }>(`/runs/${run_id}/refine`, {
    method: "POST",
    body: JSON.stringify({ message }),
  });
export const getPdfUrl = (run_id: string) => `${BASE}/runs/${run_id}/pdf`;
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types.ts frontend/src/api.ts
git commit -m "feat: add TypeScript types and API client"
```

---

## Task 14: App shell — Layout and routing

**Files:**
- Modify: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/components/Layout.tsx`

- [ ] **Step 1: Update main.tsx**

```tsx
// frontend/src/main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";
import "./index.css";

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </BrowserRouter>
  </React.StrictMode>
);
```

- [ ] **Step 2: Write App.tsx**

```tsx
// frontend/src/App.tsx
import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import RunView from "./pages/RunView";
import Sources from "./pages/Sources";
import Voice from "./pages/Voice";
import Skills from "./pages/Skills";
import Agents from "./pages/Agents";
import History from "./pages/History";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/runs/:id" element={<RunView />} />
        <Route path="/sources" element={<Sources />} />
        <Route path="/voice" element={<Voice />} />
        <Route path="/skills" element={<Skills />} />
        <Route path="/agents" element={<Agents />} />
        <Route path="/history" element={<History />} />
      </Routes>
    </Layout>
  );
}
```

- [ ] **Step 3: Write Layout.tsx**

```tsx
// frontend/src/components/Layout.tsx
import { NavLink } from "react-router-dom";

const NAV = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/sources", label: "Sources" },
  { to: "/voice", label: "Voice" },
  { to: "/skills", label: "Skills" },
  { to: "/agents", label: "Agents" },
  { to: "/history", label: "History" },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen bg-gray-50">
      <aside className="w-48 bg-white border-r flex flex-col py-6 px-4 gap-1 shrink-0">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-4">
          Daily Digest
        </p>
        {NAV.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            className={({ isActive }) =>
              `px-3 py-2 rounded text-sm font-medium transition-colors ${
                isActive
                  ? "bg-indigo-50 text-indigo-700"
                  : "text-gray-600 hover:bg-gray-100"
              }`
            }
          >
            {n.label}
          </NavLink>
        ))}
      </aside>
      <main className="flex-1 overflow-auto p-8">{children}</main>
    </div>
  );
}
```

- [ ] **Step 4: Create placeholder pages so the app compiles**

Create each with a one-liner so routing works while we build the real pages:

```bash
for page in Dashboard RunView Sources Voice Skills Agents History; do
  echo "export default function ${page}() { return <div>${page}</div>; }" > frontend/src/pages/${page}.tsx
done
mkdir -p frontend/src/components
```

- [ ] **Step 5: Verify the frontend compiles and runs**

```bash
cd frontend && npm run dev
```

Open http://localhost:5173 — you should see the sidebar and placeholder page text.

- [ ] **Step 6: Commit**

```bash
cd ..
git add frontend/src/
git commit -m "feat: add app shell with sidebar layout and routing"
```

---

## Task 15: StreamFeed and RunCard components

**Files:**
- Create: `frontend/src/components/StreamFeed.tsx`
- Create: `frontend/src/components/RunCard.tsx`

- [ ] **Step 1: Write StreamFeed**

```tsx
// frontend/src/components/StreamFeed.tsx
import { useEffect, useRef } from "react";
import type { SSEEvent } from "../types";

interface Props {
  events: SSEEvent[];
  running: boolean;
}

export default function StreamFeed({ events, running }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events.length]);

  return (
    <div className="h-full overflow-auto bg-gray-900 rounded-lg p-4 font-mono text-xs text-gray-300 space-y-1">
      {events.map((e, i) => {
        if (e.type === "step")
          return <p key={i} className="text-gray-400">{e.content}</p>;
        if (e.type === "output")
          return (
            <p key={i} className="text-green-400 whitespace-pre-wrap">
              {e.content}
            </p>
          );
        if (e.type === "error")
          return <p key={i} className="text-red-400">Error: {e.message}</p>;
        if (e.type === "done")
          return <p key={i} className="text-indigo-400">✓ Done</p>;
        return null;
      })}
      {running && (
        <p className="text-yellow-400 animate-pulse">Agent is working…</p>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
```

- [ ] **Step 2: Write RunCard**

```tsx
// frontend/src/components/RunCard.tsx
import { Link } from "react-router-dom";
import type { RunRecord } from "../types";
import { getPdfUrl } from "../api";

interface Props {
  run: RunRecord;
}

const STATUS_COLOR: Record<string, string> = {
  running: "bg-yellow-100 text-yellow-800",
  completed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
};

export default function RunCard({ run }: Props) {
  const date = new Date(run.started_at).toLocaleString();
  return (
    <div className="border rounded-lg p-4 bg-white flex items-center justify-between gap-4">
      <div className="flex items-center gap-3">
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLOR[run.status]}`}>
          {run.status}
        </span>
        <span className="text-sm text-gray-500">{date}</span>
        {run.agent_id && (
          <span className="text-xs text-gray-400 font-mono">{run.agent_id}</span>
        )}
      </div>
      <div className="flex gap-2">
        <Link
          to={`/runs/${run.id}`}
          className="text-sm text-indigo-600 hover:underline"
        >
          View
        </Link>
        {run.pdf_available && (
          <a
            href={getPdfUrl(run.id)}
            download
            className="text-sm text-green-600 hover:underline"
          >
            PDF
          </a>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/
git commit -m "feat: add StreamFeed and RunCard components"
```

---

## Task 16: Dashboard page

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`

- [ ] **Step 1: Write Dashboard**

```tsx
// frontend/src/pages/Dashboard.tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { listAgents, listRuns, startRun, getConfig } from "../api";
import RunCard from "../components/RunCard";

export default function Dashboard() {
  const navigate = useNavigate();
  const [agentId, setAgentId] = useState<string>("");
  const [loading, setLoading] = useState(false);

  const { data: config } = useQuery({ queryKey: ["config"], queryFn: getConfig });
  const { data: agents = [] } = useQuery({ queryKey: ["agents"], queryFn: listAgents });
  const { data: runs = [] } = useQuery({ queryKey: ["runs"], queryFn: listRuns });

  const recentRuns = runs.slice(0, 3);

  async function handleRun() {
    setLoading(true);
    try {
      const { run_id } = await startRun(agentId || undefined);
      navigate(`/runs/${run_id}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-2xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Daily Digest</h1>
        {config && (
          <p className="text-sm text-gray-500">
            {config.sources.length} sources · "
            {config.voice.slice(0, 60)}…"
          </p>
        )}
      </div>

      <div className="bg-white border rounded-xl p-6 space-y-4">
        <label className="block text-sm font-medium text-gray-700">
          Agent (optional — uses inline config if blank)
        </label>
        <select
          value={agentId}
          onChange={(e) => setAgentId(e.target.value)}
          className="w-full border rounded-lg px-3 py-2 text-sm"
        >
          <option value="">Inline config</option>
          {agents.map((a) => (
            <option key={a.id} value={a.id}>
              {a.id}
            </option>
          ))}
        </select>
        <button
          onClick={handleRun}
          disabled={loading}
          className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-medium rounded-lg px-4 py-2 transition-colors"
        >
          {loading ? "Starting…" : "Run Digest"}
        </button>
      </div>

      {recentRuns.length > 0 && (
        <div className="space-y-2">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
            Recent runs
          </h2>
          {recentRuns.map((r) => (
            <RunCard key={r.id} run={r} />
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx
git commit -m "feat: add Dashboard page"
```

---

## Task 17: RefinePanel component

**Files:**
- Create: `frontend/src/components/RefinePanel.tsx`

- [ ] **Step 1: Write RefinePanel**

```tsx
// frontend/src/components/RefinePanel.tsx
import { useState } from "react";
import type { SSEEvent } from "../types";
import { startRefine } from "../api";

interface Props {
  runId: string;
  onEvents: (events: SSEEvent[]) => void;
}

export default function RefinePanel({ runId, onEvents }: Props) {
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleRefine() {
    if (!message.trim()) return;
    setLoading(true);
    const events: SSEEvent[] = [];

    try {
      await startRefine(runId, message);
      setMessage("");

      await new Promise<void>((resolve, reject) => {
        const es = new EventSource(`/api/runs/${runId}/refine/stream`);
        es.onmessage = (e) => {
          const event: SSEEvent = JSON.parse(e.data);
          events.push(event);
          onEvents([...events]);
          if (event.type === "done" || event.type === "error") {
            es.close();
            resolve();
          }
        };
        es.onerror = () => { es.close(); reject(new Error("SSE error")); };
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700">
        Refine output
      </label>
      <textarea
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        rows={3}
        placeholder="Make the AI section twice as long. Add an Editor's Note at the top."
        className="w-full border rounded-lg px-3 py-2 text-sm resize-none"
      />
      <button
        onClick={handleRefine}
        disabled={loading || !message.trim()}
        className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg px-4 py-2 transition-colors"
      >
        {loading ? "Refining…" : "Refine"}
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/RefinePanel.tsx
git commit -m "feat: add RefinePanel component"
```

---

## Task 18: RunView page

**Files:**
- Modify: `frontend/src/pages/RunView.tsx`

- [ ] **Step 1: Write RunView**

```tsx
// frontend/src/pages/RunView.tsx
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getRun, getPdfUrl } from "../api";
import StreamFeed from "../components/StreamFeed";
import RefinePanel from "../components/RefinePanel";
import type { SSEEvent, RunRecord } from "../types";

export default function RunView() {
  const { id } = useParams<{ id: string }>();
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [streaming, setStreaming] = useState(true);

  const { data: run, refetch } = useQuery<RunRecord>({
    queryKey: ["run", id],
    queryFn: () => getRun(id!),
    refetchInterval: streaming ? 2000 : false,
  });

  useEffect(() => {
    if (!id) return;
    const es = new EventSource(`/api/runs/${id}/stream`);
    es.onmessage = (e) => {
      const event: SSEEvent = JSON.parse(e.data);
      setEvents((prev) => [...prev, event]);
      if (event.type === "done" || event.type === "error") {
        setStreaming(false);
        es.close();
        refetch();
      }
    };
    es.onerror = () => { setStreaming(false); es.close(); };
    return () => es.close();
  }, [id]);

  const outputText = run?.refine_output_text ?? run?.output_text;

  return (
    <div className="h-full flex flex-col gap-6">
      <h1 className="text-xl font-bold text-gray-900 shrink-0">
        Run <span className="font-mono text-sm text-gray-500">{id?.slice(0, 8)}</span>
      </h1>
      <div className="flex-1 grid grid-cols-2 gap-6 min-h-0">
        <StreamFeed events={events} running={streaming} />
        <div className="flex flex-col gap-4 overflow-auto">
          {outputText && (
            <div className="bg-white border rounded-lg p-4 text-sm text-gray-800 whitespace-pre-wrap flex-1 overflow-auto">
              {outputText}
            </div>
          )}
          {run?.pdf_available && (
            <a
              href={getPdfUrl(id!)}
              download
              className="inline-block bg-green-600 hover:bg-green-700 text-white text-sm font-medium rounded-lg px-4 py-2 text-center transition-colors"
            >
              Download PDF
            </a>
          )}
          {!streaming && run && (
            <RefinePanel
              runId={id!}
              onEvents={(refineEvents) => setEvents((prev) => [...prev, ...refineEvents])}
            />
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/RunView.tsx
git commit -m "feat: add RunView page with live stream and refine panel"
```

---

## Task 19: Sources, Voice, Skills pages

**Files:**
- Modify: `frontend/src/pages/Sources.tsx`
- Modify: `frontend/src/pages/Voice.tsx`
- Modify: `frontend/src/pages/Skills.tsx`

- [ ] **Step 1: Write Sources page**

```tsx
// frontend/src/pages/Sources.tsx
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getConfig, updateConfig } from "../api";

export default function Sources() {
  const qc = useQueryClient();
  const { data: config } = useQuery({ queryKey: ["config"], queryFn: getConfig });
  const [newUrl, setNewUrl] = useState("");

  const mutation = useMutation({
    mutationFn: (sources: string[]) => updateConfig({ sources }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["config"] }),
  });

  const sources = config?.sources ?? [];

  function add() {
    if (!newUrl.trim()) return;
    mutation.mutate([...sources, newUrl.trim()]);
    setNewUrl("");
  }

  function remove(url: string) {
    mutation.mutate(sources.filter((s) => s !== url));
  }

  return (
    <div className="max-w-xl space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Sources</h1>
      <div className="space-y-2">
        {sources.map((url) => (
          <div key={url} className="flex items-center justify-between bg-white border rounded-lg px-4 py-2">
            <span className="text-sm font-mono text-gray-700 truncate">{url}</span>
            <button onClick={() => remove(url)} className="text-red-400 hover:text-red-600 text-sm ml-4">
              Remove
            </button>
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          value={newUrl}
          onChange={(e) => setNewUrl(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && add()}
          placeholder="https://example.com"
          className="flex-1 border rounded-lg px-3 py-2 text-sm"
        />
        <button
          onClick={add}
          className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg px-4 py-2 transition-colors"
        >
          Add
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Write Voice page**

```tsx
// frontend/src/pages/Voice.tsx
import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getConfig, updateConfig } from "../api";

export default function Voice() {
  const qc = useQueryClient();
  const { data: config } = useQuery({ queryKey: ["config"], queryFn: getConfig });
  const [voice, setVoice] = useState("");

  useEffect(() => { if (config) setVoice(config.voice); }, [config]);

  const mutation = useMutation({
    mutationFn: (voice: string) => updateConfig({ voice }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["config"] }),
  });

  return (
    <div className="max-w-xl space-y-4">
      <h1 className="text-2xl font-bold text-gray-900">Voice</h1>
      <p className="text-sm text-gray-500">
        The system instruction that shapes the agent's editorial persona.
      </p>
      <textarea
        value={voice}
        onChange={(e) => setVoice(e.target.value)}
        rows={10}
        className="w-full border rounded-lg px-3 py-2 text-sm font-mono resize-y"
      />
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-400">{voice.length} characters</span>
        <button
          onClick={() => mutation.mutate(voice)}
          disabled={mutation.isPending}
          className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg px-4 py-2 transition-colors"
        >
          {mutation.isPending ? "Saving…" : "Save"}
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Write Skills page**

```tsx
// frontend/src/pages/Skills.tsx
import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getConfig, updateConfig } from "../api";

function parseFrontmatter(md: string): { name: string; description: string; body: string } {
  const match = md.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
  if (!match) return { name: "", description: "", body: md };
  const fm = match[1];
  const body = match[2].trim();
  const name = (fm.match(/^name:\s*(.+)$/m) ?? [])[1]?.trim() ?? "";
  const description = (fm.match(/^description:\s*(.+)$/m) ?? [])[1]?.trim() ?? "";
  return { name, description, body };
}

function buildFrontmatter(name: string, description: string, body: string): string {
  return `---\nname: ${name}\ndescription: ${description}\n---\n\n${body}`;
}

export default function Skills() {
  const qc = useQueryClient();
  const { data: config } = useQuery({ queryKey: ["config"], queryFn: getConfig });
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [body, setBody] = useState("");

  useEffect(() => {
    if (config) {
      const parsed = parseFrontmatter(config.skill_md);
      setName(parsed.name);
      setDescription(parsed.description);
      setBody(parsed.body);
    }
  }, [config]);

  const mutation = useMutation({
    mutationFn: () => updateConfig({ skill_md: buildFrontmatter(name, description, body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["config"] }),
  });

  return (
    <div className="max-w-xl space-y-4">
      <h1 className="text-2xl font-bold text-gray-900">Skills</h1>
      <p className="text-sm text-gray-500">
        The SKILL.md that tells the agent how to build the PDF.
      </p>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Name</label>
          <input value={name} onChange={(e) => setName(e.target.value)}
            className="w-full border rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Description</label>
          <input value={description} onChange={(e) => setDescription(e.target.value)}
            className="w-full border rounded-lg px-3 py-2 text-sm" />
        </div>
      </div>
      <textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        rows={14}
        className="w-full border rounded-lg px-3 py-2 text-sm font-mono resize-y"
      />
      <div className="flex justify-end">
        <button
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
          className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg px-4 py-2 transition-colors"
        >
          {mutation.isPending ? "Saving…" : "Save"}
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Sources.tsx frontend/src/pages/Voice.tsx frontend/src/pages/Skills.tsx
git commit -m "feat: add Sources, Voice, and Skills pages"
```

---

## Task 20: Agents and History pages

**Files:**
- Modify: `frontend/src/pages/Agents.tsx`
- Modify: `frontend/src/pages/History.tsx`

- [ ] **Step 1: Write Agents page**

```tsx
// frontend/src/pages/Agents.tsx
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listAgents, createAgent, deleteAgent } from "../api";

export default function Agents() {
  const qc = useQueryClient();
  const { data: agents = [] } = useQuery({ queryKey: ["agents"], queryFn: listAgents });
  const [id, setId] = useState("");
  const [description, setDescription] = useState("");

  const create = useMutation({
    mutationFn: () => createAgent({ id, description }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["agents"] }); setId(""); setDescription(""); },
  });

  const remove = useMutation({
    mutationFn: deleteAgent,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agents"] }),
  });

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Agents</h1>

      <div className="bg-white border rounded-xl p-5 space-y-3">
        <h2 className="text-sm font-semibold text-gray-700">Save current config as agent</h2>
        <div className="flex gap-3">
          <input value={id} onChange={(e) => setId(e.target.value)}
            placeholder="agent-id" className="flex-1 border rounded-lg px-3 py-2 text-sm" />
          <input value={description} onChange={(e) => setDescription(e.target.value)}
            placeholder="Description" className="flex-1 border rounded-lg px-3 py-2 text-sm" />
          <button
            onClick={() => create.mutate()}
            disabled={!id.trim() || create.isPending}
            className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg px-4 py-2 transition-colors"
          >
            {create.isPending ? "Saving…" : "Save"}
          </button>
        </div>
      </div>

      <div className="space-y-2">
        {agents.length === 0 && <p className="text-sm text-gray-400">No saved agents.</p>}
        {agents.map((a) => (
          <div key={a.id} className="bg-white border rounded-lg px-4 py-3 flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-900 font-mono">{a.id}</p>
              <p className="text-xs text-gray-400">{a.description || "No description"}</p>
            </div>
            <button
              onClick={() => remove.mutate(a.id)}
              className="text-red-400 hover:text-red-600 text-sm"
            >
              Delete
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Write History page**

```tsx
// frontend/src/pages/History.tsx
import { useQuery } from "@tanstack/react-query";
import { listRuns } from "../api";
import RunCard from "../components/RunCard";

export default function History() {
  const { data: runs = [] } = useQuery({ queryKey: ["runs"], queryFn: listRuns });

  return (
    <div className="max-w-2xl space-y-4">
      <h1 className="text-2xl font-bold text-gray-900">History</h1>
      {runs.length === 0 && (
        <p className="text-sm text-gray-400">No runs yet. Go to Dashboard to start one.</p>
      )}
      {runs.map((r) => <RunCard key={r.id} run={r} />)}
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Agents.tsx frontend/src/pages/History.tsx
git commit -m "feat: add Agents and History pages"
```

---

## Task 21: Final wiring and smoke test

**Files:**
- Modify: `frontend/index.html`

- [ ] **Step 1: Update index.html title**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Daily Digest</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 2: Run all backend tests**

```bash
uv run pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 3: Build frontend to verify no TypeScript errors**

```bash
cd frontend && npm run build
```

Expected: `dist/` created with no errors.

- [ ] **Step 4: Full smoke test**

In Terminal 1:
```bash
export GEMINI_API_KEY="your-key"
uv run uvicorn backend.main:app --reload
```

In Terminal 2:
```bash
cd frontend && npm run dev
```

Open http://localhost:5173 — navigate to each page and verify it renders.

- [ ] **Step 5: Final commit**

```bash
cd ..
git add frontend/index.html
git commit -m "feat: complete daily digest web app"
```
