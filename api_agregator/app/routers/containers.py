import logging
from fastapi import APIRouter, status

from app.services.update_containers import UpdateContainers
from app.db.redis.docker_containers import DockerContainers
from app.services.api_getaway import APIGateway

router = APIRouter()
logger = logging.getLogger(__name__)

DOCKER_SERVICE_URL = "http://localhost:8000"
docker_gateway = APIGateway(DOCKER_SERVICE_URL)

@router.patch("/update_containers", status_code=status.HTTP_200_OK)
async def update_containers():
    """
    Обновление информации о контейнерах
    """
    update_containers_service = UpdateContainers()
    update_containers_service.upload_containers()
    return {"message": "Containers updated successfully"}

@router.get("/containers", status_code=status.HTTP_200_OK)
async def get_containers(host: str = 'localhost') -> dict:
    docker_containers = DockerContainers()
    data = docker_containers.get_containers(host)
    return data


