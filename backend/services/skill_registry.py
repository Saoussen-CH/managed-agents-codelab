from __future__ import annotations
import logging
import re
import tempfile
from pathlib import Path

log = logging.getLogger("digest.skills")

SKILL_ID = "digest-pdf"
# Skill Registry uses us-central1 (not global like Interactions API)
SKILL_LOCATION = "us-central1"


def _resource_name(project: str) -> str:
    return f"projects/{project}/locations/{SKILL_LOCATION}/skills/{SKILL_ID}"


def _parse_description(skill_md: str) -> str:
    """Extract description from SKILL.md YAML front matter."""
    match = re.search(r"^description:\s*(.+)$", skill_md, re.MULTILINE)
    return match.group(1).strip() if match else "Tech digest PDF skill."


def _get_client(project: str):
    import vertexai
    vertexai.init(project=project, location=SKILL_LOCATION)
    return vertexai.Client(project=project, location=SKILL_LOCATION)


def publish(skill_md: str, project: str) -> str:
    """
    Upload SKILL.md to the Vertex AI Skill Registry.
    Deletes the existing skill first if present (skills are immutable revisions,
    so we delete + recreate to update content).
    Returns the skill resource name.
    """
    client = _get_client(project)
    name = _resource_name(project)

    # Delete existing skill if present
    try:
        client.skills.delete(name=name)
        log.info("Deleted existing skill: %s", SKILL_ID)
    except Exception:
        pass  # skill didn't exist yet

    with tempfile.TemporaryDirectory() as tmp:
        skill_dir = Path(tmp) / SKILL_ID
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")

        log.info("Publishing skill — id=%s project=%s location=%s", SKILL_ID, project, SKILL_LOCATION)
        skill = client.skills.create(
            display_name="digest-pdf",
            description=_parse_description(skill_md),
            config={
                "skill_id": SKILL_ID,
                "local_path": str(skill_dir),
            },
        )

    resource = getattr(skill, "name", name)
    state = getattr(skill, "state", "unknown")
    log.info("Skill published — name=%s state=%s", resource, state)
    return resource


def unpublish(project: str) -> None:
    """Delete the skill from the registry."""
    client = _get_client(project)
    try:
        client.skills.delete(name=_resource_name(project))
        log.info("Skill deleted from registry: %s", SKILL_ID)
    except Exception as exc:
        log.warning("Skill delete failed (may not exist): %s", exc)


def get_status(project: str) -> dict:
    """Return current skill status from the registry."""
    client = _get_client(project)
    name = _resource_name(project)
    try:
        skill = client.skills.get(name=name)
        return {
            "published": True,
            "name": getattr(skill, "name", name),
            "state": getattr(skill, "state", "unknown"),
            "display_name": getattr(skill, "display_name", SKILL_ID),
        }
    except Exception:
        return {"published": False, "name": None, "state": None, "display_name": None}
