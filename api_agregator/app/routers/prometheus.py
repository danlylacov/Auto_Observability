import json
import logging
import os
from typing import Any

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.postgres.database import get_db
from app.db.redis.docker_containers import DockerContainers
from app.models.postgres.container import Container
from app.models.postgres.prometheus_config import PrometheusConfig
from app.services.api_getaway import APIGateway

router = APIRouter()
logger = logging.getLogger(__name__)

load_dotenv()
prometheus_generation_url = os.getenv("PROMETHEUS_GENERATION_URL")
docker_api_url = os.getenv("DOCKER_API_URL")


@router.post("/generate_config", status_code=status.HTTP_200_OK)
async def generate_config(
        container_id: str,
        db: Session = Depends(get_db)
) -> dict[str, Any]:
    """
    Генерация конфига прометеус и сохранение в БД.
    """
    docker_containers = DockerContainers()
    container_data_str = docker_containers.get_container(container_id)

    if not container_data_str:
        return {"error": "Container not found"}

    container_data = json.loads(container_data_str)
    info = container_data.get("info", {})
    classification = container_data.get("classification", {})

    api_gateway = APIGateway(prometheus_generation_url)
    config_data = api_gateway.make_request(
        method='POST',
        endpoint='/api/v1/generate/',
        json_data=container_data,
    )

    config_info = config_data.get("info", {})
    config_file = config_data.get("config", {})

    container = db.query(Container).filter(Container.id == container_id).first()

    if not container:
        stack = None
        classification_score = None
        if classification.get("result"):
            stack = classification["result"][0][0] if classification["result"] else None
            classification_score = classification.get("result")

        container = Container(
            id=container_id,
            name=info.get("Name", "").lstrip("/") or info.get("Config", {}).get("Hostname", "unknown"),
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
        if classification.get("result"):
            container.stack = classification["result"][0][0] if classification["result"] else container.stack
            container.classification_score = classification.get("result")

    prometheus_config = PrometheusConfig(
        container_id=container_id,
        container_name=config_info.get("container_name"),
        stack=config_info.get("stack"),
        exporter_image=config_info.get("exporter_image"),
        exporter_port=config_info.get("exporter_port"),
        target_address=config_info.get("target_address"),
        job_name=config_info.get("job_name"),
        minio_bucket=config_file.get("bucket"),
        minio_file_path=config_file.get("file"),
        status="active",
        config_metadata=config_data
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
    Запуск образа экспортера

    TODO: Запускать в одной сети докер с контенером для мониторинга. Продумать, как обрабатывать параметры. Добавить очереди (Celery)
    """
    config = db.query(PrometheusConfig).filter(
        PrometheusConfig.container_id == container_id,
        PrometheusConfig.status == "active"
    ).order_by(PrometheusConfig.created_at.desc()).first()

    if not config:
        return {
            "error": "No active config found for this container",
            "container_id": container_id
        }

    exporter_image = config.exporter_image

    api_gateway = APIGateway(docker_api_url)
    start_exporter = api_gateway.make_request(
        method='POST',
        endpoint='/api/v1/manage/container/pull_and_run',
        json_data={
            "image_name": exporter_image,
            "name": f"{config.container_name}-exporter",
            "ports": {f"{config.exporter_port}/tcp": port},
        },
    )

    print("start_exporter", start_exporter)
    return start_exporter
