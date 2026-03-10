import logging

from fastapi import APIRouter, status, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.services.update_containers import UpdateContainers
from app.db.redis.docker_containers import DockerContainers
from app.services.api_getaway import APIGateway
from app.services.hosts_service import HostsService
from app.services.minio_service import MinioService
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
    
    # Получаем контейнеры из БД
    containers_in_db = db.query(Container).filter(
        Container.id.in_(container_ids)
    ).all()
    containers_set = {c.id: c for c in containers_in_db}
    
    # Получаем все конфиги для контейнеров
    all_configs = db.query(PrometheusConfig).filter(
        PrometheusConfig.container_id.in_(container_ids)
    ).all()
    
    # Группируем конфиги по container_id, предпочитаем активные, затем самые свежие
    config_map = {}
    for config in all_configs:
        if config.container_id not in config_map:
            config_map[config.container_id] = config
        else:
            existing = config_map[config.container_id]
            # Приоритет: активный конфиг > неактивный, затем по дате создания
            if config.status == "active" and existing.status != "active":
                config_map[config.container_id] = config
            elif config.status == existing.status:
                if config.created_at and existing.created_at:
                    if config.created_at > existing.created_at:
                        config_map[config.container_id] = config
    
    # Получаем все контейнеры для поиска экспортеров (один раз)
    all_containers_data = docker_containers.get_containers()
    
    # Создаем индекс экспортеров для быстрого поиска
    # Индексируем по нескольким ключам для надежности
    exporter_index_by_host = {}  # (host_id, exporter_name_lower) -> exporter_data
    exporter_index_by_name = {}  # exporter_name_lower -> [exporter_data] (для fallback поиска)
    
    for exp_id, exp_data in all_containers_data.items():
        if isinstance(exp_data, dict):
            exp_name = exp_data.get("info", {}).get("Name", "").lstrip("/")
            exp_host = exp_data.get("host_name") or exp_data.get("host_id")
            
            if exp_name and "-exporter" in exp_name.lower():
                exp_name_lower = exp_name.lower()
                
                # Индексируем по host + name
                if exp_host:
                    key = (exp_host, exp_name_lower)
                    exporter_index_by_host[key] = {
                        "container_id": exp_id,
                        "data": exp_data
                    }
                
                # Индексируем только по имени для fallback поиска
                if exp_name_lower not in exporter_index_by_name:
                    exporter_index_by_name[exp_name_lower] = []
                exporter_index_by_name[exp_name_lower].append({
                    "container_id": exp_id,
                    "data": exp_data,
                    "host": exp_host
                })
    
    # Обрабатываем каждый контейнер
    for container_id, container_data in data.items():
        if not isinstance(container_data, dict):
            continue
            
        # Проверяем наличие конфига
        has_config = container_id in config_map
        container_data['has_prometheus_config'] = has_config
        
        if has_config:
            try:
                config = config_map[container_id]
                config_metadata = config.config_metadata or {}
                
                # Определяем host_name для поиска экспортера
                # Приоритет: config_metadata > host_id из запроса > host_name из container_data
                config_host_name = (
                    config_metadata.get('host_name') or 
                    host_id or 
                    container_data.get('host_name') or 
                    container_data.get('host_id')
                )
                
                # Получаем имя контейнера
                container_name = container_data.get("info", {}).get("Name", "").lstrip("/")
                if not container_name and container_id in containers_set:
                    container_name = containers_set[container_id].name.lstrip("/")
                if not container_name:
                    container_name = config.container_name.lstrip("/") if config.container_name else ""
                
                # Ищем экспортер
                exporter_info = None
                exporter_running = False
                exporter_container_id = None
                
                if container_name:
                    # Формируем имя экспортера
                    exporter_name = f"{container_name}-exporter"
                    exporter_name_lower = exporter_name.lower()
                    
                    logger.debug(
                        f"Searching exporter for container {container_id}: "
                        f"container_name={container_name}, exporter_name={exporter_name}, "
                        f"config_host_name={config_host_name}"
                    )
                    
                    # Пробуем найти экспортер по host + name
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
                                "name": exp_data.get("info", {}).get("Name", "").lstrip("/"),
                                "status": exp_status,
                                "image": exp_data.get("info", {}).get("Config", {}).get("Image", ""),
                            }
                            
                            logger.debug(
                                f"Found exporter {exporter_name} on host {config_host_name}: "
                                f"status={exp_status}, running={exporter_running}"
                            )
                    
                    # Если не нашли по host, пробуем найти только по имени (fallback)
                    if not exporter_info and exporter_name_lower in exporter_index_by_name:
                        # Берем первый найденный экспортер с таким именем
                        # (в идеале должен быть один, но если несколько - берем первый)
                        exporter_candidates = exporter_index_by_name[exporter_name_lower]
                        if exporter_candidates:
                            exporter_entry = exporter_candidates[0]
                            exp_data = exporter_entry["data"]
                            exp_status = exp_data.get("info", {}).get("State", {}).get("Status", "")
                            exporter_running = exp_status.lower() in ("running", "up")
                            exporter_container_id = exporter_entry["container_id"]
                            
                            exporter_info = {
                                "container_id": exporter_container_id,
                                "name": exp_data.get("info", {}).get("Name", "").lstrip("/"),
                                "status": exp_status,
                                "image": exp_data.get("info", {}).get("Config", {}).get("Image", ""),
                            }
                            
                            # Логируем, если использовали fallback поиск
                            found_host = exporter_entry.get("host")
                            logger.info(
                                f"Found exporter {exporter_name} using fallback search. "
                                f"Expected host: {config_host_name}, found host: {found_host}, "
                                f"status={exp_status}, running={exporter_running}"
                            )
                    else:
                        # Логируем, если экспортер не найден
                        logger.debug(
                            f"Exporter {exporter_name} not found. "
                            f"Available exporters in index: {list(exporter_index_by_name.keys())[:10]}"
                        )
                
                # Формируем информацию о конфиге Prometheus
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
                logger.error(f"Error processing prometheus config for container {container_id}: {str(e)}", exc_info=True)
                container_data['prometheus_config'] = None
                container_data['has_prometheus_config'] = False
        else:
            container_data['prometheus_config'] = None
    
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

    # Получаем информацию о контейнере из БД перед удалением
    container = db.query(Container).filter(Container.id == id).first()
    container_name = None
    if container:
        container_name = container.name.lstrip("/")
    
    # Если контейнера нет в БД, пытаемся получить имя из Redis
    if not container_name:
        docker_containers = DockerContainers()
        container_data = docker_containers.get_container(id, host_id)
        if container_data:
            container_info = container_data.get("info", {})
            container_name = container_info.get("Name", "").lstrip("/") or container_info.get("Config", {}).get("Hostname", "")

    docker_gateway = APIGateway(host_dto.base_url)

    # Удаляем экспортер, если он существует
    if container_name:
        exporter_name = f"{container_name}-exporter"
        try:
            # Пытаемся найти и удалить экспортер
            exporter_result = docker_gateway.make_request(
                method="DELETE",
                endpoint="/api/v1/manage/container/remove",
                params={"force": True},
                json_data={"id": exporter_name},
            )
            logger.info(f"Exporter {exporter_name} removal attempted: {exporter_result}")
        except Exception as e:
            # Если экспортер не найден или произошла ошибка, просто логируем
            logger.warning(f"Could not remove exporter {exporter_name}: {str(e)}")

    # Удаляем контейнер через Docker API
    try:
        result = docker_gateway.make_request(
            method="DELETE",
            endpoint="/api/v1/manage/container/remove",
            params={"force": force},
            json_data={"id": id},
        )
    except Exception as e:
        logger.warning(f"Error removing container {id} via Docker API: {str(e)}")
        # Продолжаем удаление из БД даже если Docker API вернул ошибку
        result = {"message": f"Container removal attempted, but Docker API error: {str(e)}"}

    # Удаляем контейнер и конфиги Prometheus из БД и MinIO
    try:
        minio_service = MinioService()
        
        if container:
            # Получаем все конфиги перед удалением контейнера, чтобы удалить файлы из MinIO
            configs_to_delete = db.query(PrometheusConfig).filter(
                PrometheusConfig.container_id == id
            ).all()
            
            # Удаляем файлы из MinIO для каждого конфига
            for config in configs_to_delete:
                if config.minio_file_path:
                    bucket = config.minio_bucket or 'prometheus'
                    prefix = config.minio_file_path.rstrip('/')
                    deleted_count = minio_service.delete_files_by_prefix(prefix=prefix, bucket=bucket)
                    logger.info(f"Deleted {deleted_count} files from MinIO for config {config.id} (prefix: {prefix})")
            
            # Удаляем контейнер из БД (конфиги удалятся каскадно благодаря CASCADE в ForeignKey)
            db.delete(container)
            db.commit()
            logger.info(f"Container {id} and its Prometheus configs removed from database")
        else:
            # Если контейнера нет в БД, но есть конфиги, удаляем их напрямую
            configs_to_delete = db.query(PrometheusConfig).filter(
                PrometheusConfig.container_id == id
            ).all()
            if configs_to_delete:
                # Удаляем файлы из MinIO для каждого конфига
                for config in configs_to_delete:
                    if config.minio_file_path:
                        bucket = config.minio_bucket or 'prometheus'
                        prefix = config.minio_file_path.rstrip('/')
                        deleted_count = minio_service.delete_files_by_prefix(prefix=prefix, bucket=bucket)
                        logger.info(f"Deleted {deleted_count} files from MinIO for config {config.id} (prefix: {prefix})")
                
                # Удаляем конфиги из БД
                for config in configs_to_delete:
                    db.delete(config)
                db.commit()
                logger.info(f"Prometheus configs for container {id} removed from database")
    except Exception as e:
        logger.error(f"Error removing container {id} from database: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove container from database: {str(e)}"
        )

    # Обновляем информацию о контейнерах в Redis
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