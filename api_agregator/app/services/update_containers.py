import json
import logging
import os
from typing import Any, Dict

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from app.db.postgres.database import get_db
from app.db.redis.docker_containers import DockerContainers
from app.services.api_getaway import APIGateway
from app.services.hosts_service import HostsService

logger = logging.getLogger(__name__)


class UpdateContainers:
    """
    Сервисный класс для обновления информации о контейнерах.

    Предоставляет методы для получения информации о контейнерах со всех хостов
    и сохранения их в Redis.
    """

    def __init__(self, db: Session | None = None):
        """
        Инициализация сервиса обновления контейнеров.

        Для корректной работы в FastAPI рекомендуется передавать Session через Depends,
        но класс используется и в задачах, поэтому оставляем возможность
        ленивого получения сессии.

        Args:
            db: Сессия базы данных SQLAlchemy. Если None, будет получена лениво.
        """
        load_dotenv()
        self._external_db: Session | None = db
        docker_classification_api_url = os.getenv("DOCKER_CLASSIFICATION_API_URL")
        self._classification_gateway = (
            APIGateway(docker_classification_api_url) if docker_classification_api_url else None
        )

    def _get_db(self) -> Session:
        """
        Получение сессии базы данных.

        Returns:
            Session: Сессия базы данных
        """
        if self._external_db is not None:
            return self._external_db
        return next(get_db())

    def _classificate_container(
        self,
        container: Dict[str, Any],
        classification_gateway: APIGateway,
    ) -> Dict[str, Any]:
        """
        Классификация контейнера (определение технологий) по информации о нем.

        Args:
            container: Данные о контейнере из Docker API
            classification_gateway: Gateway для обращения к сервису классификации

        Returns:
            Dict[str, Any]: Результат классификации
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

        Returns:
            Dict[str, Dict[str, Dict[str, Any]]]: Словарь с данными о контейнерах:
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
        hosts = hosts_service.get_all_hosts()

        logger.debug(f"Получено хостов: {len(hosts)}")

        result: Dict[str, Dict[str, Dict[str, Any]]] = {}

        for host_id, host_data in hosts.items():
            # Преобразуем localhost в host.docker.internal для Docker
            host = host_data["host"]
            if os.path.exists('/.dockerenv'):
                if host in ('localhost', '127.0.0.1', '0.0.0.0'):
                    host = 'host.docker.internal'
            
            docker_api = APIGateway(f'http://{host}:{host_data["port"]}')
            # Уменьшаем таймаут для запросов к хостам, чтобы не зависать
            docker_api.timeout = 5

            try:
                response = docker_api.make_request(
                    method="POST",
                    endpoint="/api/v1/discover/",
                )
            except Exception as e:
                logger.warning(f"Failed to get containers from host {host_id} ({host}:{host_data['port']}): {e}")
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
                    "host_id": host_id,
                    "host_name": host_data['name'],
                }

            result[host_id] = host_containers

        return result

    def upload_containers(self) -> None:
        """
        Обновление информации о контейнерах в Redis.

        Получает данные о всех контейнерах со всех хостов и сохраняет их в Redis.
        Использует атомарную операцию для предотвращения race conditions:
        1. Сначала загружаем все новые контейнеры
        2. Затем удаляем только те старые, которых нет в новых данных
        
        Важно: Если не удалось получить контейнеры с хостов (ошибка подключения),
        старые контейнеры НЕ удаляются, чтобы избежать потери данных.
        """
        all_containers_by_host = self._get_all_hosts_containers()
        docker_containers = DockerContainers()
        
        logger.info(f"Updating containers for {len(all_containers_by_host)} hosts")
        
        # Проверяем, есть ли хосты с контейнерами
        total_containers_count = sum(len(containers) for containers in all_containers_by_host.values())
        
        if total_containers_count == 0:
            logger.warning(
                "No containers received from any host. "
                "This might indicate connection issues. "
                "Keeping existing containers in Redis to prevent data loss."
            )
            return
        
        # Собираем множество новых ключей для проверки
        new_keys = set()
        pipe = docker_containers.client.pipeline()
        total_containers = 0
        
        # Сначала загружаем все новые контейнеры
        for host_id, containers in all_containers_by_host.items():
            logger.debug(f"Processing {len(containers)} containers for host {host_id}")
            for container_id, data in containers.items():
                if isinstance(data, dict):
                    data.setdefault("host_name", host_id)
                key = f"container:{host_id}:{container_id}"
                new_keys.add(key)
                pipe.set(key, json.dumps(data))
                total_containers += 1
        
        # Выполняем загрузку новых контейнеров
        if new_keys:
            try:
                pipe.execute()
                logger.info(f"Loaded {len(new_keys)} new containers into Redis (total: {total_containers})")
            except Exception as e:
                logger.error(f"Error loading containers into Redis: {e}", exc_info=True)
                raise
        
        # Удаляем только те старые контейнеры, которых нет в новых данных
        # Только если мы успешно загрузили новые контейнеры
        if new_keys:
            old_keys = docker_containers.client.keys("container:*")
            # Преобразуем bytes в строки для сравнения
            old_keys_str = {
                k.decode('utf-8') if isinstance(k, bytes) else k 
                for k in old_keys
            }
            keys_to_delete = list(old_keys_str - new_keys)
            
            if keys_to_delete:
                deleted_count = docker_containers.client.delete(*keys_to_delete)
                logger.info(f"Deleted {deleted_count} old containers that are no longer present")

