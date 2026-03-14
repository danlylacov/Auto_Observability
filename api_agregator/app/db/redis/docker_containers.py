"""Docker containers Redis storage module."""

import json
import logging

from app.db.redis.redis_connection import RedisConnection

logger = logging.getLogger(__name__)


class DockerContainers(RedisConnection):
    """
    Класс для управления информацией о Docker контейнерах в Redis.

    Предоставляет методы для загрузки, получения и удаления данных о контейнерах.
    """

    def __init__(self) -> None:
        """
        Инициализация класса DockerContainers.

        Создает подключение к Redis.
        """
        super().__init__()
        self.client = self.connect()

    def upload_containers(self, containers: dict, host_name: str) -> None:
        """
        Загрузка нескольких контейнеров в Redis.

        Args:
            containers: Словарь с данными о контейнерах (id -> data)
            host_name: Имя хоста, к которому относятся контейнеры
        """
        pipe = self.client.pipeline()
        for container_id, data in containers.items():
            if isinstance(data, dict):
                data.setdefault("host_name", host_name)
            pipe.set(f"container:{host_name}:{container_id}", json.dumps(data))
        pipe.execute()

    def upload_container(self, container_id: str, container_data: dict, host_name: str) -> None:
        """
        Загрузка одного контейнера в Redis.

        Args:
            container_id: Идентификатор контейнера
            container_data: Данные о контейнере
            host_name: Имя хоста, к которому относится контейнер
        """
        if isinstance(container_data, dict):
            container_data.setdefault("host_name", host_name)
        self.client.set(f"container:{host_name}:{container_id}", json.dumps(container_data))

    def get_containers(self, host_name: str | None = None) -> dict:
        """
        Получает все контейнеры из Redis.

        Args:
            host_name: Имя хоста для фильтрации. Если None, возвращает все контейнеры.

        Returns:
            dict: Словарь с данными о контейнерах (container_id -> data)
        """
        pattern = f"container:{host_name}:*" if host_name else "container:*"
        container_keys = self.client.keys(pattern)
        if not container_keys:
            return {}

        containers: dict = {}
        pipe = self.client.pipeline()

        for key in container_keys:
            pipe.get(key)

        values = pipe.execute()

        for key, value in zip(container_keys, values):
            if not value:
                continue

            key_str = key.decode("utf-8") if isinstance(key, bytes) else key
            _, key_host_name, container_id = key_str.split(":", 2)

            data = json.loads(value)

            if isinstance(data, dict):
                data.setdefault("host_name", key_host_name)

            containers[container_id] = data
        return containers

    def get_container(self, container_id: str, host_id: str) -> dict:
        """
        Возвращает один контейнер по id и имени хоста.

        Args:
            container_id: Идентификатор контейнера
            host_id: Идентификатор хоста

        Returns:
            dict: Данные о контейнере или пустой словарь, если не найден
        """
        key = f"container:{host_id}:{container_id}"
        value = self.client.get(key)
        if not value:
            return {}
        data = json.loads(value)
        if isinstance(data, dict):
            data.setdefault("host_name", host_id)
        return data

    def delete_all_containers_by_host(self, host_name: str = None) -> int:
        """
        Удаляет все ключи с префиксом 'container:' из Redis.

        Args:
            host_name: Имя хоста для фильтрации. Если None, удаляет все контейнеры.

        Returns:
            int: Количество удаленных ключей
        """
        pattern = f"container:{host_name}:*" if host_name else "container:*"
        container_keys = self.client.keys(pattern)
        if not container_keys:
            return 0
        deleted_count = self.client.delete(*container_keys)
        return deleted_count
