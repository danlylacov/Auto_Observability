"""Containers API router module."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.postgres.database import get_db
from app.db.redis.docker_containers import DockerContainers
from app.models.postgres.container import Container
from app.models.postgres.prometheus_config import PrometheusConfig
from app.services.api_getaway import APIGateway
from app.services.hosts_service import HostsService
from app.services.minio_service import MinioService
from app.services.update_containers import UpdateContainers

router = APIRouter()
logger = logging.getLogger(__name__)


@router.patch("/update_containers", status_code=status.HTTP_200_OK)
async def update_containers(db: Session = Depends(get_db)):
    """
    Обновление информации о контейнерах по всем хостам.

    Args:
        db: Сессия базы данных

    Returns:
        dict: Сообщение об успешном обновлении
    """
    update_containers_service = UpdateContainers(db=db)
    update_containers_service.upload_containers()
    return {"message": "Containers updated successfully"}


@router.get("/containers", status_code=status.HTTP_200_OK)
async def get_containers(
    host_id: str | None = Query(default=None, description="Идентификатор целевого хоста"),
    db: Session = Depends(get_db),
) -> dict:
    """
    Получение списка контейнеров с информацией о конфигурации Prometheus.

    Args:
        host_id: Идентификатор хоста для фильтрации. Если None, возвращает все контейнеры.
        db: Сессия базы данных

    Returns:
        dict: Словарь с данными о контейнерах (container_id -> data)
    """
    docker_containers = DockerContainers()
    data = docker_containers.get_containers(host_name=host_id)

    if not data:
        return data

    container_ids = list(data.keys())

    containers_in_db = db.query(Container).filter(
        Container.id.in_(container_ids)
    ).all()
    containers_set = {c.id: c for c in containers_in_db}

    all_configs = db.query(PrometheusConfig).filter(
        PrometheusConfig.container_id.in_(container_ids)
    ).all()

    config_map = {}
    for config in all_configs:
        if config.container_id not in config_map:
            config_map[config.container_id] = config
        else:
            existing = config_map[config.container_id]
            if config.status == "active" and existing.status != "active":
                config_map[config.container_id] = config
            elif config.status == existing.status:
                if config.created_at and existing.created_at:
                    if config.created_at > existing.created_at:
                        config_map[config.container_id] = config

    all_containers_data = docker_containers.get_containers()

    exporter_index_by_host = {}
    exporter_index_by_name = {}

    for exp_id, exp_data in all_containers_data.items():
        if isinstance(exp_data, dict):
            exp_name = exp_data.get("info", {}).get("Name", "").lstrip("/")
            exp_host = exp_data.get("host_name") or exp_data.get("host_id")

            if exp_name and "-exporter" in exp_name.lower():
                exp_name_lower = exp_name.lower()

                if exp_host:
                    key = (exp_host, exp_name_lower)
                    exporter_index_by_host[key] = {
                        "container_id": exp_id,
                        "data": exp_data
                    }

                if exp_name_lower not in exporter_index_by_name:
                    exporter_index_by_name[exp_name_lower] = []
                exporter_index_by_name[exp_name_lower].append({
                    "container_id": exp_id,
                    "data": exp_data,
                    "host": exp_host
                })

    for container_id, container_data in data.items():
        if not isinstance(container_data, dict):
            continue

        has_config = container_id in config_map
        container_data['has_prometheus_config'] = has_config

        if has_config:
            try:
                config = config_map[container_id]
                config_metadata = config.config_metadata or {}

                config_host_name = (
                    config_metadata.get('host_name') or
                    host_id or
                    container_data.get('host_name') or
                    container_data.get('host_id')
                )

                container_name = container_data.get("info", {}).get("Name", "").lstrip("/")
                if not container_name and container_id in containers_set:
                    container_name = containers_set[container_id].name.lstrip("/")
                if not container_name:
                    container_name = (
                        config.container_name.lstrip("/")
                        if config.container_name else ""
                    )

                exporter_info = None
                exporter_running = False
                exporter_container_id = None

                if container_name:
                    exporter_name = f"{container_name}-exporter"
                    exporter_name_lower = exporter_name.lower()

                    if config_host_name:
                        exporter_key = (config_host_name, exporter_name_lower)
                        if exporter_key in exporter_index_by_host:
                            exporter_entry = exporter_index_by_host[exporter_key]
                            exp_data = exporter_entry["data"]
                            exp_status = exp_data.get("info", {}).get("State", {}).get("Status", "")
                            exporter_running = exp_status.lower() in ("running", "up")
                            exporter_container_id = exporter_entry["container_id"]

                            exporter_info = {
                                "container_id": exporter_container_id,
                                "name": (
                                    exp_data.get("info", {})
                                    .get("Name", "")
                                    .lstrip("/")
                                ),
                                "status": exp_status,
                                "image": (
                                    exp_data.get("info", {})
                                    .get("Config", {})
                                    .get("Image", "")
                                ),
                            }

                            logger.debug(
                                "Found exporter %s on host %s: "
                                "status=%s, running=%s",
                                exporter_name, config_host_name,
                                exp_status, exporter_running
                            )

                    if not exporter_info and exporter_name_lower in exporter_index_by_name:
                        exporter_candidates = exporter_index_by_name[exporter_name_lower]
                        if exporter_candidates:
                            exporter_entry = exporter_candidates[0]
                            exp_data = exporter_entry["data"]
                            exp_status = exp_data.get("info", {}).get("State", {}).get("Status", "")
                            exporter_running = exp_status.lower() in ("running", "up")
                            exporter_container_id = exporter_entry["container_id"]

                            exporter_info = {
                                "container_id": exporter_container_id,
                                "name": (
                                    exp_data.get("info", {})
                                    .get("Name", "")
                                    .lstrip("/")
                                ),
                                "status": exp_status,
                                "image": (
                                    exp_data.get("info", {})
                                    .get("Config", {})
                                    .get("Image", "")
                                ),
                            }

                            found_host = exporter_entry.get("host")
                            logger.info(
                                "Found exporter %s using fallback search. "
                                "Expected host: %s, found host: %s, "
                                "status=%s, running=%s",
                                exporter_name, config_host_name,
                                found_host, exp_status, exporter_running
                            )
                    else:
                        logger.debug(
                            "Exporter %s not found. "
                            "Available exporters in index: %s",
                            exporter_name,
                            list(exporter_index_by_name.keys())[:10]
                        )

                container_data['prometheus_config'] = {
                    "config_id": config.id,
                    "status": config.status,
                    "stack": config.stack,
                    "exporter_image": config.exporter_image,
                    "exporter_port": config.exporter_port,
                    "job_name": config.job_name,
                    "created_at": config.created_at.isoformat() if config.created_at else None,
                    "exporter": {
                        "exists": exporter_info is not None,
                        "running": exporter_running,
                        "container_id": exporter_container_id,
                        "info": exporter_info
                    }
                }
            except Exception as e:
                logger.error(
                    "Error processing prometheus config for container %s: %s",
                    container_id, str(e),
                    exc_info=True
                )
                container_data['prometheus_config'] = None
                container_data['has_prometheus_config'] = False
        else:
            container_data['prometheus_config'] = None

    return data


@router.post("/container/stop", status_code=status.HTTP_200_OK)
async def stop_container(
    container_id: str = Query(..., alias="id", description="Идентификатор контейнера"),
    host_id: str = Query(
        ..., description="Идентификатор хоста, на котором запущен контейнер"
    ),
    db: Session = Depends(get_db),
) -> dict:
    """
    Остановка контейнера.

    Args:
        container_id: Идентификатор контейнера
        host_id: Идентификатор хоста, на котором запущен контейнер
        db: Сессия базы данных

    Returns:
        dict: Результат операции остановки контейнера

    Raises:
        HTTPException: Если хост не найден
    """
    logger.info("Stopping container %s on host %s", container_id, host_id)
    try:
        hosts_service = HostsService(db)
        host_dto = hosts_service.get_host_by_id(host_id)
        if not host_dto:
            logger.error("Host not found: %s", host_id)
            raise HTTPException(status_code=404, detail="Host not found")

        # Преобразуем адрес хоста для Docker (localhost -> host.docker.internal)
        host_address = hosts_service._resolve_host_for_docker(host_dto.host)
        docker_api_url = f"http://{host_address}:{host_dto.port}"
        logger.info(
            "Resolved host address: %s -> %s, using URL: %s",
            host_dto.host, host_address, docker_api_url
        )
        # Создаем APIGateway с правильным URL
        docker_gateway = APIGateway(docker_api_url)
        # Увеличиваем таймаут для операций с контейнерами (остановка может занять время)
        docker_gateway.timeout = 30
        # Увеличиваем таймаут для операций с контейнерами (остановка может занять время)
        docker_gateway.timeout = 30
        logger.info("Timeout set to: %s", docker_gateway.timeout)

        result = docker_gateway.make_request(
            method="POST",
            endpoint="/api/v1/manage/container/stop",
            json_data={"id": container_id},
        )

        update_containers_service = UpdateContainers(db=db)
        update_containers_service.upload_containers()
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error stopping container %s on host %s: %s",
            container_id, host_id, str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop container: {str(e)}"
        )


@router.delete("/container/remove", status_code=status.HTTP_200_OK)
async def remove_container(
    container_id: str = Query(..., alias="id", description="Идентификатор контейнера"),
    host_id: str = Query(
        ..., description="Идентификатор хоста, на котором запущен контейнер"
    ),
    force: bool = False,
    db: Session = Depends(get_db),
) -> dict:
    """
    Удаление контейнера и связанных ресурсов.

    Удаляет контейнер, его экспортер (если существует), конфигурации Prometheus
    и файлы из MinIO.

    Args:
        container_id: Идентификатор контейнера
        host_id: Идентификатор хоста, на котором запущен контейнер
        force: Принудительное удаление
        db: Сессия базы данных

    Returns:
        dict: Результат операции удаления контейнера

    Raises:
        HTTPException: Если хост не найден или произошла ошибка при удалении из БД
    """
    hosts_service = HostsService(db)
    host_dto = hosts_service.get_host_by_id(host_id)
    if not host_dto:
        raise HTTPException(status_code=404, detail="Host not found")

    # Преобразуем адрес хоста для Docker (localhost -> host.docker.internal)
    host_address = hosts_service._resolve_host_for_docker(host_dto.host)
    docker_api_url = f"http://{host_address}:{host_dto.port}"

    container = db.query(Container).filter(Container.id == container_id).first()
    container_name = None
    if container:
        container_name = container.name.lstrip("/")

    if not container_name:
        docker_containers = DockerContainers()
        container_data = docker_containers.get_container(container_id, host_id)
        if container_data:
            container_info = container_data.get("info", {})
            container_name = (
                container_info.get("Name", "").lstrip("/") or
                container_info.get("Config", {}).get("Hostname", "")
            )

    docker_gateway = APIGateway(docker_api_url)
    # Увеличиваем таймаут для операций с контейнерами (удаление может занять время)
    docker_gateway.timeout = 30

    if container_name:
        exporter_name = f"{container_name}-exporter"
        try:
            exporter_result = docker_gateway.make_request(
                method="DELETE",
                endpoint="/api/v1/manage/container/remove",
                params={"force": True},
                json_data={"id": exporter_name},
            )
            logger.info(
                "Exporter %s removal attempted: %s",
                exporter_name, exporter_result
            )
        except Exception as e:
            logger.warning(
                "Could not remove exporter %s: %s",
                exporter_name, str(e)
            )

    try:
        result = docker_gateway.make_request(
            method="DELETE",
            endpoint="/api/v1/manage/container/remove",
            params={"force": force},
            json_data={"id": container_id},
        )
    except Exception as e:
        logger.warning(
            "Error removing container %s via Docker API: %s",
            container_id, str(e)
        )
        result = {
            "message": (
                f"Container removal attempted, "
                f"but Docker API error: {str(e)}"
            )
        }

    try:
        minio_service = MinioService()

        if container:
            configs_to_delete = db.query(PrometheusConfig).filter(
                PrometheusConfig.container_id == container_id
            ).all()

            for config in configs_to_delete:
                if config.minio_file_path:
                    bucket = config.minio_bucket or 'prometheus'
                    prefix = config.minio_file_path.rstrip('/')
                    deleted_count = minio_service.delete_files_by_prefix(
                        prefix=prefix,
                        bucket=bucket
                    )
                    logger.info(
                        "Deleted %s files from MinIO for config %s "
                        "(prefix: %s)",
                        deleted_count, config.id, prefix
                    )

            db.delete(container)
            db.commit()
            logger.info(
                "Container %s and its Prometheus configs removed from database",
                container_id
            )
        else:
            configs_to_delete = db.query(PrometheusConfig).filter(
                PrometheusConfig.container_id == container_id
            ).all()
            if configs_to_delete:
                for config in configs_to_delete:
                    if config.minio_file_path:
                        bucket = config.minio_bucket or 'prometheus'
                        prefix = config.minio_file_path.rstrip('/')
                        deleted_count = minio_service.delete_files_by_prefix(
                            prefix=prefix,
                            bucket=bucket
                        )
                        logger.info(
                            "Deleted %s files from MinIO for config %s "
                            "(prefix: %s)",
                            deleted_count, config.id, prefix
                        )

                for config in configs_to_delete:
                    db.delete(config)
                db.commit()
                logger.info(
                    "Prometheus configs for container %s removed from database",
                    container_id
                )
    except Exception as e:
        logger.error(
            "Error removing container %s from database: %s",
            container_id, str(e)
        )
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove container from database: {str(e)}"
        ) from e

    update_containers_service = UpdateContainers(db=db)
    update_containers_service.upload_containers()

    return result


@router.post("/container/start", status_code=status.HTTP_200_OK)
async def start_container(
    container_id: str = Query(..., alias="id", description="Идентификатор контейнера"),
    host_id: str = Query(
        ...,
        description=(
            "Идентификатор хоста, "
            "на котором должен быть запущен контейнер"
        )
    ),
    db: Session = Depends(get_db),
) -> dict:
    """
    Запуск контейнера.

    Args:
        container_id: Идентификатор контейнера
        host_id: Идентификатор хоста, на котором должен быть запущен контейнер
        db: Сессия базы данных

    Returns:
        dict: Результат операции запуска контейнера

    Raises:
        HTTPException: Если хост не найден
    """
    hosts_service = HostsService(db)
    host_dto = hosts_service.get_host_by_id(host_id)
    if not host_dto:
        raise HTTPException(status_code=404, detail="Host not found")

    # Преобразуем адрес хоста для Docker (localhost -> host.docker.internal)
    host_address = hosts_service._resolve_host_for_docker(host_dto.host)
    docker_api_url = f"http://{host_address}:{host_dto.port}"
    docker_gateway = APIGateway(docker_api_url)
    # Увеличиваем таймаут для операций с контейнерами (запуск может занять время)
    docker_gateway.timeout = 30

    result = docker_gateway.make_request(
        method="POST",
        endpoint="/api/v1/manage/container/start",
        json_data={"id": container_id},
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