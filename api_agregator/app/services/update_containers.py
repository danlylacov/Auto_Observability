from typing import Dict, Any
import os

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from app.db.redis.docker_containers import DockerContainers
from app.services.api_getaway import APIGateway
from app.services.hosts_service import HostsService, HostDTO
from app.db.postgres.database import get_db


class UpdateContainers:
    """
    Сервисный класс для обновления информации о контейнерах
    """

    def __init__(self, db: Session | None = None):
        """
        Для корректной работы в FastAPI рекомендуется передавать Session через Depends,
        но на данный момент класс используется и в задачах, поэтому оставляем
        возможность ленивого получения сессии.
        """
        load_dotenv()
        self._external_db: Session | None = db
        docker_classification_api_url = os.getenv("DOCKER_CLASSIFICATION_API_URL")
        self._classification_gateway = (
            APIGateway(docker_classification_api_url) if docker_classification_api_url else None
        )

    def _get_db(self) -> Session:
        if self._external_db is not None:
            return self._external_db
        # ленивое получение сессии для фоновых задач / вызовов вне запроса
        return next(get_db())

    def _classificate_container(
        self,
        container: Dict[str, Any],
        classification_gateway: APIGateway,
    ) -> Dict[str, Any]:
        """
        Классификация контейнера (определение технологий) по информации о нем
        """
        container_params = {
            "labels": container.get("Config", {}).get("Labels"),
            "envs": container.get("Config", {}).get("Env"),
            "image": container.get("Config", {}).get("Image"),
            "ports": [
                port.split("/")[0]
                for port in container.get("Config", {}).get("ExposedPorts", {}).keys()
            ]
            if container.get("Config", {}).get("ExposedPorts")
            else [],
        }
        classificate_response = classification_gateway.make_request(
            method="POST",
            endpoint="/api/v1/classificate/",
            json_data=container_params
        )
        return classificate_response

    def _get_all_hosts_containers(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Получение всех контейнеров по всем хостам.

        Структура результата:
        {
            host_id: {
                container_id: {
                    "info": {...},
                    "classification": {...}
                },
                ...
            },
            ...
        }
        """
        db = self._get_db()
        hosts_service = HostsService(db)
        hosts: list[HostDTO] = hosts_service.get_all_hosts()

        result: Dict[str, Dict[str, Dict[str, Any]]] = {}

        for host in hosts:
            docker_api = APIGateway(host.base_url)

            try:
                response = docker_api.make_request(
                    method="POST",
                    endpoint="/api/v1/discover/",
                )
            except Exception:
                # best-effort: если хост недоступен, просто пропускаем его
                continue

            containers = response.get("containers", [])
            host_containers: Dict[str, Dict[str, Any]] = {}

            for container in containers:
                container_id = container.get("Id")
                if not container_id:
                    continue
                if self._classification_gateway is None:
                    classification = {}
                else:
                    classification = self._classificate_container(
                        container=container,
                        classification_gateway=self._classification_gateway,
                    )
                host_containers[container_id] = {
                    "info": container,
                    "classification": classification,
                    "host_id": host.id,
                    "host_name": host.name,
                }

            result[host.id] = host_containers

        return result

    def upload_containers(self) -> None:
        """
        Обновление информации о контейнерах в Redis
        """
        all_containers_by_host = self._get_all_hosts_containers()
        docker_containers = DockerContainers()
        docker_containers.delete_all_containers_by_host()
        for host_id, containers in all_containers_by_host.items():
            docker_containers.upload_containers(containers, host_id)

