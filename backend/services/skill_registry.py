from __future__ import annotations
import logging
import re
import tempfile
from pathlib import Path

log = logging.getLogger("digest.skills")

SKILL_ID = "digest-pdf"
SKILL_LOCATION = "us-central1"


def _resource_name(project: str) -> str:
    return f"projects/{project}/locations/{SKILL_LOCATION}/skills/{SKILL_ID}"


def _parse_description(skill_md: str) -> str:
    match = re.search(r"^description:\s*(.+)$", skill_md, re.MULTILINE)
    return match.group(1).strip() if match else "Tech digest PDF skill."


def _get_client(project: str):
    # Use agentplatform.Client as documented for google-cloud-aiplatform >= 1.154.0
    import agentplatform
    log.debug("Creating agentplatform.Client — project=%s location=%s", project, SKILL_LOCATION)
    return agentplatform.Client(project=project, location=SKILL_LOCATION)


def publish(skill_md: str, project: str) -> str:
    """
    Upload SKILL.md to the Vertex AI Skill Registry.
    Uses agentplatform.Client (google-cloud-aiplatform >= 1.154.0).
    skill_id is a top-level parameter in this version.
    Returns the skill resource name.
    """
    log.info("Starting skill publish — project=%s location=%s skill_id=%s", project, SKILL_LOCATION, SKILL_ID)
    client = _get_client(project)
    name = _resource_name(project)
    log.info("Skill resource name: %s", name)

    # Delete existing skill first (skill IDs are reserved for 24h after deletion)
    try:
        log.debug("Attempting to delete existing skill: %s", name)
        client.skills.delete(name=name)
        log.info("Deleted existing skill: %s", SKILL_ID)
    except Exception as exc:
        log.debug("Delete skipped (skill may not exist yet): %s", exc)

    with tempfile.TemporaryDirectory() as tmp:
        skill_dir = Path(tmp) / SKILL_ID
        skill_dir.mkdir()
        skill_md_path = skill_dir / "SKILL.md"
        skill_md_path.write_text(skill_md, encoding="utf-8")
        log.debug("SKILL.md written — %d bytes at %s", skill_md_path.stat().st_size, skill_md_path)

        description = _parse_description(skill_md)
        log.info("Calling client.skills.create — skill_id=%s display_name=digest-pdf", SKILL_ID)
        log.debug("  local_path=%s", str(skill_dir))

        try:
            # >= 1.154.0 API: skill_id is a top-level parameter, not inside config
            skill = client.skills.create(
                skill_id=SKILL_ID,
                display_name="digest-pdf",
                description=description,
                config={"local_path": str(skill_dir)},
            )
        except Exception as exc:
            log.error("client.skills.create failed: %s", exc)
            log.error("  type=%s project=%s location=%s", type(exc).__name__, project, SKILL_LOCATION)
            raise

    resource = getattr(skill, "name", name)
    state = getattr(skill, "state", "unknown")
    log.info("Skill published — name=%s state=%s", resource, state)
    return resource


def unpublish(project: str) -> None:
    log.info("Deleting skill — project=%s skill=%s", project, SKILL_ID)
    client = _get_client(project)
    try:
        client.skills.delete(name=_resource_name(project))
        log.info("Skill deleted: %s", SKILL_ID)
    except Exception as exc:
        log.warning("Skill delete failed (may not exist): %s", exc)


def get_status(project: str) -> dict:
    log.debug("Checking skill status — project=%s", project)
    client = _get_client(project)
    name = _resource_name(project)
    try:
        skill = client.skills.get(name=name)
        result = {
            "published": True,
            "name": getattr(skill, "name", name),
            "state": getattr(skill, "state", "unknown"),
            "display_name": getattr(skill, "display_name", SKILL_ID),
        }
        log.debug("Skill status: %s", result)
        return result
    except Exception as exc:
        log.debug("Skill not found: %s", exc)
        return {"published": False, "name": None, "state": None, "display_name": None}
