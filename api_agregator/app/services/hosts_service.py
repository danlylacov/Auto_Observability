from typing import List

import requests
from sqlalchemy.orm import Session

from app.models.postgres.host import Host
from app.db.redis.hosts import Hosts


class HostDTO:
    """
    Простая DTO-модель для целевого хоста docker_api.

    Предоставляет структурированное представление хоста с базовым URL.
    """

    def __init__(self, host_id: str, name: str, host: str, port: int):
        """
        Инициализация DTO хоста.

        Args:
            host_id: Идентификатор хоста
            name: Имя хоста
            host: Адрес хоста
            port: Порт хоста
        """
        self.id = host_id
        self.name = name
        self.host = host
        self.port = port

    @property
    def base_url(self) -> str:
        """
        Базовый URL для docker_api на данном хосте.

        Returns:
            str: URL в формате http://host:port
        """
        return f"http://{self.host}:{self.port}"


class HostsService:
    """
    Сервис для работы со списком целевых хостов.

    Предоставляет методы для получения хостов из БД и синхронизации с Redis.
    """

    def __init__(self, db: Session):
        """
        Инициализация сервиса хостов.

        Args:
            db: Сессия базы данных SQLAlchemy
        """
        self.db = db
        self.redis_hosts = Hosts()

    def get_all_hosts_from_db(self) -> List[HostDTO]:
        """
        Возвращает все хосты из БД в виде DTO.

        Returns:
            List[HostDTO]: Список DTO хостов
        """
        hosts: List[Host] = self.db.query(Host).all()
        return [HostDTO(host_id=h.id, name=h.name, host=h.host, port=h.port) for h in hosts]

    def get_host_by_id(self, host_id: str) -> HostDTO | None:
        """
        Возвращает хост по его id или None.

        Args:
            host_id: Идентификатор хоста

        Returns:
            HostDTO | None: DTO хоста или None, если не найден
        """
        host: Host | None = self.db.query(Host).filter(Host.id == host_id).first()
        if not host:
            return None
        return HostDTO(host_id=host.id, name=host.name, host=host.host, port=host.port)

    def upload_hosts(self) -> dict[str, dict]:
        """
        Проверяет хосты на работоспособность и записывает результат в Redis.

        Returns:
            dict[str, dict]: Словарь с данными о хостах (host_id -> data)
        """
        hosts = self.get_all_hosts_from_db()
        result = {}
        for host in hosts:
            result[host.id] = {'name': host.name, 'host': host.host, 'port': host.port}
            try:
                result[host.id]['status'] = requests.get(f'{host.base_url}/health').status_code
            except (Exception,):
                result[host.id]['status'] = 'down'
        self.redis_hosts.delete_hosts()
        self.redis_hosts.upload_hosts(result)
        return result

    def get_all_hosts(self) -> list:
        """
        Возвращает все хосты из Redis.

        Returns:
            list: Список хостов
        """
        return self.redis_hosts.get_hosts()



