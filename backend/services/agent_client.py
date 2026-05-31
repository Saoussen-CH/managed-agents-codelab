from __future__ import annotations
import asyncio
import logging
import os
import subprocess
import tarfile
import tempfile
from pathlib import Path

import requests as http_requests

log = logging.getLogger("digest.agent")

BASE_AGENT = "antigravity-preview-05-2026"


def _is_vertex() -> bool:
    return os.environ.get("USE_VERTEX", "").lower() in ("1", "true", "yes")


_client_singleton = None


def _make_client():
    """Return a module-level singleton. Creates once on first call."""
    global _client_singleton
    if _client_singleton is not None:
        return _client_singleton

    from google import genai
    if _is_vertex():
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
        if not project:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT must be set when USE_VERTEX=true")
        log.info("Creating Vertex AI client — project=%s location=%s", project, location)
        # Strip API key vars — Vertex uses ADC (OAuth2), not API keys.
        for _key in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
            os.environ.pop(_key, None)
        # Notebooks use enterprise=True (not vertexai=True)
        _client_singleton = genai.Client(enterprise=True, project=project, location=location)
    else:
        log.info("Creating Gemini API client")
        _client_singleton = genai.Client()

    return _client_singleton


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


def _base_environment(extra_sources: list[dict] | None = None) -> dict:
    """Vertex network is denied by default — always add allowlist when on Vertex."""
    env: dict = {"type": "remote"}
    if extra_sources:
        env["sources"] = extra_sources
    if _is_vertex():
        env["network"] = {"allowlist": [{"domain": "*"}]}
    return env


def _parse_events(stream) -> tuple[list[str], str | None, str | None, str | None]:
    """
    Iterate stream events. Returns (step_contents, output_text, env_id, interaction_id).

    Handles two event formats:
    - Gemini API: raw objects with output_text/environment_id/id on stream after iteration
    - Vertex AI: typed objects (StepStart/StepDelta/InteractionCompletedEvent) —
                 text in StepDelta.delta.text, IDs in InteractionCompletedEvent.interaction
    """
    steps: list[str] = []
    text_parts: list[str] = []
    env_id = None
    iid = None
    last = None

    for event in stream:
        last = event
        event_type = getattr(event, "event_type", None)

        if event_type is None:
            # Gemini API — raw event, stringify for display
            steps.append(str(event)[:300])
            continue

        # Vertex typed events
        if event_type == "step.start":
            step = getattr(event, "step", None)
            if step:
                stype = getattr(step, "type", "")
                name = getattr(step, "name", "")
                if stype == "function_call" and name:
                    steps.append(f"🔧 {name}")
                elif stype == "model_output":
                    steps.append("✍️ Writing response…")

        elif event_type == "step.delta":
            delta = getattr(event, "delta", None)
            if delta:
                dtype = getattr(delta, "type", "")
                if dtype == "text":
                    chunk = getattr(delta, "text", "")
                    if chunk:
                        text_parts.append(chunk)
                elif dtype == "function_result":
                    result = getattr(delta, "result", None)
                    if result:
                        steps.append(f"  → {str(result)[:200]}")
                elif dtype == "arguments_delta":
                    args = getattr(delta, "arguments", "")
                    if args:
                        steps.append(f"  {args[:200]}")

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

        elif event_type == "interaction.created":
            steps.append("⚡ Interaction started")

    # Gemini API: env_id and iid are on the stream object after iteration
    if not env_id:
        env_id = getattr(stream, "environment_id", None) or getattr(last, "environment_id", None)
    if not iid:
        iid = getattr(stream, "id", None) or getattr(last, "id", None)

    # Output text: Vertex accumulates from DeltaText; Gemini API has output_text on stream
    output = "".join(text_parts) if text_parts else (
        getattr(stream, "output_text", None) or getattr(last, "output_text", None)
    )

    return steps, output, env_id, iid


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
    """Runs in thread executor. Pushes SSE event dicts into the asyncio queue."""
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
            kwargs["environment"] = _base_environment()
        else:
            kwargs["system_instruction"] = config["voice"]
            kwargs["environment"] = _base_environment(extra_sources=[
                {"type": "inline", "target": ".agents/AGENTS.md", "content": config["agents_md"]},
                {"type": "inline", "target": ".agents/skills/digest-pdf/SKILL.md", "content": config["skill_md"]},
            ])

        stream = _create_with_provisioning_retry(client, kwargs, put)
        steps, output, env_id, iid = _parse_events(stream)

        for step in steps:
            put({"type": "step", "content": step})

        log.info("Interaction complete — env=%s interaction=%s", env_id, iid)
        put({"type": "output", "content": output or "", "environment_id": env_id, "interaction_id": iid})
        put({"type": "done", "pdf_available": True})

    except Exception as exc:
        log.error("Interaction failed: %s", exc)
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
    """Runs in thread executor. Streams a refinement turn."""
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

        stream = client.interactions.create(**kwargs)
        steps, output, _, iid = _parse_events(stream)

        for step in steps:
            put({"type": "step", "content": step})

        log.info("Refinement complete — interaction=%s", iid)
        put({"type": "output", "content": output or "", "interaction_id": iid})
        put({"type": "done", "pdf_available": True})

    except Exception as exc:
        log.error("Refinement failed: %s", exc)
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
            project = os.environ["GOOGLE_CLOUD_PROJECT"]
            location = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
            token = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
            r = http_requests.get(
                f"https://aiplatform.googleapis.com/v1beta1/projects/{project}"
                f"/locations/{location}/files/environment-{environment_id}:download",
                params={"alt": "media"},
                headers={"Authorization": f"Bearer {token}"},
                allow_redirects=True,
            )
        else:
            api_key = os.environ["GEMINI_API_KEY"]
            r = http_requests.get(
                f"https://generativelanguage.googleapis.com/v1beta/files/environment-{environment_id}:download",
                params={"alt": "media"},
                headers={"x-goog-api-key": api_key},
                allow_redirects=True,
            )

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
