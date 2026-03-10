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
from app.models.main_config import AddServiceRequest, RemoveServiceRequest
from app.services.hosts_service import HostsService
from app.services.minio_service import MinioService

router = APIRouter()
logger = logging.getLogger(__name__)

load_dotenv()
prometheus_generation_url = os.getenv("PROMETHEUS_GENERATION_URL")
docker_api_url = os.getenv("DOCKER_API_URL")
prometheus_manager_url = os.getenv("PROMETHEUS_MANAGER_URL")


def get_prometheus_manager_gateway() -> APIGateway:
    """
    Возвращает APIGateway для Prometheus Manager.
    Бросает понятную ошибку, если PROMETHEUS_MANAGER_URL не задан.
    """
    if not prometheus_manager_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PROMETHEUS_MANAGER_URL is not configured in environment"
        )
    return APIGateway(prometheus_manager_url)


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

    # ПРОВЕРЯЕМ ЭКСПОРТЕР ПЕРЕД ГЕНЕРАЦИЕЙ КОНФИГА
    exporter_name = f"{container_name}-exporter"
    exporter_name_lower = exporter_name.lower()
    all_containers_data = docker_containers.get_containers()
    
    exporter_found = False
    exporter_running = False
    exporter_info = None
    
    logger.info(f"Checking exporter before config generation: exporter_name={exporter_name}, host_id={host_id}")
    
    # Сначала ищем экспортер по точному совпадению host_id и имени
    for exp_container_id, exp_container_data in all_containers_data.items():
        if isinstance(exp_container_data, dict):
            exp_container_name = exp_container_data.get("info", {}).get("Name", "").lstrip("/")
            exp_container_host = exp_container_data.get("host_name") or exp_container_data.get("host_id")
            
            # Проверяем совпадение имени экспортера и хоста
            if (exp_container_name.lower() == exporter_name_lower and 
                exp_container_host == host_id):
                exp_container_status = exp_container_data.get("info", {}).get("State", {}).get("Status", "")
                exporter_found = True
                exporter_running = exp_container_status.lower() in ("running", "up")
                
                exporter_info = {
                    "container_id": exp_container_id,
                    "name": exp_container_name,
                    "status": exp_container_status,
                    "image": exp_container_data.get("info", {}).get("Config", {}).get("Image", ""),
                }
                
                logger.info(
                    f"Found exporter: name={exp_container_name}, host={exp_container_host}, "
                    f"status={exp_container_status}, running={exporter_running}"
                )
                break
    
    # Если не нашли по точному совпадению, пробуем найти только по имени (fallback)
    if not exporter_found:
        logger.debug(f"Exporter not found with exact host match, trying fallback search by name only")
        for exp_container_id, exp_container_data in all_containers_data.items():
            if isinstance(exp_container_data, dict):
                exp_container_name = exp_container_data.get("info", {}).get("Name", "").lstrip("/")
                exp_container_host = exp_container_data.get("host_name") or exp_container_data.get("host_id")
                
                if exp_container_name.lower() == exporter_name_lower:
                    exp_container_status = exp_container_data.get("info", {}).get("State", {}).get("Status", "")
                    exporter_found = True
                    exporter_running = exp_container_status.lower() in ("running", "up")
                    
                    exporter_info = {
                        "container_id": exp_container_id,
                        "name": exp_container_name,
                        "status": exp_container_status,
                        "image": exp_container_data.get("info", {}).get("Config", {}).get("Image", ""),
                    }
                    
                    logger.warning(
                        f"Found exporter using fallback search: name={exp_container_name}, "
                        f"host={exp_container_host} (expected: {host_id}), status={exp_container_status}, "
                        f"running={exporter_running}"
                    )
                    break
    
    # Если экспортер не найден или не запущен, возвращаем ошибку ДО генерации конфига
    if not exporter_found:
        logger.warning(f"Exporter '{exporter_name}' not found on host '{host_id}'")
        # Логируем все найденные экспортеры для отладки
        all_exporters = [
            (data.get("info", {}).get("Name", "").lstrip("/"), 
             data.get("host_name") or data.get("host_id"))
            for data in all_containers_data.values()
            if isinstance(data, dict) and "-exporter" in data.get("info", {}).get("Name", "").lower()
        ]
        logger.debug(f"Available exporters: {all_exporters}")
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Exporter '{exporter_name}' not found on host '{host_id}'. Please start the exporter first using /api/v1/prometheus/up_exporter endpoint."
        )
    
    if not exporter_running:
        exporter_status = exporter_info.get('status', 'unknown') if exporter_info else 'unknown'
        logger.warning(
            f"Exporter '{exporter_name}' found but not running. Status: {exporter_status}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Exporter '{exporter_name}' is not running (status: {exporter_status}). Please start the exporter first."
        )
    
    logger.info(f"Exporter check passed. Proceeding with config generation for container {container_id}")
    
    # Вызываем сервис генерации с параметром host (только если экспортер найден и запущен)
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

        normalized_container_name = config.container_name.lstrip("/")
        exporter_name = f"{normalized_container_name}-exporter"
        exporter_info = None
        exporter_running = False
        exporter_container_id = None

        logger.debug(f"Looking for exporter: {exporter_name} on host: {host_name} (container_name: {config.container_name})")

        for container_id, container_data in all_containers.items():
            container_name = container_data.get("info", {}).get("Name", "").lstrip("/")
            container_host = container_data.get("host_name") or container_data.get("host_id")

            if "-exporter" in container_name.lower():
                logger.debug(f"Found potential exporter container: {container_name} on host: {container_host}")

            # Проверяем совпадение имени экспортера (сначала по host, потом fallback)
            if container_name.lower() == exporter_name.lower():
                if container_host == host_name:
                    # Точное совпадение по host и имени
                    container_status = container_data.get("info", {}).get("State", {}).get("Status", "")
                    exporter_running = container_status.lower() in ("running", "up")
                    exporter_container_id = container_id
                    
                    logger.info(f"Found exporter: {container_name}, host: {container_host}, status: {container_status}, running: {exporter_running}")
                    
                    exporter_info = {
                        "container_id": container_id,
                        "name": container_name,
                        "status": container_status,
                        "image": container_data.get("info", {}).get("Config", {}).get("Image", ""),
                        "created": container_data.get("info", {}).get("Created", ""),
                        "network_settings": container_data.get("info", {}).get("NetworkSettings", {})
                    }
                    break
                elif not exporter_info:
                    # Fallback: сохраняем первый найденный экспортер с таким именем
                    container_status = container_data.get("info", {}).get("State", {}).get("Status", "")
                    exporter_running = container_status.lower() in ("running", "up")
                    exporter_container_id = container_id
                    
                    logger.warning(
                        f"Found exporter using fallback: {container_name}, host: {container_host} "
                        f"(expected: {host_name}), status: {container_status}, running: {exporter_running}"
                    )
                    
                    exporter_info = {
                        "container_id": container_id,
                        "name": container_name,
                        "status": container_status,
                        "image": container_data.get("info", {}).get("Config", {}).get("Image", ""),
                        "created": container_data.get("info", {}).get("Created", ""),
                        "network_settings": container_data.get("info", {}).get("NetworkSettings", {})
                    }

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



@router.post("/main_config/add", status_code=status.HTTP_200_OK)
async def add_main_config_service(
    request: AddServiceRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Добавляет сервис в основной конфиг Prometheus.
    Проверяет, что экспортер запущен перед добавлением.
    """
    # Извлекаем job_name из запроса
    logger.debug(f"Received request: {request.model_dump()}")
    logger.debug(f"scrape_config type: {type(request.scrape_config)}")
    logger.debug(f"scrape_config value: {request.scrape_config}")
    
    job_name = None
    if request.scrape_config and isinstance(request.scrape_config, dict):
        scrape_configs = request.scrape_config.get('scrape_configs', [])
        logger.debug(f"scrape_configs: {scrape_configs}")
        if scrape_configs and len(scrape_configs) > 0:
            if isinstance(scrape_configs[0], dict):
                job_name = scrape_configs[0].get('job_name')
            else:
                job_name = getattr(scrape_configs[0], 'job_name', None)
    
    logger.info(f"Extracted job_name: {job_name}")
    
    if not job_name:
        logger.error(f"Job name not found in request. scrape_config: {request.scrape_config}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job name is required in scrape_config.scrape_configs[0].job_name"
        )
    
    # Находим конфиг Prometheus по job_name
    config = db.query(PrometheusConfig).filter(
        PrometheusConfig.job_name == job_name,
        PrometheusConfig.status == "active"
    ).order_by(PrometheusConfig.created_at.desc()).first()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prometheus config with job_name '{job_name}' not found"
        )
    
    # Проверяем статус экспортера
    config_metadata = config.config_metadata or {}
    host_name = config_metadata.get('host_name', 'localhost')
    container_name = config.container_name.lstrip("/")
    exporter_name = f"{container_name}-exporter"
    exporter_name_lower = exporter_name.lower()
    
    docker_containers = DockerContainers()
    all_containers_data = docker_containers.get_containers()
    
    exporter_found = False
    exporter_running = False
    exporter_info = None
    
    logger.info(
        f"Checking exporter before adding to main config: exporter_name={exporter_name}, "
        f"host_name={host_name}, job_name={job_name}"
    )
    
    # Сначала ищем экспортер по точному совпадению host_name и имени
    for exp_container_id, exp_container_data in all_containers_data.items():
        if isinstance(exp_container_data, dict):
            exp_container_name = exp_container_data.get("info", {}).get("Name", "").lstrip("/")
            exp_container_host = exp_container_data.get("host_name") or exp_container_data.get("host_id")
            
            logger.debug(
                f"Checking exporter candidate: name={exp_container_name}, host={exp_container_host}, "
                f"expected_name={exporter_name_lower}, expected_host={host_name}"
            )
            
            if (exp_container_name.lower() == exporter_name_lower and 
                exp_container_host == host_name):
                exp_container_status = exp_container_data.get("info", {}).get("State", {}).get("Status", "")
                exporter_found = True
                exporter_running = exp_container_status.lower() in ("running", "up")
                
                exporter_info = {
                    "container_id": exp_container_id,
                    "name": exp_container_name,
                    "status": exp_container_status,
                }
                
                logger.info(
                    f"Found exporter: name={exp_container_name}, host={exp_container_host}, "
                    f"status={exp_container_status}, running={exporter_running}"
                )
                break
    
    # Если не нашли по точному совпадению, пробуем найти только по имени (fallback)
    if not exporter_found:
        logger.debug(f"Exporter not found with exact host match, trying fallback search by name only")
        for exp_container_id, exp_container_data in all_containers_data.items():
            if isinstance(exp_container_data, dict):
                exp_container_name = exp_container_data.get("info", {}).get("Name", "").lstrip("/")
                exp_container_host = exp_container_data.get("host_name") or exp_container_data.get("host_id")
                
                if exp_container_name.lower() == exporter_name_lower:
                    exp_container_status = exp_container_data.get("info", {}).get("State", {}).get("Status", "")
                    exporter_found = True
                    exporter_running = exp_container_status.lower() in ("running", "up")
                    
                    exporter_info = {
                        "container_id": exp_container_id,
                        "name": exp_container_name,
                        "status": exp_container_status,
                    }
                    
                    logger.warning(
                        f"Found exporter using fallback search: name={exp_container_name}, "
                        f"host={exp_container_host} (expected: {host_name}), status={exp_container_status}, "
                        f"running={exporter_running}"
                    )
                    break
    
    # Если экспортер не найден или не запущен, возвращаем ошибку
    if not exporter_found:
        logger.warning(f"Exporter '{exporter_name}' not found on host '{host_name}'")
        # Логируем все найденные экспортеры для отладки
        all_exporters = [
            (data.get("info", {}).get("Name", "").lstrip("/"), 
             data.get("host_name") or data.get("host_id"))
            for data in all_containers_data.values()
            if isinstance(data, dict) and "-exporter" in data.get("info", {}).get("Name", "").lower()
        ]
        logger.debug(f"Available exporters: {all_exporters}")
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Exporter '{exporter_name}' not found on host '{host_name}'. Please start the exporter first."
        )
    
    if not exporter_running:
        exporter_status = exporter_info.get('status', 'unknown') if exporter_info else 'unknown'
        logger.warning(
            f"Exporter '{exporter_name}' found but not running. Status: {exporter_status}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Exporter '{exporter_name}' is not running (status: {exporter_status}). Please start the exporter first before adding to main config."
        )
    
    logger.info(f"Exporter check passed. Adding service '{job_name}' to main config")
    
    # Если экспортер запущен, добавляем в основной конфиг
    try:
        if not prometheus_generation_url:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="PROMETHEUS_GENERATION_URL is not configured"
            )
        
        logger.info(f"Making request to prometheus_generation service: {prometheus_generation_url}/api/v1/main-config/add")
        logger.debug(f"Request data: {request.model_dump()}")
        
        api_gateway = APIGateway(prometheus_generation_url)
        result = api_gateway.make_request(
            method='POST',
            endpoint='/api/v1/main-config/add',
            json_data=request.model_dump()
        )
        
        logger.info(f"Successfully added service '{job_name}' to main config")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding service to main config: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add service to main config: {str(e)}"
        )


@router.delete("/main_config/remove", status_code=status.HTTP_200_OK)
async def remove_main_config_service(request: RemoveServiceRequest) -> Dict[str, Any]:
    """
    Удаляет сервис из основного конфига Prometheus
    """
    api_gateway = APIGateway(prometheus_generation_url)
    result = api_gateway.make_request(
        method='DELETE',
        endpoint='/api/v1/main-config/remove',
        json_data=request.model_dump()
    )
    return result


@router.get("/main_config/get", status_code=status.HTTP_200_OK)
async def get_main_config() -> Dict[str, Any]:
    """
    Получает полный конфиг Prometheus и все файлы targets
    """
    api_gateway = APIGateway(prometheus_generation_url)
    result = api_gateway.make_request(
        method='GET',
        endpoint='/api/v1/main-config/'
    )
    return result


@router.post("/manager/start", status_code=status.HTTP_200_OK)
async def start_prometheus_manager() -> Dict[str, Any]:
    """
    Запускает Prometheus через Prometheus Manager сервис.
    """
    api_gateway = get_prometheus_manager_gateway()
    result = api_gateway.make_request(
        method='POST',
        endpoint='/api/v1/manage/prometheus/start',
    )
    return result


@router.post("/manager/stop", status_code=status.HTTP_200_OK)
async def stop_prometheus_manager() -> Dict[str, Any]:
    """
    Останавливает Prometheus через Prometheus Manager сервис.
    """
    api_gateway = get_prometheus_manager_gateway()
    result = api_gateway.make_request(
        method='POST',
        endpoint='/api/v1/manage/prometheus/stop',
    )
    return result


@router.get("/manager/status", status_code=status.HTTP_200_OK)
async def status_prometheus_manager() -> Dict[str, Any]:
    """
    Получает статус Prometheus из Prometheus Manager сервиса.
    """
    api_gateway = get_prometheus_manager_gateway()
    result = api_gateway.make_request(
        method='GET',
        endpoint='/api/v1/manage/prometheus/status',
    )
    return result


@router.get("/manager/settings", status_code=status.HTTP_200_OK)
async def get_prometheus_settings() -> Dict[str, Any]:
    """
    Получает настройки Prometheus из Prometheus Manager сервиса.
    """
    api_gateway = get_prometheus_manager_gateway()
    result = api_gateway.make_request(
        method='GET',
        endpoint='/api/v1/manage/prometheus/settings',
    )
    return result


@router.post("/manager/settings", status_code=status.HTTP_200_OK)
async def update_prometheus_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Обновляет настройки Prometheus через Prometheus Manager сервис.
    """
    api_gateway = get_prometheus_manager_gateway()
    result = api_gateway.make_request(
        method='POST',
        endpoint='/api/v1/manage/prometheus/settings',
        json_data=settings
    )
    return result


@router.post("/manager/config/update", status_code=status.HTTP_200_OK)
async def update_prometheus_config() -> Dict[str, Any]:
    """
    Обновляет конфигурацию Prometheus (prometheus.yml и targets) из MinIO
    через Prometheus Manager сервис.
    """
    api_gateway = get_prometheus_manager_gateway()
    result = api_gateway.make_request(
        method='POST',
        endpoint='/api/v1/manage/config/update',
    )
    return result
