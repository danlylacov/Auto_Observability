from typing import List

import requests
from sqlalchemy.orm import Session

from app.models.postgres.host import Host
from app.db.redis.hosts import Hosts

class HostDTO:
    """
    Простая DTO-модель для целевого хоста docker_api.
    """

    def __init__(self, id: str, name: str, host: str, port: int):
        self.id = id
        self.name = name
        self.host = host
        self.port = port

    @property
    def base_url(self) -> str:
        """
        Базовый URL для docker_api на данном хосте.
        """
        return f"http://{self.host}:{self.port}"


class HostsService:
    """
    Сервис для работы со списком целевых хостов.
    """

    def __init__(self, db: Session):
        self.db = db
        self.redis_hosts = Hosts()

    def get_all_hosts_from_db(self) -> List[HostDTO]:
        """
        Возвращает все хосты из БД в виде DTO.
        """
        hosts: List[Host] = self.db.query(Host).all()
        return [HostDTO(id=h.id, name=h.name, host=h.host, port=h.port) for h in hosts]

    def get_host_by_id(self, host_id: str) -> HostDTO | None:
        """
        Возвращает хост по его id или None.
        """
        host: Host | None = self.db.query(Host).filter(Host.id == host_id).first()
        if not host:
            return None
        return HostDTO(id=host.id, name=host.name, host=host.host, port=host.port)

    def upload_hosts(self) -> dict[str, dict]:
        """
        Проверяет хосты на работоспособность и записывает результат в redis
        """
        hosts = self.get_all_hosts_from_db()
        result = {}
        for host in hosts:
            result[host.id] = {'name': host.name, 'host': host.host, 'port': host.port}
            try:
                result[host.id]['status'] = requests.get(f'{host.base_url}/health').status_code
            except (Exception,):
                result[host.id]['status'] = 'down'
        self.redis_hosts.upload_hosts(result)
        return result

    def get_all_hosts(self) -> list:
        self.redis_hosts.get_hosts()
        return self.redis_hosts.get_hosts()



