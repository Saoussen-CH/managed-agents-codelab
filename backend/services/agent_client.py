from __future__ import annotations
import asyncio
import logging
import os
import subprocess
import tarfile
import tempfile
import threading
from pathlib import Path

import requests as http_requests

log = logging.getLogger("digest.agent")

BASE_AGENT = "antigravity-preview-05-2026"


def _is_vertex() -> bool:
    return os.environ.get("USE_VERTEX", "").lower() in ("1", "true", "yes")


_client_singleton = None
_client_lock = threading.Lock()


def _make_client():
    """Return a thread-safe module-level singleton. Creates once on first call."""
    global _client_singleton
    if _client_singleton is not None:
        return _client_singleton

    with _client_lock:
        if _client_singleton is not None:  # double-checked — another thread may have created it
            return _client_singleton

        from google import genai
        if _is_vertex():
            project = os.environ.get("GOOGLE_CLOUD_PROJECT")
            location = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
            if not project:
                raise RuntimeError("GOOGLE_CLOUD_PROJECT must be set when USE_VERTEX=true")
            log.info("Creating Vertex AI client — project=%s location=%s", project, location)
            for _key in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
                os.environ.pop(_key, None)
            _client_singleton = genai.Client(enterprise=True, project=project, location=location)
        else:
            log.info("Creating Gemini API client")
            _client_singleton = genai.Client()

    return _client_singleton


def _reset_client() -> None:
    """Discard the singleton so the next call creates a fresh client."""
    global _client_singleton
    with _client_lock:
        _client_singleton = None


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


def _skill_sources(
    agents_md: str,
    skill_md: str,
    skill_registry_name: str | None = None,
    gcs_skill_path: str | None = None,
) -> list[dict]:
    """
    Return environment sources for AGENTS.md and SKILL.md.

    Priority on Vertex:
      1. GCS source  (if gcs_skill_path is set)
      2. Skill Registry (if skill_registry_name is set)
      3. Inline fallback

    Gemini API: always inline (GCS/Registry not needed, no size limit issues).
    """
    if _is_vertex() and gcs_skill_path:
        return [
            {"type": "inline", "target": "/.agent/AGENTS.md", "content": agents_md},
            {"type": "gcs", "source": gcs_skill_path, "target": "/.agent/skills/digest-pdf"},
        ]

    if _is_vertex() and skill_registry_name:
        return [
            {"type": "inline", "target": "/.agent/AGENTS.md", "content": agents_md},
            {"type": "skill_registry", "source": skill_registry_name, "target": "/.agent/skills/"},
        ]

    # Inline fallback (Gemini API, or Vertex with no GCS/registry configured)
    agent_targets = (
        [".agents/AGENTS.md", "/.agent/AGENTS.md"] if _is_vertex() else [".agents/AGENTS.md"]
    )
    skill_targets = (
        [".agents/skills/digest-pdf/SKILL.md", "/.agent/skills/digest-pdf/SKILL.md"]
        if _is_vertex()
        else [".agents/skills/digest-pdf/SKILL.md"]
    )
    return (
        [{"type": "inline", "target": t, "content": agents_md} for t in agent_targets]
        + [{"type": "inline", "target": t, "content": skill_md} for t in skill_targets]
    )


def _base_environment(extra_sources: list[dict] | None = None) -> dict:
    """Vertex network is denied by default — always add allowlist when on Vertex."""
    env: dict = {"type": "remote"}
    if extra_sources:
        env["sources"] = extra_sources
    if _is_vertex():
        env["network"] = {"allowlist": [{"domain": "*"}]}
    return env


def _handle_event(event, put, text_parts: list[str]) -> tuple[str | None, str | None]:
    """
    Process one stream event. Calls put() immediately for displayable steps.
    Appends text to text_parts for Vertex DeltaText chunks.
    Returns (env_id, interaction_id) if found in this event, else (None, None).
    """
    event_type = getattr(event, "event_type", None)
    env_id = None
    iid = None

    if event_type is None:
        # Gemini API — raw event object
        put({"type": "step", "content": str(event)[:400]})

    elif event_type == "interaction.created":
        put({"type": "step", "content": "⚡ Interaction started"})

    elif event_type == "step.start":
        step = getattr(event, "step", None)
        if step:
            stype = getattr(step, "type", "")
            name = getattr(step, "name", "")
            if stype == "function_call" and name:
                put({"type": "step", "content": f"🔧 {name}"})
            elif stype == "mcp_server_tool_call" and name:
                server = getattr(step, "server_name", "")
                put({"type": "step", "content": f"🔧 {name} (MCP: {server})" if server else f"🔧 {name}"})
            elif stype == "code_execution_call":
                args = getattr(step, "arguments", None)
                code_preview = getattr(args, "code", "")[:80] if args else ""
                put({"type": "step", "content": f"🖥️ Running code… {code_preview}"})
            elif stype == "url_context_call":
                args = getattr(step, "arguments", None)
                urls = getattr(args, "urls", []) if args else []
                put({"type": "step", "content": f"🌐 Fetching {urls[0] if urls else 'URL'}…"})
            elif stype == "google_search_call":
                args = getattr(step, "arguments", None)
                queries = getattr(args, "queries", []) if args else []
                put({"type": "step", "content": f"🔍 Searching: {queries[0] if queries else '…'}"})
            elif stype == "model_output":
                put({"type": "step", "content": "✍️ Writing response…"})

    elif event_type == "step.delta":
        delta = getattr(event, "delta", None)
        if delta:
            dtype = getattr(delta, "type", "")
            if dtype == "text":
                # Accumulate text — don't push individual chunks (too noisy)
                text_parts.append(getattr(delta, "text", ""))
            elif dtype == "function_result":
                result = getattr(delta, "result", None)
                if result:
                    put({"type": "step", "content": f"  → {str(result)[:300]}"})
            elif dtype == "code_execution_result":
                result = getattr(delta, "result", "")
                if result:
                    put({"type": "step", "content": f"  📤 {str(result)[:300]}"})
            elif dtype == "arguments_delta":
                # SDK exposes as delta.arguments (partial_arguments in REST JSON)
                args = getattr(delta, "arguments", "") or getattr(delta, "partial_arguments", "")
                if args:
                    put({"type": "step", "content": f"  {args[:300]}"})

    elif event_type == "interaction.completed":
        interaction = getattr(event, "interaction", None)
        if interaction:
            env_id = getattr(interaction, "environment_id", None)
            iid = getattr(interaction, "id", None)
            usage = getattr(interaction, "usage", None)
            if usage:
                log.info(
                    "Usage — input=%s output=%s total=%s",
                    getattr(usage, "total_input_tokens", "?"),
                    getattr(usage, "total_output_tokens", "?"),
                    getattr(usage, "total_tokens", "?"),
                )

    return env_id, iid


def _create_with_provisioning_retry(client, kwargs: dict, put) -> object:
    """Retry on Vertex 'Provisioning is in progress' 500 with exponential backoff."""
    import time

    max_attempts = 5
    delay = 5

    for attempt in range(1, max_attempts + 1):
        try:
            return client.interactions.create(**kwargs)
        except Exception as exc:
            if "Provisioning is in progress" in str(exc) and attempt < max_attempts:
                log.info("Sandbox provisioning — retrying in %ds (%d/%d)", delay, attempt, max_attempts)
                put({"type": "step", "content": f"⏳ Sandbox provisioning… retrying in {delay}s ({attempt}/{max_attempts})"})
                time.sleep(delay)
                delay = min(delay * 2, 30)
            else:
                raise


def _stream_sync(
    agent_id: str | None,
    config: dict,
    queue: asyncio.Queue,
    loop: asyncio.AbstractEventLoop,
) -> None:
    """Runs in thread executor. Pushes SSE event dicts live into the asyncio queue."""
    client = _make_client()
    put = lambda event: loop.call_soon_threadsafe(queue.put_nowait, event)

    try:
        prompt = _build_prompt(config["sources"])
        log.info("Starting interaction — agent=%s sources=%d", agent_id or BASE_AGENT, len(config["sources"]))

        kwargs: dict = {"agent": agent_id or BASE_AGENT, "input": prompt, "stream": True}
        if _is_vertex():
            kwargs["background"] = True
            kwargs["store"] = True

        if agent_id:
            if not _is_vertex():
                kwargs["environment"] = "remote"
            # Vertex: omit environment — agent's base_environment used automatically
        else:
            kwargs["system_instruction"] = config["voice"]
            kwargs["environment"] = _base_environment(
                extra_sources=_skill_sources(
                    config["agents_md"],
                    config["skill_md"],
                    config.get("skill_registry_name"),
                    config.get("gcs_skill_path"),
                )
            )

        stream = _create_with_provisioning_retry(client, kwargs, put)

        text_parts: list[str] = []
        env_id = None
        iid = None
        last = None
        step_count = 0

        for event in stream:
            last = event
            step_count += 1
            log.debug("Step %d: %s", step_count, str(event)[:120])
            e, i = _handle_event(event, put, text_parts)
            if e:
                env_id = e
            if i:
                iid = i

        # env_id / iid come from InteractionCompletedEvent (in _handle_event).
        # Fallback: some SDK versions expose these on the stream object after iteration.
        if not env_id:
            env_id = getattr(stream, "environment_id", None) or (getattr(last, "environment_id", None) if last else None)
        if not iid:
            iid = getattr(stream, "id", None) or (getattr(last, "id", None) if last else None)

        # Per API reference: InteractionCompletedEvent carries EMPTY outputs.
        # All text comes from StepDelta(type="text") events accumulated in text_parts.
        output = "".join(text_parts) if text_parts else None

        log.info("Interaction complete — steps=%d env=%s interaction=%s", step_count, env_id, iid)
        put({"type": "output", "content": output or "", "environment_id": env_id, "interaction_id": iid})
        put({"type": "done", "pdf_available": True})

    except Exception as exc:
        log.error("Interaction failed: %s", exc)
        _reset_client()  # discard broken client so next run starts fresh
        put({"type": "error", "message": str(exc)})
    finally:
        put(None)


def _refine_sync(
    environment_id: str,
    interaction_id: str,
    message: str,
    agent_id: str | None,
    queue: asyncio.Queue,
    loop: asyncio.AbstractEventLoop,
) -> None:
    """Runs in thread executor. Streams a refinement turn live."""
    client = _make_client()
    put = lambda event: loop.call_soon_threadsafe(queue.put_nowait, event)

    try:
        log.info("Starting refinement — env=%s previous=%s", environment_id, interaction_id)

        kwargs: dict = {
            "agent": agent_id or BASE_AGENT,
            "input": message,
            "environment": environment_id,
            "previous_interaction_id": interaction_id,
            "stream": True,
        }
        if _is_vertex():
            kwargs["background"] = True
            kwargs["store"] = True

        stream = _create_with_provisioning_retry(client, kwargs, put)

        text_parts: list[str] = []
        iid = None
        last = None
        step_count = 0

        for event in stream:
            last = event
            step_count += 1
            log.debug("Refine step %d: %s", step_count, str(event)[:120])
            _, i = _handle_event(event, put, text_parts)
            if i:
                iid = i

        if not iid:
            iid = getattr(stream, "id", None) or (getattr(last, "id", None) if last else None)
        output = "".join(text_parts) if text_parts else None

        log.info("Refinement complete — steps=%d interaction=%s", step_count, iid)
        put({"type": "output", "content": output or "", "interaction_id": iid})
        put({"type": "done", "pdf_available": True})

    except Exception as exc:
        log.error("Refinement failed: %s", exc)
        _reset_client()
        put({"type": "error", "message": str(exc)})
    finally:
        put(None)


def download_pdf(environment_id: str) -> bytes:
    """Download the PDF from the environment snapshot."""
    log.info("Downloading PDF snapshot — env=%s surface=%s",
             environment_id, "Vertex AI" if _is_vertex() else "Gemini API")

    with tempfile.TemporaryDirectory() as tmp:
        tar_path = Path(tmp) / "snapshot.tar"

        if _is_vertex():
            token = subprocess.check_output(
                ["gcloud", "auth", "print-access-token"], text=True
            ).strip()
            # Try the Gemini API endpoint first (same underlying storage, works with bearer token)
            url = f"https://generativelanguage.googleapis.com/v1beta/files/environment-{environment_id}:download"
            log.info("Trying Gemini API download endpoint for Vertex env: %s", url)
            r = http_requests.get(
                url,
                params={"alt": "media"},
                headers={"Authorization": f"Bearer {token}"},
                allow_redirects=True,
            )
            if r.status_code == 404:
                # Fallback: try aiplatform endpoint
                project = os.environ["GOOGLE_CLOUD_PROJECT"]
                location = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
                url2 = (
                    f"https://aiplatform.googleapis.com/v1beta1/projects/{project}"
                    f"/locations/{location}/files/environment-{environment_id}:download"
                )
                log.info("Falling back to aiplatform endpoint: %s", url2)
                r = http_requests.get(
                    url2,
                    params={"alt": "media"},
                    headers={"Authorization": f"Bearer {token}"},
                    allow_redirects=True,
                )
            log.info("Download response — status=%d content-type=%s size=%d",
                     r.status_code, r.headers.get("content-type", "?"), len(r.content))
        else:
            api_key = os.environ["GEMINI_API_KEY"]
            url = f"https://generativelanguage.googleapis.com/v1beta/files/environment-{environment_id}:download"
            log.info("Downloading from Gemini API: %s", url)
            r = http_requests.get(
                url,
                params={"alt": "media"},
                headers={"x-goog-api-key": api_key},
                allow_redirects=True,
            )
            log.info("Download response — status=%d content-type=%s size=%d",
                     r.status_code, r.headers.get("content-type", "?"), len(r.content))

        if not r.ok:
            log.error("Download failed — status=%d body=%s", r.status_code, r.text[:500])
        r.raise_for_status()
        tar_path.write_bytes(r.content)

        with tarfile.open(tar_path) as tar:
            tar.extractall(path=tmp, filter="data")

        pdf_path = Path(tmp) / "workspace" / "digest.pdf"
        if not pdf_path.exists():
            raise FileNotFoundError("digest.pdf not found in environment snapshot")
        size = pdf_path.stat().st_size
        log.info("PDF downloaded — %d bytes", size)
        return pdf_path.read_bytes()
