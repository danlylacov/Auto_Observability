import logging
from typing import Optional
from fastapi import APIRouter, status, HTTPException
from app.services.docker_clasification import WeightedDiscovery
from app.models.classificate import ContainerInspectData


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", status_code=status.HTTP_200_OK)
async def classificate(container_attrs: ContainerInspectData) -> dict:
    """
    Классифицировать контейнер
    """
    try:
        discovery = WeightedDiscovery()
        result = discovery.classify_container(
            container_attrs.labels,
            container_attrs.envs,
            container_attrs.image,
            container_attrs.ports)
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}
