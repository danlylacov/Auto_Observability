import json

from app.db.redis.redis_connection import RedisConnection


class DockerContainers(RedisConnection):
    """
    Класс для управления информацией о DockerContainers в Redis
    """
    def __init__(self) -> None:
        super().__init__()
        self.client = self.connect()

    def upload_containers(self, containers: dict) -> None:
        """
        Загрузка нескольких контейнеров
        """
        pipe = self.client.pipeline()
        for id, data in containers.items():
            pipe.set(f'container:{id}', json.dumps(data))
        pipe.execute()

    def upload_container(self, container_id: str, container_data: dict) -> None:
        """
        Зашрузка одного контейнера
        """
        self.client.set(f'container:{container_id}', json.dumps(container_data))

    def get_containers(self) -> dict:
        """
        Получает все контейнеры для указанного хоста
        """
        pattern = f'container:*'
        container_keys = self.client.keys(pattern)
        if not container_keys:
            return {}

        containers = {}
        pipe = self.client.pipeline()

        for key in container_keys:
            pipe.get(key)

        values = pipe.execute()

        for key, value in zip(container_keys, values):
            if value:
                container_id = key.decode('utf-8').split(':')[-1] if isinstance(key, bytes) else key.split(':')[-1]
                containers[container_id] = json.loads(value)
        return containers

    def delete_all_containers_by_host(self) -> int:
        """
        Удаляет все ключи с префиксом 'container:'
        Возвращает количество удаленных ключей
        """
        container_keys = self.client.keys(f'container:*')
        if not container_keys:
            print("Контейнеры не найдены")
            return 0
        deleted_count = self.client.delete(*container_keys)
        return deleted_count




