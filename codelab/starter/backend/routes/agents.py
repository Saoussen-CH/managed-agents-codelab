import logging

from fastapi import APIRouter, HTTPException

from backend.models import CreateAgentRequest
from backend.services.agent_client import BASE_AGENT, _inline_sources, _make_client, _reset_client
from backend.services.storage import storage

log = logging.getLogger("digest.agents")
router = APIRouter(prefix="/api/agents", tags=["agents"])


def _get_client():
    return _make_client()


@router.get("")
def list_agents():
    # ── TODO 6a ─────────────────────────────────────────────────────────────
    # List all saved managed agents.
    # client.agents.list() returns an object with an .agents attribute.
    #
    # try:
    #     result = _get_client().agents.list()
    #     agents = result.agents or []
    #     return [
    #         {
    #             "id": a.id,
    #             "description": getattr(a, "description", ""),
    #             "base_agent": getattr(a, "base_agent", BASE_AGENT),
    #         }
    #         for a in agents
    #     ]
    # except Exception as exc:
    #     _reset_client()
    #     raise HTTPException(status_code=502, detail=str(exc))
    # ─────────────────────────────────────────────────────────────────────────
    return []


@router.post("", status_code=201)
def create_agent(req: CreateAgentRequest):
    config = storage.read_config()
    log.info("Creating agent — id=%s", req.id)

    # ── TODO 6b ─────────────────────────────────────────────────────────────
    # Save the current configuration as a managed agent.
    # base_environment bakes in AGENTS.md + SKILL.md so every future invocation
    # gets them automatically — no inline config needed at call time.
    #
    # agent = _get_client().agents.create(
    #     id=req.id,
    #     base_agent=BASE_AGENT,
    #     description=req.description,
    #     system_instruction=config.voice,
    #     tools=[
    #         {"type": "code_execution"},
    #         {"type": "google_search"},
    #         {"type": "url_context"},
    #     ],
    #     base_environment={
    #         "type": "remote",
    #         "sources": _inline_sources(config.agents_md, config.skill_md),
    #     },
    # )
    # log.info("Agent created — id=%s", getattr(agent, "id", req.id))
    # return {"id": getattr(agent, "id", req.id), "description": getattr(agent, "description", req.description)}
    # ─────────────────────────────────────────────────────────────────────────
    raise HTTPException(status_code=501, detail="TODO 6b not implemented — add agents.create()")


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
