from fastapi import APIRouter, HTTPException
from google import genai
from backend.models import CreateAgentRequest
from backend.services.storage import storage
from backend.services.agent_client import BASE_AGENT

router = APIRouter(prefix="/api/agents", tags=["agents"])

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client()
    return _client


@router.get("")
def list_agents():
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


@router.post("", status_code=201)
def create_agent(req: CreateAgentRequest):
    config = storage.read_config()
    agent = _get_client().agents.create(
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
    except Exception:
        raise HTTPException(status_code=404, detail="Agent not found")
