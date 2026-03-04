import json

from app.db.redis.redis_connection import RedisConnection


class Hosts(RedisConnection):
    """
    Класс для управления информацией о Hosts в Redis
    """

    def __init__(self) -> None:
        super().__init__()
        self.client = self.connect()

    def upload_hosts(self, hosts: dict) -> None:
        """
        Загрузка информации о хостах
        """
        pipe = self.client.pipeline()
        for id, data in hosts.items():
            pipe.set(f"host:{id}", json.dumps(data))
        pipe.execute()

    def get_hosts(self) -> dict[str, dict]:
        """
        Получение информации о всех хостах из Redis
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
                host_id = key.decode('utf-8').split(':')[1] if isinstance(key, bytes) else key.split(':')[1]
                hosts[host_id] = json.loads(value)
        return hosts


    def delete_hosts(self, host_id: str = None) -> int:
        """
        Удаляет хост или все хосты
        """
        pattern = f"host:{host_id}:*" if host_id else "host:*"
        container_keys = self.client.keys(pattern)
        if not container_keys:
            print("Хосты не найдены")
            return 0
        deleted_count = self.client.delete(*container_keys)
        return deleted_count


