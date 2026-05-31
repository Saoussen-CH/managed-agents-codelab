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
    """Return a module-level singleton client. Creates it once on first call."""
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
        log.info("Auth: using Application Default Credentials (run 'gcloud auth application-default login' if not set)")
        _client_singleton = genai.Client(vertexai=True, project=project, location=location)
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
    """Build environment config. On Vertex, network is denied by default — add allowlist."""
    env: dict = {"type": "remote"}
    if extra_sources:
        env["sources"] = extra_sources
    if _is_vertex():
        env["network"] = {"allowlist": [{"domain": "*"}]}
    return env


def _stream_sync(
    agent_id: str | None,
    config: dict,
    queue: asyncio.Queue,
    loop: asyncio.AbstractEventLoop,
) -> None:
    """Runs in a thread executor. Pushes SSE event dicts into the asyncio queue."""
    client = _make_client()
    put = lambda event: loop.call_soon_threadsafe(queue.put_nowait, event)

    try:
        prompt = _build_prompt(config["sources"])
        log.info("Starting interaction — agent=%s sources=%d",
                 agent_id or BASE_AGENT, len(config["sources"]))

        kwargs: dict = {
            "agent": agent_id or BASE_AGENT,
            "input": prompt,
            "stream": True,
        }

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

        stream = client.interactions.create(**kwargs)

        last = None
        step_count = 0
        for event in stream:
            last = event
            step_count += 1
            log.debug("Step %d: %s", step_count, str(event)[:120])
            put({"type": "step", "content": str(event)})

        env_id = getattr(stream, "environment_id", None) or getattr(last, "environment_id", None)
        iid = getattr(stream, "id", None) or getattr(last, "id", None)
        output = getattr(stream, "output_text", None) or getattr(last, "output_text", None)

        log.info("Interaction complete — steps=%d env=%s interaction=%s", step_count, env_id, iid)
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
    """Runs in a thread executor. Streams a refinement turn."""
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

        last = None
        step_count = 0
        for event in stream:
            last = event
            step_count += 1
            log.debug("Refine step %d: %s", step_count, str(event)[:120])
            put({"type": "step", "content": str(event)})

        output = getattr(stream, "output_text", None) or getattr(last, "output_text", None)
        iid = getattr(stream, "id", None) or getattr(last, "id", None)

        log.info("Refinement complete — steps=%d interaction=%s", step_count, iid)
        put({"type": "output", "content": output or "", "interaction_id": iid})
        put({"type": "done", "pdf_available": True})

    except Exception as exc:
        log.error("Refinement failed: %s", exc)
        put({"type": "error", "message": str(exc)})
    finally:
        put(None)


def download_pdf(environment_id: str) -> bytes:
    """Download the PDF from the environment snapshot and return its bytes."""
    log.info("Downloading PDF snapshot — env=%s surface=%s",
             environment_id, "Vertex AI" if _is_vertex() else "Gemini API")

    with tempfile.TemporaryDirectory() as tmp:
        tar_path = Path(tmp) / "snapshot.tar"

        if _is_vertex():
            # Vertex: use gcloud to get a token and hit the aiplatform endpoint
            project = os.environ["GOOGLE_CLOUD_PROJECT"]
            location = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
            token = subprocess.check_output(
                ["gcloud", "auth", "print-access-token"], text=True
            ).strip()
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
