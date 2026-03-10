import logging

from fastapi import APIRouter, status

from app.models.classificate import ContainerInspectData
from app.services.docker_clasification import WeightedDiscovery

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", status_code=status.HTTP_200_OK)
async def classificate(container_attrs: ContainerInspectData) -> dict:
    """
    Классифицировать контейнер по технологиям.

    Args:
        container_attrs: Данные инспекции контейнера

    Returns:
        dict: Результат классификации с технологиями и баллами или ошибка
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
        logger.error(f"Error classifying container: {str(e)}", exc_info=True)
        return {"error": str(e)}
