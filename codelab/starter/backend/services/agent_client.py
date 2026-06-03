from __future__ import annotations
import asyncio
import logging
import os
import tarfile
import tempfile
import threading
from pathlib import Path

import requests as http_requests
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("digest.agent")

BASE_AGENT = "antigravity-preview-05-2026"

_client_singleton = None
_client_lock = threading.Lock()


# TODO 1: Create the Gemini API client
# genai.Client() reads GEMINI_API_KEY from the environment automatically.
# It is the entry point for all Managed Agents API operations.
# Add the import and client creation inside _make_client() below:
#   from google import genai
#   log.info("Creating Gemini API client")
#   _client_singleton = genai.Client()
def _make_client():
    """Return a thread-safe module-level singleton."""
    global _client_singleton
    if _client_singleton is not None:
        return _client_singleton
    with _client_lock:
        if _client_singleton is not None:
            return _client_singleton
        # TODO 1: add genai import and genai.Client() here
        raise RuntimeError("TODO 1 not implemented — create genai.Client() in _make_client()")
    return _client_singleton


def _reset_client() -> None:
    global _client_singleton
    with _client_lock:
        _client_singleton = None


def _build_prompt(sources: list[str]) -> str:
    return (
        "You're building a daily tech digest.\n\n"
        "For each source below:\n"
        + "\n".join(f"- {s}" for s in sources)
        + "\n\n"
        "Steps:\n"
        "1. Fetch each homepage.\n"
        "2. Extract the top 3 headlines per source.\n"
        "3. Write the full digest as formatted text — grouped by source, "
        "2-3 sentence summary per story. Include a 'Skip This' section.\n"
        "4. Output the complete written digest BEFORE generating the PDF.\n"
        "5. Then generate the PDF using the digest-pdf skill."
    )


def _inline_sources(agents_md: str, skill_md: str) -> list[dict]:
    """Build the inline sources list for AGENTS.md and SKILL.md."""
    return [
        {"type": "inline", "target": ".agents/AGENTS.md", "content": agents_md},
        {"type": "inline", "target": ".agents/skills/digest-pdf/SKILL.md", "content": skill_md},
    ]


def _handle_event(event, put, text_parts: list[str]) -> tuple[str | None, str | None]:
    """Dispatch one stream event to the SSE queue and accumulate text."""
    event_type = getattr(event, "event_type", None)
    env_id = None
    iid = None

    if event_type is None:
        put({"type": "step", "content": str(event)[:400]})

    elif event_type == "interaction.created":
        put({"type": "step", "content": "⚡ Interaction started"})

    elif event_type == "step.start":
        step = getattr(event, "step", None)
        if step:
            stype = getattr(step, "type", "")
            name  = getattr(step, "name", "")
            if stype == "function_call" and name:
                put({"type": "step", "content": f"🔧 {name}"})
            elif stype == "code_execution_call":
                args = getattr(step, "arguments", None)
                put({"type": "step", "content": f"🖥️ Running code… {getattr(args, 'code', '')[:80] if args else ''}"})
            elif stype == "url_context_call":
                args = getattr(step, "arguments", None)
                urls = getattr(args, "urls", []) if args else []
                put({"type": "step", "content": f"🌐 Fetching {urls[0] if urls else 'URL'}…"})
            elif stype == "google_search_call":
                args = getattr(step, "arguments", None)
                queries = getattr(args, "queries", []) if args else []
                put({"type": "step", "content": f"🔍 Searching: {queries[0] if queries else '…'}"})
            elif stype == "model_output":
                # Clear earlier narration — the LAST model_output is the actual digest
                text_parts.clear()
                put({"type": "step", "content": "✍️ Writing response…"})

    elif event_type == "step.delta":
        delta = getattr(event, "delta", None)
        if delta:
            dtype = getattr(delta, "type", "")
            if dtype == "text":
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
                args = getattr(delta, "arguments", "") or getattr(delta, "partial_arguments", "")
                if args:
                    put({"type": "step", "content": f"  {args[:300]}"})

    elif event_type == "interaction.completed":
        # TODO 4: Extract environment_id and interaction_id from the completed event
        # These are needed for:
        #   - multi-turn refinement (TODO 5): resume the same sandbox
        #   - file download: download digest.pdf from the sandbox
        # The text output does NOT come from this event — it accumulates in text_parts above.
        #
        # interaction = getattr(event, "interaction", None)
        # if interaction:
        #     env_id = getattr(interaction, "environment_id", None)
        #     iid    = getattr(interaction, "id", None)
        #     usage  = getattr(interaction, "usage", None)
        #     if usage:
        #         log.info("Usage — input=%s output=%s total=%s",
        #             getattr(usage, "total_input_tokens", "?"),
        #             getattr(usage, "total_output_tokens", "?"),
        #             getattr(usage, "total_tokens", "?"))
        pass

    return env_id, iid


def _stream_sync(
    agent_id: str | None,
    config: dict,
    queue: asyncio.Queue,
    loop: asyncio.AbstractEventLoop,
) -> None:
    """Runs in a thread executor. Pushes SSE event dicts live into the asyncio queue."""
    client = _make_client()
    put = lambda event: loop.call_soon_threadsafe(queue.put_nowait, event)

    try:
        prompt = _build_prompt(config["sources"])
        log.info("Starting interaction — agent=%s sources=%d",
                 agent_id or BASE_AGENT, len(config["sources"]))

        # TODO 2: Build the kwargs dict for interactions.create()
        # Required fields: agent, input, stream=True
        # stream=True returns an iterable of events instead of waiting for the full result.
        #
        # kwargs: dict = {
        #     "agent": agent_id or BASE_AGENT,
        #     "input": prompt,
        #     "stream": True,
        # }
        kwargs: dict = {}

        # TODO 3: Add system_instruction and environment to kwargs
        # The environment parameter provisions the Linux sandbox and mounts your config files.
        #
        # Case A — Using a saved agent (agent_id is set):
        #   kwargs["environment"] = "remote"
        #   "remote" forks a fresh sandbox from the agent's base_environment.
        #   Your AGENTS.md and SKILL.md are already baked in — no inline config needed.
        #
        # Case B — Using inline config (no saved agent):
        #   if agent_id:
        #       kwargs["environment"] = "remote"
        #   else:
        #       kwargs["system_instruction"] = config["voice"]
        #       kwargs["environment"] = {
        #           "type": "remote",
        #           "sources": _inline_sources(config["agents_md"], config["skill_md"]),
        #       }
        #   _inline_sources() mounts two files into the sandbox at startup:
        #     .agents/AGENTS.md                       → persistent behavioural rules
        #     .agents/skills/digest-pdf/SKILL.md      → PDF skill auto-discovered by the harness

        if not kwargs:
            put({"type": "error", "message": "TODO 2 and 3 not implemented yet"})
            return

        stream = client.interactions.create(**kwargs)

        text_parts: list[str] = []
        env_id = None
        iid = None
        last = None
        step_count = 0

        for event in stream:
            last = event
            step_count += 1
            log.debug("event[%d] type=%s", step_count,
                      getattr(event, "event_type", type(event).__name__))
            e, i = _handle_event(event, put, text_parts)
            if e:
                env_id = e
            if i:
                iid = i

        if not env_id:
            env_id = getattr(stream, "environment_id", None) or (
                getattr(last, "environment_id", None) if last else None)
        if not iid:
            iid = getattr(stream, "id", None) or (
                getattr(last, "id", None) if last else None)
        output = "".join(text_parts) if text_parts else None

        log.info("Interaction complete — steps=%d env=%s interaction=%s",
                 step_count, env_id, iid)
        put({"type": "output", "content": output or "",
             "environment_id": env_id, "interaction_id": iid})
        put({"type": "done", "pdf_available": True})

    except Exception as exc:
        log.error("Interaction failed: %s", exc)
        _reset_client()
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
    """Runs in a thread executor. Streams a multi-turn refinement turn."""
    client = _make_client()
    put = lambda event: loop.call_soon_threadsafe(queue.put_nowait, event)

    try:
        log.info("Starting refinement — env=%s previous=%s",
                 environment_id, interaction_id)

        # TODO 5: Implement multi-turn refinement
        # The Interactions API tracks two independent dimensions:
        #   environment=environment_id          → reuse files, installed packages, sandbox state
        #   previous_interaction_id=...         → continue conversation context and reasoning trace
        # Both are required to resume exactly where the previous turn left off.
        #
        # stream = client.interactions.create(
        #     agent=agent_id or BASE_AGENT,
        #     input=message,
        #     environment=environment_id,
        #     previous_interaction_id=interaction_id,
        #     stream=True,
        # )
        put({"type": "error",
             "message": "TODO 5 not implemented — add multi-turn call"})
        put(None)
        return

        # (runs once TODO 5 is complete)
        text_parts: list[str] = []  # noqa
        iid = None
        last = None
        step_count = 0
        for event in stream:  # noqa
            last = event
            step_count += 1
            _, i = _handle_event(event, put, text_parts)
            if i:
                iid = i
        if not iid:
            iid = getattr(stream, "id", None) or (  # noqa
                getattr(last, "id", None) if last else None)
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
    """Download the PDF from the environment snapshot via the Files API."""
    log.info("Downloading PDF snapshot — env=%s", environment_id)
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
        size = pdf_path.stat().st_size
        log.info("PDF downloaded — %d bytes", size)
        return pdf_path.read_bytes()
