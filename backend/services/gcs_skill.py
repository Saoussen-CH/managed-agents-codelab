from __future__ import annotations
import logging
import os

log = logging.getLogger("digest.gcs")

# Path inside the bucket where the skill is stored
SKILL_BLOB = "skills/digest-pdf/SKILL.md"
SKILL_PREFIX = "skills/digest-pdf"  # GCS directory mounted as skill source


def _bucket_name() -> str:
    name = os.environ.get("GCS_BUCKET", "managed-agents")
    log.debug("GCS bucket: %s", name)
    return name


def _ensure_bucket(client, bucket_name: str) -> None:
    """Create the bucket if it doesn't exist."""
    from google.cloud.exceptions import Conflict
    b = client.bucket(bucket_name)
    if not b.exists():
        log.info("Bucket %s not found — creating it", bucket_name)
        try:
            project = os.environ.get("GOOGLE_CLOUD_PROJECT")
            client.create_bucket(bucket_name, project=project)
            log.info("Bucket created: gs://%s", bucket_name)
        except Conflict:
            log.debug("Bucket already exists (race condition): %s", bucket_name)


def upload(skill_md: str, bucket_name: str | None = None) -> str:
    """
    Upload SKILL.md to GCS. Creates the bucket if it doesn't exist.
    Returns the gs:// path to the skill directory (used as source in base_environment).
    """
    from google.cloud import storage

    bucket = bucket_name or _bucket_name()
    log.info("Uploading SKILL.md to GCS — bucket=%s blob=%s", bucket, SKILL_BLOB)

    client = storage.Client()
    _ensure_bucket(client, bucket)

    b = client.bucket(bucket)
    blob = b.blob(SKILL_BLOB)
    blob.upload_from_string(skill_md.encode("utf-8"), content_type="text/plain")

    gcs_path = f"gs://{bucket}/{SKILL_PREFIX}"
    log.info("SKILL.md uploaded — gcs_path=%s", gcs_path)
    return gcs_path


def delete(bucket_name: str | None = None) -> None:
    """Remove the SKILL.md blob from GCS."""
    from google.cloud import storage

    bucket = bucket_name or _bucket_name()
    log.info("Deleting SKILL.md from GCS — bucket=%s blob=%s", bucket, SKILL_BLOB)
    try:
        client = storage.Client()
        client.bucket(bucket).blob(SKILL_BLOB).delete()
        log.info("SKILL.md deleted from GCS")
    except Exception as exc:
        log.warning("GCS delete failed (may not exist): %s", exc)


def exists(bucket_name: str | None = None) -> bool:
    """Check whether the SKILL.md blob exists in GCS."""
    from google.cloud import storage

    bucket = bucket_name or _bucket_name()
    try:
        client = storage.Client()
        return client.bucket(bucket).blob(SKILL_BLOB).exists()
    except Exception:
        return False


def gcs_source(gcs_path: str) -> dict:
    """Build the environment source dict for this GCS skill."""
    return {
        "type": "gcs",
        "source": gcs_path,
        "target": "/.agent/skills/digest-pdf",
    }
