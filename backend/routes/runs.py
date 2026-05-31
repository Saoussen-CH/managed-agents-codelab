from __future__ import annotations
import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from sse_starlette.sse import EventSourceResponse

from backend.models import RefineRequest, RunRecord, RunStatus, StartRunRequest
from backend.services import agent_client
from backend.services.storage import storage

log = logging.getLogger("digest.runs")
router = APIRouter(prefix="/api/runs", tags=["runs"])

_run_queues: dict[str, asyncio.Queue] = {}
_refine_queues: dict[str, asyncio.Queue] = {}


@router.post("", status_code=202)
async def start_run(req: StartRunRequest):
    run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    run = RunRecord(id=run_id, started_at=now, agent_id=req.agent_id)
    storage.write_run(run)
    log.info("Run created — id=%s agent=%s", run_id, req.agent_id or "inline")

    queue: asyncio.Queue = asyncio.Queue()
    _run_queues[run_id] = queue
    config = storage.read_config().model_dump()
    loop = asyncio.get_running_loop()

    async def background():
        await loop.run_in_executor(
            None, agent_client._stream_sync, req.agent_id, config, queue, loop
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


@router.get("/{run_id}/stream")
async def stream_run(run_id: str):
    run = storage.read_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    queue = _run_queues.get(run_id)

    async def event_generator():
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
                current = storage.read_run(run_id)
                if current and current.status != RunStatus.failed:
                    current.status = RunStatus.completed
                    storage.write_run(current)
                    log.info("Run completed — id=%s", run_id)
                _run_queues.pop(run_id, None)
                break

            if event.get("type") == "output":
                current = storage.read_run(run_id)
                if current:
                    current.output_text = event.get("content")
                    current.environment_id = event.get("environment_id")
                    current.interaction_id = event.get("interaction_id")
                    current.pdf_available = True
                    storage.write_run(current)

            if event.get("type") == "error":
                log.error("Run failed — id=%s error=%s", run_id, event.get("message"))
                current = storage.read_run(run_id)
                if current:
                    current.status = RunStatus.failed
                    current.error = event.get("message")
                    storage.write_run(current)

            yield {"data": json.dumps(event)}

    return EventSourceResponse(event_generator())


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


@router.post("/{run_id}/refine", status_code=202)
async def start_refine(run_id: str, req: RefineRequest):
    run = storage.read_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if not run.environment_id or not run.interaction_id:
        raise HTTPException(status_code=400, detail="Run has no environment to refine")

    log.info("Refinement started — run=%s", run_id)
    queue: asyncio.Queue = asyncio.Queue()
    _refine_queues[run_id] = queue
    loop = asyncio.get_running_loop()

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
                if current and current.status != RunStatus.failed:
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
