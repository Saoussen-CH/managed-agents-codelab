import logging
import time

from fastapi import APIRouter, HTTPException

from backend.models import CreateAgentRequest
from backend.services.agent_client import BASE_AGENT, _is_vertex, _make_client, _reset_client
from backend.services.storage import storage

log = logging.getLogger("digest.agents")
router = APIRouter(prefix="/api/agents", tags=["agents"])


def _get_client():
    return _make_client()


@router.get("")
def list_agents():
    try:
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
    except Exception as exc:
        _reset_client()
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("", status_code=201)
def create_agent(req: CreateAgentRequest):
    config = storage.read_config()
    log.info("Creating agent — id=%s", req.id)

    # On Vertex, network is denied by default — include allowlist so agent can fetch URLs
    base_env: dict = {
        "type": "remote",
        "sources": [
            {"type": "inline", "target": ".agents/AGENTS.md", "content": config.agents_md},
            {"type": "inline", "target": ".agents/skills/digest-pdf/SKILL.md", "content": config.skill_md},
        ],
    }
    if _is_vertex():
        base_env["network"] = {"allowlist": [{"domain": "*"}]}

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
        base_environment=base_env,
    )

    # Vertex: agents.create() is an LRO — agent.id is None until provisioning completes.
    # Poll client.agents.get() until the agent is ready (up to 60 s).
    if _is_vertex() and not getattr(agent, "id", None):
        log.info("Waiting for agent provisioning — id=%s", req.id)
        for attempt in range(12):
            time.sleep(5)
            try:
                agent = _get_client().agents.get(id=req.id)
                if getattr(agent, "id", None):
                    break
            except Exception as poll_exc:
                log.warning("Polling attempt %d failed: %s", attempt + 1, poll_exc)
        if not getattr(agent, "id", None):
            log.warning("Agent provisioning timed out — returning requested id=%s", req.id)
            return {"id": req.id, "description": req.description}

    log.info("Agent created — id=%s", getattr(agent, "id", req.id))
    return {"id": agent.id, "description": getattr(agent, "description", req.description)}


@router.get("/{agent_id}")
def get_agent(agent_id: str):
    try:
        a = _get_client().agents.get(id=agent_id)
        return {
            "id": a.id,
            "description": getattr(a, "description", ""),
            "base_agent": getattr(a, "base_agent", BASE_AGENT),
        }
    except Exception:
        raise HTTPException(status_code=404, detail="Agent not found")


@router.delete("/{agent_id}", status_code=204)
def delete_agent(agent_id: str):
    try:
        _get_client().agents.delete(id=agent_id)
        log.info("Agent deleted — id=%s", agent_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Agent not found")
