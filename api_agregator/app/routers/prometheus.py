"""Prometheus API router module."""

import copy
import json
import logging
import os
import time
from typing import Any, Dict

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
import yaml

from app.db.postgres.database import get_db
from app.db.redis.docker_containers import DockerContainers
from app.models.main_config import AddServiceRequest, RemoveServiceRequest
from app.models.postgres.container import Container
from app.models.postgres.prometheus_config import PrometheusConfig
from app.services.api_getaway import APIGateway
from app.services.hosts_service import HostsService
from app.services.minio_service import MinioService
from app.services.prometheus_scrape_resolution import (
    host_port_from_redis_inspect,
    redis_host_key_for_api_host_id,
    resolve_scrape_host_port_for_workload,
    rewrite_targets_internal_port_to_host_port,
)

router = APIRouter()
logger = logging.getLogger(__name__)

load_dotenv()
prometheus_generation_url = os.getenv("PROMETHEUS_GENERATION_URL")
docker_api_url = os.getenv("DOCKER_API_URL")
prometheus_manager_url = os.getenv("PROMETHEUS_MANAGER_URL")


def get_prometheus_manager_gateway() -> APIGateway:
    """
    Возвращает APIGateway для Prometheus Manager.

    Returns:
        APIGateway: Gateway для Prometheus Manager

    Raises:
        HTTPException: Если PROMETHEUS_MANAGER_URL не задан
    """
    if not prometheus_manager_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PROMETHEUS_MANAGER_URL is not configured in environment"
        )
    return APIGateway(prometheus_manager_url)


def _resolve_exporter_state(
        all_containers_data: dict[str, Any],
        *,
        host_name: str,
        container_name: str
) -> tuple[bool, bool, dict[str, Any] | None, str | None]:
    """Find exporter by host/name and return (found, running, info, id)."""
    exporter_name = f"{container_name}-exporter".lower()
    exporter_info = None
    exporter_running = False
    exporter_container_id = None

    for exp_container_id, exp_container_data in all_containers_data.items():
        if not isinstance(exp_container_data, dict):
            continue
        exp_container_name = exp_container_data.get("info", {}).get("Name", "").lstrip("/")
        exp_container_host = redis_host_key_for_api_host_id(exp_container_data)
        if exp_container_name.lower() == exporter_name and exp_container_host == host_name:
            exp_container_status = exp_container_data.get("info", {}).get("State", {}).get("Status", "")
            exporter_running = exp_container_status.lower() in ("running", "up")
            exporter_container_id = exp_container_id
            exporter_info = {
                "container_id": exp_container_id,
                "name": exp_container_name,
                "status": exp_container_status,
            }
            return True, exporter_running, exporter_info, exporter_container_id

    for exp_container_id, exp_container_data in all_containers_data.items():
        if not isinstance(exp_container_data, dict):
            continue
        exp_container_name = exp_container_data.get("info", {}).get("Name", "").lstrip("/")
        if exp_container_name.lower() == exporter_name:
            exp_container_status = exp_container_data.get("info", {}).get("State", {}).get("Status", "")
            exporter_running = exp_container_status.lower() in ("running", "up")
            exporter_container_id = exp_container_id
            exporter_info = {
                "container_id": exp_container_id,
                "name": exp_container_name,
                "status": exp_container_status,
            }
            return True, exporter_running, exporter_info, exporter_container_id

    return False, False, None, None


def _signature_exporter_command(stack: str | None) -> list[str] | str | None:
    """Universal fallback: read exporter_command for stack from signatures.yml."""
    if not stack:
        return None
    candidates = ["/app/signatures.yml"]
    current_file = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
    candidates.append(os.path.join(project_root, "signatures.yml"))
    for path in candidates:
        try:
            with open(path, "r", encoding="utf-8") as f:
                signatures = yaml.safe_load(f) or {}
            cfg = signatures.get(str(stack).lower().replace(" ", "_")) or {}
            cmd = cfg.get("exporter_command")
            if cmd:
                return cmd
        except Exception:
            continue
    return None


def _generation_exporter_command(stack: str | None) -> list[str] | str | None:
    """Read exporter_command from prometheus_generation signature endpoint."""
    if not stack or not prometheus_generation_url:
        return None
    try:
        gw = APIGateway(prometheus_generation_url)
        data = gw.make_request("GET", "/api/v1/signature/get", timeout=15.0)
        parsed = None
        if isinstance(data, str):
            parsed = yaml.safe_load(data)
        elif isinstance(data, dict):
            if "signature" in data and isinstance(data["signature"], str):
                parsed = yaml.safe_load(data["signature"])
            elif "signature.yml" in data and isinstance(data["signature.yml"], str):
                parsed = yaml.safe_load(data["signature.yml"])
            else:
                parsed = data
        signatures = parsed or {}
        cfg = signatures.get(str(stack).lower().replace(" ", "_")) or {}
        cmd = cfg.get("exporter_command")
        return cmd if cmd else None
    except Exception:
        return None


def _resolve_target_address(info: dict[str, Any], host: str = "localhost") -> str:
    container_name = (
        info.get("Name", "").lstrip("/")
        or info.get("Config", {}).get("Hostname", "unknown")
    )
    labels = info.get("Config", {}).get("Labels", {}) or {}
    target_address = host or "localhost"
    if target_address in ("127.0.0.1",):
        target_address = "localhost"
    if not target_address:
        if labels.get("com.docker.compose.service"):
            target_address = labels["com.docker.compose.service"]
        elif container_name:
            target_address = container_name
    return target_address


def _bootstrap_active_prometheus_config(
    db: Session,
    container_id: str,
    container_data: dict[str, Any],
    redis_host_key: str,
) -> PrometheusConfig:
    """
    Создаёт active PrometheusConfig для up_exporter, если записи ещё нет.
    Не требует уже запущенного sidecar-экспортёра (в отличие от generate_config).
    """
    info = container_data.get("info", {})
    classification = container_data.get("classification", {})

    container_name = (
        info.get("Name", "").lstrip("/")
        or info.get("Config", {}).get("Hostname", "unknown")
    )
    target_address = _resolve_target_address(info)

    stack = None
    if classification.get("result"):
        stack = classification["result"][0][0] if classification["result"] else None

    payload: dict[str, Any] = copy.deepcopy(container_data)
    api_gateway = APIGateway(prometheus_generation_url)
    config_data = api_gateway.make_request(
        method="POST",
        endpoint="/api/v1/generate/",
        json_data=payload,
        params={"host": target_address},
    )

    exporter_config = config_data.get("info", {})
    config_file = config_data.get("config", {})

    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        classification_score = classification.get("result") if classification.get("result") else None
        container = Container(
            id=container_id,
            name=container_name,
            image=info.get("Config", {}).get("Image", ""),
            status=info.get("State", {}).get("Status", "unknown"),
            stack=stack,
            classification_score=classification_score,
            docker_info=info,
        )
        db.add(container)
    else:
        container.status = info.get("State", {}).get("Status", container.status)
        container.docker_info = info
        if stack:
            container.stack = stack
            container.classification_score = classification.get("result")

    network_name = exporter_config.get("network")
    exporter_image = exporter_config.get("exporter_image")
    exporter_port = exporter_config.get("exporter_port")
    job_name_suffix = exporter_config.get("job_name_suffix", "")
    job_name = f"{container_name}{job_name_suffix}"

    info_block: dict[str, Any] = {
        "container_name": container_name,
        "stack": stack,
        "exporter_image": exporter_image,
        "exporter_port": exporter_port,
        "target_address": target_address,
        "job_name": job_name,
        "network": network_name,
        "exporter_env_vars": exporter_config.get("env_vars", {}),
        "exporter_command": exporter_config.get("exporter_command"),
        "exporter_entrypoint": exporter_config.get("exporter_entrypoint"),
    }
    if "native_prometheus_scrape" in exporter_config:
        info_block["native_prometheus_scrape"] = bool(
            exporter_config["native_prometheus_scrape"]
        )

    config_metadata = {
        "host_name": redis_host_key,
        "config": config_file,
        "info": info_block,
    }

    existing_config = (
        db.query(PrometheusConfig)
        .filter(
            PrometheusConfig.container_id == container_id,
            PrometheusConfig.status == "active",
        )
        .order_by(PrometheusConfig.created_at.desc())
        .first()
    )

    if existing_config:
        existing_config.container_name = container_name
        existing_config.stack = stack
        existing_config.exporter_image = exporter_image
        existing_config.exporter_port = exporter_port
        existing_config.target_address = target_address
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
            target_address=target_address,
            job_name=job_name,
            minio_bucket=config_file.get("bucket"),
            minio_file_path=config_file.get("file"),
            status="active",
            config_metadata=config_metadata,
        )
        db.add(prometheus_config)

    db.commit()
    db.refresh(prometheus_config)
    logger.info(
        "Bootstrapped prometheus config for container %s (stack=%s) before up_exporter",
        container_id,
        stack,
    )
    return prometheus_config


def _refresh_exporter_metadata_from_generation(
    db: Session,
    config: PrometheusConfig,
    container_data: dict[str, Any],
    target_address: str,
    *,
    prometheus_scrape_port: int | None = None,
) -> None:
    """
    Повторно вызывает prometheus_generation и обновляет sidecar-поля в config_metadata.
    Нужен при устаревших или пустых exporter_env_vars / command / network в БД.
    """
    payload: dict[str, Any] = copy.deepcopy(container_data)
    if prometheus_scrape_port is not None:
        payload["prometheus_scrape_port"] = int(prometheus_scrape_port)

    api_gateway = APIGateway(prometheus_generation_url)
    gen_params: dict[str, Any] = {"host": target_address}
    if prometheus_scrape_port is not None:
        gen_params["prometheus_scrape_port"] = int(prometheus_scrape_port)

    config_data = api_gateway.make_request(
        method="POST",
        endpoint="/api/v1/generate/",
        json_data=payload,
        params=gen_params,
    )
    exporter_config = config_data.get("info") or {}
    config_file = config_data.get("config", {})

    md = copy.deepcopy(config.config_metadata or {})
    inf = dict(md.get("info") or {})

    info_src = container_data.get("info") or {}
    container_name = (
        inf.get("container_name")
        or info_src.get("Name", "").lstrip("/")
        or info_src.get("Config", {}).get("Hostname", "unknown")
    )
    job_name_suffix = exporter_config.get("job_name_suffix", "")
    job_name = f"{container_name}{job_name_suffix}"

    stack = inf.get("stack")
    cl = container_data.get("classification") or {}
    if not stack and cl.get("result"):
        stack = cl["result"][0][0] if cl["result"] else None

    if "env_vars" in exporter_config:
        inf["exporter_env_vars"] = exporter_config.get("env_vars") or {}
    for key in (
        "exporter_image",
        "exporter_port",
        "exporter_command",
        "exporter_entrypoint",
        "network",
    ):
        if key in exporter_config and exporter_config[key] is not None:
            inf[key] = exporter_config[key]
    if "native_prometheus_scrape" in exporter_config:
        inf["native_prometheus_scrape"] = bool(
            exporter_config["native_prometheus_scrape"]
        )

    inf["container_name"] = container_name
    inf["job_name"] = job_name
    if stack:
        inf["stack"] = stack
    inf["target_address"] = inf.get("target_address") or target_address

    md["info"] = inf
    if config_file:
        md["config"] = config_file

    config.config_metadata = md
    if "exporter_image" in exporter_config:
        config.exporter_image = exporter_config["exporter_image"]
    if exporter_config.get("exporter_port") is not None:
        config.exporter_port = exporter_config["exporter_port"]
    if stack:
        config.stack = stack
    config.container_name = container_name
    config.job_name = job_name
    config.target_address = inf.get("target_address", config.target_address)
    if config_file.get("bucket"):
        config.minio_bucket = config_file.get("bucket")
    if config_file.get("file"):
        config.minio_file_path = config_file.get("file")

    flag_modified(config, "config_metadata")
    db.commit()
    db.refresh(config)
    logger.info(
        "Refreshed exporter metadata via prometheus_generation for container %s",
        config.container_id,
    )


def _exporter_sidecar_ready(info: dict[str, Any]) -> bool:
    """Экспортёр может стартовать без env (только command/entrypoint)."""
    if info.get("native_prometheus_scrape"):
        return True
    env = info.get("exporter_env_vars")
    if isinstance(env, dict) and len(env) > 0:
        return True
    if info.get("exporter_entrypoint"):
        return True
    if info.get("exporter_command"):
        return True
    return False


@router.post("/generate_config", status_code=status.HTTP_200_OK)
async def generate_config(
        container_id: str,
        host_id: str,
        db: Session = Depends(get_db)
) -> dict[str, Any]:
    """
    Генерация конфига Prometheus и сохранение в БД.

    Если sidecar-экспортёр ещё не запущен, конфиг всё равно генерируется (хост scrape порта
    берётся из БД или внутреннего порта экспортёра).

    Args:
        container_id: Идентификатор контейнера
        host_id: Идентификатор хоста
        db: Сессия базы данных

    Returns:
        dict[str, Any]: Словарь с данными о созданной конфигурации

    Raises:
        HTTPException: Если хост не найден или контейнер не найден
    """
    hosts_service = HostsService(db)
    host_dto = hosts_service.get_host_by_id(host_id)
    if not host_dto:
        raise HTTPException(status_code=404, detail="Host not found")

    host = host_dto.host
    docker_containers = DockerContainers()
    host_candidates = list(
        dict.fromkeys(
            x for x in (str(host_id).strip(), str(host_dto.id).strip()) if x
        )
    )
    container_data: dict[str, Any] = {}
    redis_host_key = host_candidates[0] if host_candidates else str(host_id).strip()
    for hk in host_candidates:
        cd = docker_containers.get_container(container_id, hk)
        if cd:
            container_data = cd
            redis_host_key = hk
            break

    if not container_data:
        return {"error": "Container not found"}
    info = container_data.get("info", {})
    classification = container_data.get("classification", {})

    container_name = (
        info.get("Name", "").lstrip("/") or
        info.get("Config", {}).get("Hostname", "unknown")
    )

    existing_cfg = (
        db.query(PrometheusConfig)
        .filter(
            PrometheusConfig.container_id == container_id,
            PrometheusConfig.status == "active",
        )
        .order_by(PrometheusConfig.created_at.desc())
        .first()
    )

    # Use container-reachable address for Prometheus targets.
    network_settings = info.get("NetworkSettings", {})
    networks = network_settings.get("Networks", {}) or {}
    labels = info.get("Config", {}).get("Labels", {}) or {}

    target_address = host or "localhost"
    if target_address in ("127.0.0.1",):
        target_address = "localhost"
    if not target_address:
        if labels.get("com.docker.compose.service"):
            target_address = labels["com.docker.compose.service"]
        elif container_name:
            target_address = container_name

    all_containers_data = docker_containers.get_containers()
    exporter_found, exporter_running, _, _ = _resolve_exporter_state(
        all_containers_data,
        host_name=redis_host_key,
        container_name=container_name,
    )
    scrape_port: int | None = None
    if exporter_found and exporter_running:
        pref_internal = existing_cfg.exporter_port if existing_cfg else None
        scrape_port = resolve_scrape_host_port_for_workload(
            config_info=(existing_cfg.config_metadata or {}).get("info") if existing_cfg else None,
            exporter_internal_port=pref_internal,
            workload_container_name=container_name,
            redis_host_key=redis_host_key,
            all_containers=all_containers_data,
        )
    else:
        logger.warning(
            "Exporter for %s not running or missing; generating config without live scrape port",
            container_name,
        )
        if existing_cfg:
            infop = (existing_cfg.config_metadata or {}).get("info") or {}
            raw_sp = infop.get("scrape_host_port")
            if raw_sp is not None:
                try:
                    scrape_port = int(raw_sp)
                except (TypeError, ValueError):
                    scrape_port = None
            if scrape_port is None and existing_cfg.exporter_port is not None:
                scrape_port = int(existing_cfg.exporter_port)

    stack = None
    if classification.get("result"):
        stack = classification["result"][0][0] if classification["result"] else None

    logger.info("Proceeding with config generation for container %s exporter_found=%s exporter_running=%s",
                container_id, exporter_found, exporter_running)

    payload: dict[str, Any] = copy.deepcopy(container_data)
    if scrape_port is not None:
        payload["prometheus_scrape_port"] = scrape_port
        logger.info(
            "Using prometheus_scrape_port=%s for container %s (host scrape)",
            scrape_port,
            container_name,
        )

    api_gateway = APIGateway(prometheus_generation_url)
    gen_params: dict[str, Any] = {'host': target_address}
    if scrape_port is not None:
        gen_params['prometheus_scrape_port'] = int(scrape_port)
    config_data = api_gateway.make_request(
        method='POST',
        endpoint='/api/v1/generate/',
        json_data=payload,
        params=gen_params,
    )

    exporter_config = config_data.get("info", {})
    config_file = config_data.get("config", {})

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

    network_name = exporter_config.get("network")
    exporter_image = exporter_config.get("exporter_image")
    exporter_port = exporter_config.get("exporter_port")
    job_name_suffix = exporter_config.get("job_name_suffix", "")

    job_name = f"{container_name}{job_name_suffix}"

    info_block: dict[str, Any] = {
        'container_name': container_name,
        'stack': stack,
        'exporter_image': exporter_image,
        'exporter_port': exporter_port,
        'target_address': target_address,
        'job_name': job_name,
        'network': network_name,
        'exporter_env_vars': exporter_config.get("env_vars", {}),
        'exporter_command': exporter_config.get("exporter_command"),
        'exporter_entrypoint': exporter_config.get("exporter_entrypoint"),
    }
    if "native_prometheus_scrape" in exporter_config:
        info_block["native_prometheus_scrape"] = bool(
            exporter_config["native_prometheus_scrape"]
        )
    if scrape_port is not None:
        info_block["scrape_host_port"] = scrape_port
    elif existing_cfg:
        prev_hp = (existing_cfg.config_metadata or {}).get("info", {}).get("scrape_host_port")
        if prev_hp is not None:
            info_block["scrape_host_port"] = prev_hp

    config_metadata = {
        'host_name': redis_host_key,
        'config': config_file,
        'info': info_block,
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
        existing_config.target_address = target_address
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
            target_address=target_address,
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
    Запуск образа экспортера для контейнера.

    Использует данные из сохраненной конфигурации (network и exporter_env_vars).

    Args:
        container_id: Идентификатор контейнера
        port: Порт для экспортера
        db: Сессия базы данных

    Returns:
        dict[str, Any]: Результат запуска экспортера или ошибка
    """
    config = db.query(PrometheusConfig).filter(
        PrometheusConfig.container_id == container_id,
        PrometheusConfig.status == "active"
    ).order_by(PrometheusConfig.created_at.desc()).first()

    docker_containers = DockerContainers()
    container_data: dict[str, Any] | None = None

    if not config:
        all_containers = docker_containers.get_containers()
        container_data = all_containers.get(container_id)
        if not container_data:
            logger.error("No active config and container %s not in Redis", container_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "No active Prometheus config for this container. "
                    "Container not found in Redis — run update containers first."
                ),
            )
        hosts_service_bootstrap = HostsService(db)
        host_dto_bootstrap = hosts_service_bootstrap.resolve_host_for_container(
            None, container_data
        )
        if not host_dto_bootstrap:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "No Docker host registered. Add a host in settings "
                    "or set DOCKER_API_URL."
                ),
            )
        redis_host_key = host_dto_bootstrap.id
        logger.info(
            "No active config for %s; bootstrapping from classification before exporter start",
            container_id,
        )
        config = _bootstrap_active_prometheus_config(
            db, container_id, container_data, redis_host_key
        )

    if container_data is None:
        container_data = docker_containers.get_containers().get(container_id)

    config_metadata = config.config_metadata or {}
    config_host_key = config_metadata.get("host_name")

    # Получаем адрес хоста для обращения к docker_api
    hosts_service = HostsService(db)
    host_dto = hosts_service.resolve_host_for_container(config_host_key, container_data)
    if not host_dto:
        logger.error("Host %s not found (container host_id=%s)", config_host_key, (container_data or {}).get("host_id"))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Host {config_host_key!r} not found. "
                "Register the Docker host or regenerate the Prometheus config."
            ),
        )
    host_id = host_dto.id
    
    # Преобразуем адрес хоста для Docker (localhost -> host.docker.internal)
    host_address = hosts_service._resolve_host_for_docker(host_dto.host)
    docker_api_host_url = f"http://{host_address}:{host_dto.port}"

    if container_data is None:
        container_data = docker_containers.get_container(container_id, host_id)

    # Если не найден с host_id, пробуем найти без фильтра по хосту
    if not container_data:
        logger.warning("Container %s not found with host_id %s, trying to find without host filter", container_id, host_id)
        all_containers = docker_containers.get_containers()
        container_data = all_containers.get(container_id)
        
        if container_data:
            logger.info("Container found without host filter, using it")
        else:
            logger.error("Target container %s not found in Redis at all", container_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target container not found in Redis. Please update containers first.",
            )

    container_info = container_data.get("info", {})
    if not container_info:
        logger.error("Container info is empty for %s", container_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Container info is empty",
        )

    config_metadata = config.config_metadata or {}
    exporter_info = dict(config_metadata.get("info") or {})

    network_name = exporter_info.get("network")
    if not network_name:
        network_settings = container_info.get("NetworkSettings", {})
        networks = network_settings.get("Networks", {})
        if networks:
            network_names = list(networks.keys())
            network_name = (
                "bridge"
                if "bridge" in network_names
                else network_names[0] if network_names else None
            )

    target_address = (
        exporter_info.get("target_address")
        or config.target_address
        or _resolve_target_address(container_info)
    )
    pref_scrape = exporter_info.get("scrape_host_port")
    if pref_scrape is not None:
        try:
            pref_scrape = int(pref_scrape)
        except (TypeError, ValueError):
            pref_scrape = None

    if not _exporter_sidecar_ready(exporter_info) or not network_name:
        logger.info(
            "Refreshing exporter sidecar metadata from prometheus_generation for %s",
            container_id,
        )
        _refresh_exporter_metadata_from_generation(
            db,
            config,
            container_data,
            target_address,
            prometheus_scrape_port=pref_scrape,
        )
        config_metadata = config.config_metadata or {}
        exporter_info = dict(config_metadata.get("info") or {})
        network_name = exporter_info.get("network") or network_name

    if not network_name:
        network_settings = container_info.get("NetworkSettings", {})
        networks = network_settings.get("Networks", {})
        if networks:
            network_names = list(networks.keys())
            network_name = (
                "bridge"
                if "bridge" in network_names
                else network_names[0] if network_names else None
            )

    if not network_name:
        logger.error("Target container %s has no networks. Container must be running.", container_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target container has no networks. Container must be running.",
        )

    if not _exporter_sidecar_ready(exporter_info):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Could not resolve exporter env/command/entrypoint for this stack "
                "after refresh. Check container classification and signatures.yml."
            ),
        )

    if exporter_info.get("native_prometheus_scrape"):
        try:
            iport = int(config.exporter_port) if config.exporter_port is not None else None
        except (TypeError, ValueError):
            iport = None
        hp_live = (
            host_port_from_redis_inspect({"info": container_info}, iport)
            if iport is not None
            else None
        )
        # #region agent log
        try:
            with open(
                "/home/daniil/Рабочий стол/диплом/Auto_Observability/.cursor/debug-a72628.log",
                "a",
                encoding="utf-8",
            ) as _df:
                _df.write(
                    json.dumps(
                        {
                            "sessionId": "a72628",
                            "hypothesisId": "H2",
                            "location": "prometheus:up_exporter:native",
                            "message": "up_exporter native rabbit scrape host port",
                            "data": {
                                "container_id": container_id,
                                "internal_port": iport,
                                "hp_live": hp_live,
                                "port_param": port,
                            },
                            "timestamp": int(time.time() * 1000),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        except OSError:
            pass
        # #endregion
        scrape_stored = int(hp_live) if hp_live is not None else int(port)
        md = dict(config.config_metadata or {})
        inf = dict(md.get("info") or {})
        inf["scrape_host_port"] = scrape_stored
        md["info"] = inf
        config.config_metadata = md
        flag_modified(config, "config_metadata")
        db.commit()
        db.refresh(config)
        try:
            await generate_config(
                container_id=config.container_id, host_id=str(host_dto.id), db=db
            )
        except Exception as sync_exc:
            logger.warning(
                "Regenerate Prometheus config after native scrape sync failed for %s: %s",
                container_id,
                sync_exc,
                exc_info=True,
            )
        try:
            mgr = get_prometheus_manager_gateway()
            mgr.make_request("POST", "/api/v1/manage/config/update", timeout=120.0)
        except Exception as mgr_exc:
            logger.warning(
                "Prometheus manager config pull after native scrape failed: %s",
                mgr_exc,
                exc_info=True,
            )
        return {
            "message": "RabbitMQ native Prometheus plugin scrape (no exporter sidecar)",
            "native_prometheus_scrape": True,
            "scrape_host_port": scrape_stored,
            "stack": config.stack,
        }

    exporter_env_vars = exporter_info.get("exporter_env_vars") or {}
    if not isinstance(exporter_env_vars, dict):
        exporter_env_vars = {}

    json_data = {
        "image_name": config.exporter_image,
        "name": f"{config.container_name}-exporter",
        "ports": {f"{config.exporter_port}/tcp": port},
        "detach": True,
        "network": network_name
    }

    if exporter_env_vars:
        json_data["environment"] = exporter_env_vars
        logger.info("Using env vars from config: %s", exporter_env_vars)
    else:
        logger.info("No env vars for exporter %s (command/entrypoint only)", container_id)

    cmd = exporter_info.get("exporter_command")
    if not cmd:
        cmd = _signature_exporter_command(config.stack)
    if not cmd:
        cmd = _generation_exporter_command(config.stack)
    if isinstance(cmd, list):
        cmds = [str(x) for x in cmd if str(x).strip()]
        if cmds:
            json_data["command"] = cmds
    elif isinstance(cmd, str) and cmd.strip():
        json_data["command"] = cmd.strip()

    ep = exporter_info.get("exporter_entrypoint")
    if ep:
        if isinstance(ep, list):
            ep_list = [str(x) for x in ep if str(x).strip()]
            if ep_list:
                json_data["entrypoint"] = ep_list
        elif isinstance(ep, str) and ep.strip():
            json_data["entrypoint"] = ep.strip()

    try:
        # Используем адрес хоста вместо глобального DOCKER_API_URL
        api_gateway = APIGateway(docker_api_host_url)
        logger.info("Using docker_api at %s for host %s", docker_api_host_url, host_id)
        start_exporter = api_gateway.make_request(
            method='POST',
            endpoint='/api/v1/manage/container/pull_and_run',
            json_data=json_data,
            timeout=300,
        )

        inner = (
            start_exporter.get("result")
            if isinstance(start_exporter, dict)
            else None
        )
        if isinstance(inner, dict) and inner.get("error"):
            logger.error(
                "docker_api pull_and_run returned error for %s: %s",
                container_id,
                inner["error"],
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(inner["error"]),
            )

        if not isinstance(inner, dict) or not inner.get("container_id"):
            logger.error(
                "docker_api pull_and_run missing container_id for %s, raw=%s",
                container_id,
                start_exporter,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    "docker_api returned success without container_id; "
                    "exporter was not started reliably."
                ),
            )

        logger.info("Exporter started successfully: %s", start_exporter)
        all_containers = docker_containers.get_containers()
        hp_live = resolve_scrape_host_port_for_workload(
            config_info=(config.config_metadata or {}).get("info"),
            exporter_internal_port=int(config.exporter_port) if config.exporter_port is not None else None,
            workload_container_name=config.container_name.lstrip("/"),
            redis_host_key=str(config_metadata.get("host_name") or "localhost"),
            all_containers=all_containers,
        )
        scrape_stored = int(hp_live) if hp_live is not None else int(port)
        md = dict(config.config_metadata or {})
        inf = dict(md.get("info") or {})
        inf["scrape_host_port"] = scrape_stored
        md["info"] = inf
        config.config_metadata = md
        flag_modified(config, "config_metadata")
        db.commit()
        db.refresh(config)

        try:
            await generate_config(container_id=config.container_id, host_id=str(host_dto.id), db=db)
        except Exception as sync_exc:
            logger.warning(
                "Regenerate Prometheus config after exporter start failed for %s: %s",
                container_id,
                sync_exc,
                exc_info=True,
            )
        try:
            mgr = get_prometheus_manager_gateway()
            mgr.make_request("POST", "/api/v1/manage/config/update", timeout=120.0)
        except Exception as mgr_exc:
            logger.warning(
                "Prometheus manager config pull after exporter start failed: %s",
                mgr_exc,
                exc_info=True,
            )

        return {
            "message": "Exporter started successfully",
            "exporter": start_exporter,
            "network": network_name,
            "environment": exporter_env_vars,
            "stack": config.stack,
            "scrape_host_port": scrape_stored,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to start exporter: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start exporter: {str(e)}",
        ) from e


@router.get("/get_signature", status_code=200)
async def get_signature() -> Dict[str, str]:
    """
    Получение файла с настройками генерации Prometheus Config.

    Returns:
        Dict[str, str]: Файл с настройками
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
    Обновление файла с настройками генерации Prometheus Config.

    Args:
        new_signature: Новая подпись для обновления

    Returns:
        Dict[str, str]: Результат обновления
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

    Args:
        db: Сессия базы данных

    Returns:
        dict[str, Any]: Словарь с общим количеством и списком конфигов
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

        logger.debug(
            "Looking for exporter: %s on host: %s "
            "(container_name: %s)",
            exporter_name, host_name, config.container_name
        )

        for container_id, container_data in all_containers.items():
            container_name = container_data.get("info", {}).get("Name", "").lstrip("/")
            container_host = redis_host_key_for_api_host_id(container_data)

            if "-exporter" in container_name.lower():
                logger.debug(
                    "Found potential exporter container: %s on host: %s",
                    container_name, container_host
                )

            if container_name.lower() == exporter_name.lower():
                if container_host == host_name:
                    container_status = container_data.get("info", {}).get("State", {}).get("Status", "")
                    exporter_running = container_status.lower() in ("running", "up")
                    exporter_container_id = container_id

                    logger.info(
                        "Found exporter: %s, host: %s, "
                        "status: %s, running: %s",
                        container_name, container_host,
                        container_status, exporter_running
                    )

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
                    container_status = container_data.get("info", {}).get("State", {}).get("Status", "")
                    exporter_running = container_status.lower() in ("running", "up")
                    exporter_container_id = container_id

                    logger.warning(
                        "Found exporter using fallback: %s, host: %s "
                        "(expected: %s), status: %s, running: %s",
                        container_name, container_host,
                        host_name, container_status, exporter_running
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
    Получает YAML файлы из MinIO по ID конфига из БД.

    Возвращает scrape_config.yml и targets файл.

    Args:
        config_id: Идентификатор конфига
        db: Сессия базы данных

    Returns:
        dict: Словарь с YAML файлами

    Raises:
        HTTPException: Если конфиг не найден
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

    Args:
        request: Запрос с данными о сервисе для добавления
        db: Сессия базы данных

    Returns:
        Dict[str, Any]: Результат добавления сервиса

    Raises:
        HTTPException: Если job_name не найден, конфиг не найден,
                       экспортер не найден или не запущен
    """
    logger.debug("Received request: %s", request.model_dump())
    logger.debug("scrape_config type: %s", type(request.scrape_config))
    logger.debug("scrape_config value: %s", request.scrape_config)

    job_name = None
    if request.scrape_config and isinstance(request.scrape_config, dict):
        scrape_configs = request.scrape_config.get('scrape_configs', [])
        logger.debug("scrape_configs: %s", scrape_configs)
        if scrape_configs and len(scrape_configs) > 0:
            if isinstance(scrape_configs[0], dict):
                job_name = scrape_configs[0].get('job_name')
            else:
                job_name = getattr(scrape_configs[0], 'job_name', None)

    logger.info("Extracted job_name: %s", job_name)

    if not job_name:
        logger.error("Job name not found in request. scrape_config: %s", request.scrape_config)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job name is required in scrape_config.scrape_configs[0].job_name"
        )

    config = db.query(PrometheusConfig).filter(
        PrometheusConfig.job_name == job_name,
        PrometheusConfig.status == "active"
    ).order_by(PrometheusConfig.created_at.desc()).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prometheus config with job_name '{job_name}' not found"
        )

    config_metadata = config.config_metadata or {}
    host_name = config_metadata.get('host_name', 'localhost')
    container_name = config.container_name.lstrip("/")
    exporter_name = f"{container_name}-exporter"

    docker_containers = DockerContainers()
    all_containers_data = docker_containers.get_containers()
    logger.info(
        "Checking exporter before adding to main config: exporter_name=%s, host_name=%s, job_name=%s",
        exporter_name, host_name, job_name
    )
    exporter_found, exporter_running, exporter_info, _ = _resolve_exporter_state(
        all_containers_data,
        host_name=host_name,
        container_name=container_name,
    )

    if not exporter_found:
        logger.warning("Exporter '%s' not found on host '%s'", exporter_name, host_name)
        all_exporters = [
            (data.get("info", {}).get("Name", "").lstrip("/"),
             redis_host_key_for_api_host_id(data))
            for data in all_containers_data.values()
            if isinstance(data, dict) and "-exporter" in data.get("info", {}).get("Name", "").lower()
        ]
        logger.debug("Available exporters: %s", all_exporters)

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
            detail=(
                f"Exporter '{exporter_name}' is not running (status: {exporter_status}). "
                f"Please start the exporter first before adding to main config."
            )
        )

    logger.info("Exporter check passed. Adding service '%s' to main config", job_name)

    hp = resolve_scrape_host_port_for_workload(
        config_info=(config.config_metadata or {}).get("info"),
        exporter_internal_port=config.exporter_port,
        workload_container_name=container_name,
        redis_host_key=host_name,
        all_containers=all_containers_data,
    )
    forward_request = request
    if hp is not None and config.exporter_port is not None:
        forward_request = AddServiceRequest(
            scrape_config=request.scrape_config,
            target=rewrite_targets_internal_port_to_host_port(
                request.target,
                internal_port=int(config.exporter_port),
                host_port=int(hp),
            ),
            target_name=request.target_name,
        )

    try:
        if not prometheus_generation_url:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="PROMETHEUS_GENERATION_URL is not configured"
            )

        logger.info(
            f"Making request to prometheus_generation service: "
            f"{prometheus_generation_url}/api/v1/main-config/add"
        )
        logger.debug("Request data: %s", forward_request.model_dump())

        api_gateway = APIGateway(prometheus_generation_url)
        result = api_gateway.make_request(
            method='POST',
            endpoint='/api/v1/main-config/add',
            json_data=forward_request.model_dump()
        )

        logger.info("Successfully added service '%s' to main config", job_name)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error adding service to main config: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add service to main config: {str(e)}"
        )


@router.delete("/main_config/remove", status_code=status.HTTP_200_OK)
async def remove_main_config_service(request: RemoveServiceRequest) -> Dict[str, Any]:
    """
    Удаляет сервис из основного конфига Prometheus.

    Args:
        request: Запрос с данными о сервисе для удаления

    Returns:
        Dict[str, Any]: Результат удаления сервиса
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
    Получает полный конфиг Prometheus и все файлы targets.

    Returns:
        Dict[str, Any]: Полный конфиг Prometheus и файлы targets.
                       Если конфиг еще не создан, возвращает пустую структуру.

    Raises:
        HTTPException: Если PROMETHEUS_GENERATION_URL не настроен или произошла ошибка
    """
    if not prometheus_generation_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PROMETHEUS_GENERATION_URL is not configured in environment"
        )
    try:
        api_gateway = APIGateway(prometheus_generation_url)
        result = api_gateway.make_request(
            method='GET',
            endpoint='/api/v1/main-config/'
        )
        return result
    except HTTPException as e:
        # Если конфиг не найден (404 или 500 с NoSuchKey), возвращаем пустую структуру
        if "NoSuchKey" in str(e.detail) or "does not exist" in str(e.detail):
            return {
                'main_config': None,
                'targets': {}
            }
        raise
    except Exception as e:
        # Если конфиг не найден, возвращаем пустую структуру вместо ошибки
        error_str = str(e)
        if "NoSuchKey" in error_str or "does not exist" in error_str:
            logger.info("Main config not found, returning empty structure")
            return {
                'main_config': None,
                'targets': {}
            }
        logger.error(
            "Error getting main config: %s",
            error_str,
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get main config: {error_str}"
        )


@router.post("/manager/start", status_code=status.HTTP_200_OK)
async def start_prometheus_manager() -> Dict[str, Any]:
    """
    Запускает Prometheus через Prometheus Manager сервис.

    Returns:
        Dict[str, Any]: Результат запуска Prometheus

    Raises:
        HTTPException: Если PROMETHEUS_MANAGER_URL не настроен
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

    Returns:
        Dict[str, Any]: Результат остановки Prometheus

    Raises:
        HTTPException: Если PROMETHEUS_MANAGER_URL не настроен
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

    Returns:
        Dict[str, Any]: Статус Prometheus

    Raises:
        HTTPException: Если PROMETHEUS_MANAGER_URL не настроен
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

    Returns:
        Dict[str, Any]: Настройки Prometheus

    Raises:
        HTTPException: Если PROMETHEUS_MANAGER_URL не настроен
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

    Args:
        settings: Новые настройки Prometheus

    Returns:
        Dict[str, Any]: Результат обновления настроек

    Raises:
        HTTPException: Если PROMETHEUS_MANAGER_URL не настроен
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
    Обновляет конфигурацию Prometheus из MinIO через Prometheus Manager сервис.

    Обновляет prometheus.yml и targets файлы.

    Returns:
        Dict[str, Any]: Результат обновления конфигурации

    Raises:
        HTTPException: Если PROMETHEUS_MANAGER_URL не настроен
    """
    api_gateway = get_prometheus_manager_gateway()
    result = api_gateway.make_request(
        method='POST',
        endpoint='/api/v1/manage/config/update',
    )
    return result
