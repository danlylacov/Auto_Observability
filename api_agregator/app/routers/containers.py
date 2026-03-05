import logging

from fastapi import APIRouter, status, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.services.update_containers import UpdateContainers
from app.db.redis.docker_containers import DockerContainers
from app.services.api_getaway import APIGateway
from app.services.hosts_service import HostsService
from app.db.postgres.database import get_db
from app.models.postgres.container import Container
from app.models.postgres.prometheus_config import PrometheusConfig


router = APIRouter()
logger = logging.getLogger(__name__)


@router.patch("/update_containers", status_code=status.HTTP_200_OK)
async def update_containers(db: Session = Depends(get_db)):
    """
    Обновление информации о контейнерах по всем хостам.
    """
    update_containers_service = UpdateContainers(db=db)
    update_containers_service.upload_containers()
    return {"message": "Containers updated successfully"}


@router.get("/containers", status_code=status.HTTP_200_OK)
async def get_containers(
    host_id: str | None = Query(default=None, description="Идентификатор целевого хоста"),
    db: Session = Depends(get_db),
) -> dict:
    docker_containers = DockerContainers()
    data = docker_containers.get_containers(host_name=host_id)
    
    if not data:
        return data
    
    container_ids = list(data.keys())
    
    containers_in_db = db.query(Container).filter(
        Container.id.in_(container_ids)
    ).all()
    containers_set = {c.id for c in containers_in_db}
    
    active_configs = db.query(PrometheusConfig).filter(
        PrometheusConfig.container_id.in_(container_ids),
        PrometheusConfig.status == "active"
    ).all()
    config_map = {config.container_id: config for config in active_configs}
    
    for container_id, container_data in data.items():
        if isinstance(container_data, dict):
            container_data['has_prometheus_config'] = (
                container_id in containers_set and 
                container_id in config_map
            )
    
    return data


@router.post("/container/stop", status_code=status.HTTP_200_OK)
async def stop_container(
    id: str,
    host_id: str = Query(..., description="Идентификатор хоста, на котором запущен контейнер"),
    db: Session = Depends(get_db),
) -> dict:
    hosts_service = HostsService(db)
    host_dto = hosts_service.get_host_by_id(host_id)
    if not host_dto:
        raise HTTPException(status_code=404, detail="Host not found")

    docker_gateway = APIGateway(host_dto.base_url)

    result = docker_gateway.make_request(
        method="POST",
        endpoint="/api/v1/manage/container/stop",
        json_data={"id": id},
    )

    update_containers_service = UpdateContainers(db=db)
    update_containers_service.upload_containers()
    return result


@router.delete("/container/remove", status_code=status.HTTP_200_OK)
async def remove_container(
    id: str,
    host_id: str = Query(..., description="Идентификатор хоста, на котором запущен контейнер"),
    force: bool = False,
    db: Session = Depends(get_db),
) -> dict:
    hosts_service = HostsService(db)
    host_dto = hosts_service.get_host_by_id(host_id)
    if not host_dto:
        raise HTTPException(status_code=404, detail="Host not found")

    docker_gateway = APIGateway(host_dto.base_url)

    result = docker_gateway.make_request(
        method="DELETE",
        endpoint="/api/v1/manage/container/remove",
        params={"force": force},
        json_data={"id": id},
    )

    update_containers_service = UpdateContainers(db=db)
    update_containers_service.upload_containers()
    return result


@router.post("/container/start", status_code=status.HTTP_200_OK)
async def start_container(
    id: str,
    host_id: str = Query(..., description="Идентификатор хоста, на котором должен быть запущен контейнер"),
    db: Session = Depends(get_db),
) -> dict:
    hosts_service = HostsService(db)
    host_dto = hosts_service.get_host_by_id(host_id)
    if not host_dto:
        raise HTTPException(status_code=404, detail="Host not found")

    docker_gateway = APIGateway(host_dto.base_url)

    result = docker_gateway.make_request(
        method="POST",
        endpoint="/api/v1/manage/container/start",
        json_data={"id": id},
    )

    update_containers_service = UpdateContainers(db=db)
    update_containers_service.upload_containers()
    return result













"""@router.delete("/volume/remove", status_code=status.HTTP_200_OK)
async def remove_volume(volume_name: str, force: bool = False) -> dict:
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
    update_containers_service.upload_containers()
    return result


@router.post("/volumes/prune", status_code=status.HTTP_200_OK)
async def prune_volumes() -> dict:
    result = docker_gateway.make_request(
        method="POST",
        endpoint="/api/v1/manage/volumes/prune"
    )
    update_containers_service.upload_containers()
    return result


@router.delete("/image/remove", status_code=status.HTTP_200_OK)
async def remove_image(image_id_or_name: str, force: bool = False) -> dict:
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
    update_containers_service.upload_containers()
    return result


@router.post("/system/cleanup", status_code=status.HTTP_200_OK)
async def cleanup_system() -> dict:
    result = docker_gateway.make_request(
        method="POST",
        endpoint="/api/v1/manage/system/cleanup"
    )
    update_containers_service.upload_containers()
    return result
"""