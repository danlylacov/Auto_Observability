import json
import logging
import os
from typing import Any, Dict

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from app.db.postgres.database import get_db
from app.db.redis.docker_containers import DockerContainers
from app.models.postgres.container import Container
from app.models.postgres.prometheus_config import PrometheusConfig
from app.services.api_getaway import APIGateway
from app.services.hosts_service import HostsService
from app.services.minio_service import MinioService

router = APIRouter()
logger = logging.getLogger(__name__)

load_dotenv()
prometheus_generation_url = os.getenv("PROMETHEUS_GENERATION_URL")
docker_api_url = os.getenv("DOCKER_API_URL")


@router.post("/generate_config", status_code=status.HTTP_200_OK)
async def generate_config(
        container_id: str,
        host_id: str,
        db: Session = Depends(get_db)
) -> dict[str, Any]:
    """
    Генерация конфига прометеус и сохранение в БД.
    """
    # Получаем хост из БД по host_id
    hosts_service = HostsService(db)
    host_dto = hosts_service.get_host_by_id(host_id)
    if not host_dto:
        raise HTTPException(status_code=404, detail="Host not found")

    # Используем адрес хоста из БД
    host = host_dto.host

    docker_containers = DockerContainers()
    container_data = docker_containers.get_container(container_id, host_id)

    if not container_data:
        return {"error": "Container not found"}
    info = container_data.get("info", {})
    classification = container_data.get("classification", {})

    # Получаем имя контейнера
    container_name = info.get("Name", "").lstrip("/") or info.get("Config", {}).get("Hostname", "unknown")

    # Получаем stack из классификации
    stack = None
    if classification.get("result"):
        stack = classification["result"][0][0] if classification["result"] else None

    # Вызываем сервис генерации с параметром host
    api_gateway = APIGateway(prometheus_generation_url)
    config_data = api_gateway.make_request(
        method='POST',
        endpoint='/api/v1/generate/',
        json_data=container_data,
        params={'host': host}
    )

    # Извлекаем данные из ответа
    exporter_config = config_data.get("info", {})  # это exporter_config из signatures.yml + network
    config_file = config_data.get("config", {})  # это upload_data из minio

    container = db.query(Container).filter(Container.id == container_id).first()

    if not container:
        classification_score = None
        if classification.get("result"):
            classification_score = classification.get("result")

        container = Container(
            id=container_id,
            name=container_name,
            image=info.get("Config", {}).get("Image", ""),
            status=info.get("State", {}).get("Status", "unknown"),
            stack=stack,
            classification_score=classification_score,
            docker_info=info
        )
        db.add(container)
    else:
        container.status = info.get("State", {}).get("Status", container.status)
        container.docker_info = info
        if stack:
            container.stack = stack
            container.classification_score = classification.get("result")

    # Извлекаем данные из exporter_config
    network_name = exporter_config.get("network")
    exporter_image = exporter_config.get("exporter_image")
    exporter_port = exporter_config.get("exporter_port")
    job_name_suffix = exporter_config.get("job_name_suffix", "")

    # Формируем job_name
    job_name = f"{container_name}{job_name_suffix}"

    # Формируем config_metadata с полной информацией
    config_metadata = {
        'host_name': host_id,  # Сохраняем host_name для последующего использования
        'config': config_file,
        'info': {
            'container_name': container_name,
            'stack': stack,
            'exporter_image': exporter_image,
            'exporter_port': exporter_port,
            'target_address': host,
            'job_name': job_name,
            'network': network_name,
            'exporter_env_vars': exporter_config.get("env_vars", {}),  # Базовые env_vars из signatures.yml
        }
    }

    existing_config = db.query(PrometheusConfig).filter(
        PrometheusConfig.container_id == container_id,
        PrometheusConfig.status == "active"
    ).order_by(PrometheusConfig.created_at.desc()).first()

    if existing_config:
        existing_config.container_name = container_name
        existing_config.stack = stack
        existing_config.exporter_image = exporter_image
        existing_config.exporter_port = exporter_port
        existing_config.target_address = host
        existing_config.job_name = job_name
        existing_config.minio_bucket = config_file.get("bucket")
        existing_config.minio_file_path = config_file.get("file")
        existing_config.config_metadata = config_metadata
        existing_config.version += 1
        
        prometheus_config = existing_config
    else:
        prometheus_config = PrometheusConfig(
            container_id=container_id,
            container_name=container_name,
            stack=stack,
            exporter_image=exporter_image,
            exporter_port=exporter_port,
            target_address=host,
            job_name=job_name,
            minio_bucket=config_file.get("bucket"),
            minio_file_path=config_file.get("file"),
            status="active",
            config_metadata=config_metadata
        )
        db.add(prometheus_config)
    db.commit()
    db.refresh(prometheus_config)

    return {
        "config_id": prometheus_config.id,
        "container_id": container_id,
        "config": config_data
    }


@router.post("/up_exporter", status_code=status.HTTP_200_OK)
async def up_exporter(container_id: str, port: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Запуск образа экспортера для любого типа контейнера.
    Использует данные из сохраненной конфигурации (network и exporter_env_vars).
    """
    config = db.query(PrometheusConfig).filter(
        PrometheusConfig.container_id == container_id,
        PrometheusConfig.status == "active"
    ).order_by(PrometheusConfig.created_at.desc()).first()

    if not config:
        logger.error(f"No active config found for container {container_id}")
        return {
            "error": "No active config found for this container",
            "container_id": container_id
        }

    # Получаем host_name из config_metadata или используем значение по умолчанию
    # Получаем host_name из config_metadata или используем значение по умолчанию
    config_metadata = config.config_metadata or {}
    host_name = config_metadata.get('host_name', 'localhost')  # fallback на localhost

    docker_containers = DockerContainers()
    container_data = docker_containers.get_container(container_id, host_name)

    if not container_data:
        logger.error(f"Target container {container_id} not found in Redis")
        return {
            "error": "Target container not found in Redis. Please update containers first.",
            "container_id": container_id
        }

    # container_data уже словарь, возвращается из get_container
    exporter_info = config_metadata.get('info', {})

    network_name = exporter_info.get("network")
    exporter_env_vars = exporter_info.get("exporter_env_vars", {})

    if not network_name or not exporter_env_vars:
        logger.warning(f"Network or env_vars not found in config_metadata for {container_id}, trying to get from Redis")

        container_info = container_data.get("info", {})

        if not container_info:
            logger.error(f"Container info is empty for {container_id}")
            return {
                "error": "Container info is empty",
                "container_id": container_id
            }

        if not network_name:
            network_settings = container_info.get('NetworkSettings', {})
            networks = network_settings.get('Networks', {})
            if networks:
                network_names = list(networks.keys())
                network_name = 'bridge' if 'bridge' in network_names else network_names[0] if network_names else None

        if not exporter_env_vars:
            logger.warning(f"Env vars not found in config, need to regenerate config for {container_id}")
            return {
                "error": "Env vars not found in config. Please regenerate config first.",
                "container_id": container_id
            }

    if not network_name:
        logger.error(f"Target container {container_id} has no networks. Container must be running.")
        return {
            "error": "Target container has no networks. Container must be running.",
            "container_id": container_id
        }

    json_data = {
        "image_name": config.exporter_image,
        "name": f"{config.container_name}-exporter",
        "ports": {f"{config.exporter_port}/tcp": port},
        "detach": True,
        "network": network_name
    }

    if exporter_env_vars:
        json_data["environment"] = exporter_env_vars
        logger.info(f"Using env vars from config: {exporter_env_vars}")
    else:
        logger.warning(f"No env vars in config for container {container_id}. Exporter may not work correctly.")

    try:
        api_gateway = APIGateway(docker_api_url)
        start_exporter = api_gateway.make_request(
            method='POST',
            endpoint='/api/v1/manage/container/pull_and_run',
            json_data=json_data,
        )

        logger.info(f"Exporter started successfully: {start_exporter}")
        return {
            "message": "Exporter started successfully",
            "exporter": start_exporter,
            "network": network_name,
            "environment": exporter_env_vars,
            "stack": config.stack
        }
    except Exception as e:
        logger.error(f"Failed to start exporter: {e}", exc_info=True)
        return {
            "error": f"Failed to start exporter: {str(e)}",
            "container_id": container_id,
            "network": network_name,
            "stack": config.stack
        }


@router.get("/get_signature", status_code=200)
async def get_signature() -> Dict[str, str]:
    """
    Получение файла с настройками генерации Prometheus Config
    """
    api_gateway = APIGateway(prometheus_generation_url)
    result = api_gateway.make_request(
        method='GET',
        endpoint='/api/v1/signature/get'
    )
    return result


@router.patch("/update_signature", status_code=200)
async def update_signature(new_signature: str) -> Dict[str, str]:
    """
    Обновление файла с настройками генерации Prometheus Config
    """
    api_gateway = APIGateway(prometheus_generation_url)
    result = api_gateway.make_request(
        method='PATCH',
        endpoint=f'/api/v1/signature/update?new_signature={new_signature}',
    )
    return result


@router.get("/get_all_configs", status_code=status.HTTP_200_OK)
async def get_all_configs(db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Получает все активные конфиги Prometheus и информацию об экспортерах для них.
    """
    configs = db.query(PrometheusConfig).filter(
        PrometheusConfig.status == "active"
    ).order_by(PrometheusConfig.created_at.desc()).all()

    docker_containers = DockerContainers()
    all_containers = docker_containers.get_containers()

    result = []

    for config in configs:
        config_metadata = config.config_metadata or {}
        host_name = config_metadata.get('host_name', 'localhost')
        
        exporter_name = f"{config.container_name}-exporter"
        exporter_info = None
        exporter_running = False
        exporter_container_id = None

        for container_id, container_data in all_containers.items():
            container_name = container_data.get("info", {}).get("Name", "").lstrip("/")
            container_host = container_data.get("host_name") or container_data.get("host_id")
            
            if container_name == exporter_name and container_host == host_name:
                container_status = container_data.get("info", {}).get("State", {}).get("Status", "")
                exporter_running = container_status == "running"
                exporter_container_id = container_id
                
                exporter_info = {
                    "container_id": container_id,
                    "name": container_name,
                    "status": container_status,
                    "image": container_data.get("info", {}).get("Config", {}).get("Image", ""),
                    "created": container_data.get("info", {}).get("Created", ""),
                    "network_settings": container_data.get("info", {}).get("NetworkSettings", {})
                }
                break

        config_data = {
            "config_id": config.id,
            "container_id": config.container_id,
            "container_name": config.container_name,
            "stack": config.stack,
            "exporter_image": config.exporter_image,
            "exporter_port": config.exporter_port,
            "target_address": config.target_address,
            "job_name": config.job_name,
            "minio_bucket": config.minio_bucket,
            "minio_file_path": config.minio_file_path,
            "host_name": host_name,
            "created_at": config.created_at.isoformat() if config.created_at else None,
            "updated_at": config.updated_at.isoformat() if config.updated_at else None,
            "exporter": {
                "running": exporter_running,
                "container_id": exporter_container_id,
                "info": exporter_info
            },
            "config_metadata": config_metadata
        }
        
        result.append(config_data)

    return {
        "total": len(result),
        "configs": result
    }


@router.get("/get_config_files/{config_id}", status_code=status.HTTP_200_OK)
async def get_config_files(config_id: int, db: Session = Depends(get_db)):
    """
    Получает два YAML файла из MinIO по ID конфига из БД.
    Возвращает scrape_config.yml и targets файл.
    """
    config = db.query(PrometheusConfig).filter(PrometheusConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    minio_service = MinioService()
    bucket = config.minio_bucket or 'prometheus'

    base_path = config.minio_file_path.rstrip('/')
    result = minio_service.get_yml_files(
        conf_path=base_path,
        bucket=bucket,
    )
    return result

