from fastapi import APIRouter, Body
from backend.models import AppConfig
from backend.services.storage import storage

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("", response_model=AppConfig)
def get_config():
    return storage.read_config()


@router.put("", response_model=AppConfig)
def update_config(updates: dict = Body()):
    current = storage.read_config().model_dump()
    current.update({k: v for k, v in updates.items() if k in current})
    new_config = AppConfig.model_validate(current)
    storage.write_config(new_config)
    return new_config
