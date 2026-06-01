import asyncio
import logging
import os

from fastapi import APIRouter, HTTPException

from backend.services import skill_registry
from backend.services.storage import storage

log = logging.getLogger("digest.skills")
router = APIRouter(prefix="/api/skills", tags=["skills"])


def _require_vertex() -> str:
    if os.environ.get("USE_VERTEX", "").lower() not in ("1", "true", "yes"):
        raise HTTPException(status_code=400, detail="Skill Registry is only available in Vertex AI mode (USE_VERTEX=true)")
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project:
        raise HTTPException(status_code=400, detail="GOOGLE_CLOUD_PROJECT must be set")
    return project


@router.post("/publish")
async def publish_skill():
    """
    Upload the current SKILL.md to the Vertex AI Skill Registry.
    Runs in a thread executor — publishing takes ~30s and must not block the event loop.
    """
    project = _require_vertex()
    config = storage.read_config()

    loop = asyncio.get_running_loop()
    try:
        name = await loop.run_in_executor(
            None, skill_registry.publish, config.skill_md, project
        )
    except Exception as exc:
        log.error("Skill publish failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))

    config.skill_registry_name = name
    storage.write_config(config)
    log.info("Skill registry name saved: %s", name)
    return {"skill_registry_name": name}


@router.get("/status")
def skill_status():
    """Check whether the current skill is published to the registry."""
    project = _require_vertex()
    return skill_registry.get_status(project)


@router.delete("/unpublish", status_code=204)
def unpublish_skill():
    """Remove the skill from the registry and clear the stored name."""
    project = _require_vertex()
    skill_registry.unpublish(project)
    config = storage.read_config()
    config.skill_registry_name = None
    storage.write_config(config)
    return
