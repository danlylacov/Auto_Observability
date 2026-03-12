"""Hosts Redis storage module."""

import json
import logging

from app.db.redis.redis_connection import RedisConnection

logger = logging.getLogger(__name__)


class Hosts(RedisConnection):
    """
    Класс для управления информацией о хостах в Redis.

    Предоставляет методы для загрузки, получения и удаления данных о хостах.
    """

    def __init__(self) -> None:
        """
        Инициализация класса Hosts.

        Создает подключение к Redis.
        """
        super().__init__()
        self.client = self.connect()

    def upload_hosts(self, hosts: dict) -> None:
        """
        Загрузка информации о хостах в Redis.

        Args:
            hosts: Словарь с данными о хостах (host_id -> data)
        """
        pipe = self.client.pipeline()
        for host_id, data in hosts.items():
            pipe.set(f"host:{host_id}", json.dumps(data))
        pipe.execute()

    def get_hosts(self) -> dict[str, dict]:
        """
        Получение информации о всех хостах из Redis.

        Returns:
            dict[str, dict]: Словарь с данными о хостах (host_id -> data)
        """
        keys = self.client.keys("host:*")

        if not keys:
            return {}

        pipe = self.client.pipeline()
        for key in keys:
            pipe.get(key)

        values = pipe.execute()

        hosts = {}
        for key, value in zip(keys, values):
            if value:
                host_id = (
                    key.decode('utf-8').split(':')[1]
                    if isinstance(key, bytes)
                    else key.split(':')[1]
                )
                hosts[host_id] = json.loads(value)
        return hosts

    def delete_hosts(self, host_id: str = None) -> int:
        """
        Удаляет хост или все хосты из Redis.

        Args:
            host_id: Идентификатор хоста для фильтрации. Если None, удаляет все хосты.

        Returns:
            int: Количество удаленных ключей
        """
        if host_id:
            # Удаляем конкретный хост по точному ключу
            key = f"host:{host_id}"
            deleted_count = self.client.delete(key)
            logger.debug(f"Deleted host key: {key}, count: {deleted_count}")
            return deleted_count
        else:
            # Удаляем все хосты
            pattern = "host:*"
            container_keys = self.client.keys(pattern)
            if not container_keys:
                logger.debug("Хосты не найдены")
                return 0
            deleted_count = self.client.delete(*container_keys)
            logger.debug(f"Deleted all hosts, count: {deleted_count}")
            return deleted_count

