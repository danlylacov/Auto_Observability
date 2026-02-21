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

@router.post("/container/stop", status_code=status.HTTP_200_OK)
async def stop_container(id: str, host: str = 'localhost') -> dict:
    result = docker_gateway.make_request(
        method="POST",
        endpoint="/api/v1/manage/container/stop",
        json_data={
            "container": {
                "id": id
            }
        }
    )
    return result


@router.delete("/container/remove", status_code=status.HTTP_200_OK)
async def remove_container(id: str, force: bool = False, host: str = 'localhost') -> dict:
    result = docker_gateway.make_request(
        method="DELETE",
        endpoint="/api/v1/manage/container/remove",
        params={
            "force": force
        },
        json_data={
            "container": {
                "id": id
            }
        }
    )
    return result


@router.post("/container/start", status_code=status.HTTP_200_OK)
async def start_container(id: str, host: str = 'localhost') -> dict:
    result = docker_gateway.make_request(
        method="POST",
        endpoint="/api/v1/manage/container/start",
        json_data={
            "container": {
                "id": id
            }
        }
    )
    return result


@router.delete("/volume/remove", status_code=status.HTTP_200_OK)
async def remove_volume(volume_name: str, force: bool = False, host: str = 'localhost') -> dict:
    result = docker_gateway.make_request(
        method="DELETE",
        endpoint="/api/v1/manage/volume/remove",
        params={
            "force": force
        },
        json_data={
            "volume_name": volume_name
        }
    )
    return result


@router.post("/volumes/prune", status_code=status.HTTP_200_OK)
async def prune_volumes(host: str = 'localhost') -> dict:
    result = docker_gateway.make_request(
        method="POST",
        endpoint="/api/v1/manage/volumes/prune"
    )
    return result


@router.delete("/image/remove", status_code=status.HTTP_200_OK)
async def remove_image(image_id_or_name: str, force: bool = False, host: str = 'localhost') -> dict:
    result = docker_gateway.make_request(
        method="DELETE",
        endpoint="/api/v1/manage/image/remove",
        params={
            "force": force
        },
        json_data={
            "image_id_or_name": image_id_or_name
        }
    )
    return result


@router.post("/system/cleanup", status_code=status.HTTP_200_OK)
async def cleanup_system(host: str = 'localhost') -> dict:
    result = docker_gateway.make_request(
        method="POST",
        endpoint="/api/v1/manage/system/cleanup"
    )
    return result




