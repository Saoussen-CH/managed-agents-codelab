import asyncio
import logging
import os

from fastapi import APIRouter, HTTPException

from backend.services import gcs_skill, skill_registry
from backend.services.storage import storage

log = logging.getLogger("digest.skills")
router = APIRouter(prefix="/api/skills", tags=["skills"])


def _require_vertex() -> str:
    if os.environ.get("USE_VERTEX", "").lower() not in ("1", "true", "yes"):
        raise HTTPException(status_code=400, detail="Only available in Vertex AI mode (USE_VERTEX=true)")
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project:
        raise HTTPException(status_code=400, detail="GOOGLE_CLOUD_PROJECT must be set")
    return project


# ── GCS endpoints ──────────────────────────────────────────────────────────────

@router.post("/gcs/upload")
async def upload_to_gcs():
    """Upload SKILL.md to GCS. Runs in a thread executor (network I/O)."""
    _require_vertex()
    config = storage.read_config()
    bucket = os.environ.get("GCS_BUCKET", "managed-agents")

    loop = asyncio.get_running_loop()
    try:
        gcs_path = await loop.run_in_executor(
            None, gcs_skill.upload, config.skill_md, bucket
        )
    except Exception as exc:
        log.error("GCS upload failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))

    config.gcs_skill_path = gcs_path
    storage.write_config(config)
    log.info("GCS skill path saved: %s", gcs_path)
    return {"gcs_skill_path": gcs_path}


@router.get("/gcs/status")
def gcs_status():
    """Check whether SKILL.md exists in GCS."""
    _require_vertex()
    bucket = os.environ.get("GCS_BUCKET", "managed-agents")
    uploaded = gcs_skill.exists(bucket)
    config = storage.read_config()
    return {"uploaded": uploaded, "gcs_skill_path": config.gcs_skill_path}


@router.delete("/gcs/remove", status_code=204)
def remove_from_gcs():
    """Delete SKILL.md from GCS and clear the stored path."""
    _require_vertex()
    bucket = os.environ.get("GCS_BUCKET", "managed-agents")
    gcs_skill.delete(bucket)
    config = storage.read_config()
    config.gcs_skill_path = None
    storage.write_config(config)
    return


# ── Skill Registry endpoints (kept for future use) ─────────────────────────────

@router.post("/publish")
async def publish_skill():
    """Upload to Vertex AI Skill Registry (requires project enrollment)."""
    project = _require_vertex()
    config = storage.read_config()

    loop = asyncio.get_running_loop()
    try:
        name = await loop.run_in_executor(
            None, skill_registry.publish, config.skill_md, project
        )
    except Exception as exc:
        msg = str(exc)
        log.error("Skill Registry publish failed: %s", msg)
        if "The project doesn't exist" in msg:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Skill Registry is not available for this project. "
                    "Use GCS upload instead — it works identically."
                ),
            )
        raise HTTPException(status_code=502, detail=msg)

    config.skill_registry_name = name
    storage.write_config(config)
    return {"skill_registry_name": name}


@router.delete("/unpublish", status_code=204)
def unpublish_skill():
    project = _require_vertex()
    skill_registry.unpublish(project)
    config = storage.read_config()
    config.skill_registry_name = None
    storage.write_config(config)
    return
