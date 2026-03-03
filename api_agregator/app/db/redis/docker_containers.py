import json

from app.db.redis.redis_connection import RedisConnection


class DockerContainers(RedisConnection):
    """
    Класс для управления информацией о DockerContainers в Redis
    """

    def __init__(self) -> None:
        super().__init__()
        self.client = self.connect()

    def upload_containers(self, containers: dict, host_name: str) -> None:
        """
        Загрузка нескольких контейнеров
        """
        pipe = self.client.pipeline()
        for id, data in containers.items():
            # гарантируем, что в данных есть информация о хосте
            if isinstance(data, dict):
                data.setdefault("host_name", host_name)
            pipe.set(f"container:{host_name}:{id}", json.dumps(data))
        pipe.execute()

    def upload_container(self, container_id: str, container_data: dict, host_name: str) -> None:
        """
        Зашрузка одного контейнера
        """
        if isinstance(container_data, dict):
            container_data.setdefault("host_name", host_name)
        self.client.set(f"container:{host_name}:{container_id}", json.dumps(container_data))

    def get_containers(self, host_name: str | None = None) -> dict:
        """
        Получает все контейнеры
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

            # ключ формата container:{host_name}:{container_id}
            key_str = key.decode("utf-8") if isinstance(key, bytes) else key
            _, key_host_name, container_id = key_str.split(":", 2)

            data = json.loads(value)

            # дописываем host_name, если его не было в payload
            if isinstance(data, dict):
                data.setdefault("host_name", key_host_name)

            # Если запрошен конкретный хост, то просто мапа id -> data
            if host_name:
                containers[container_id] = data
            else:
                # При отсутствии host_name агрегируем по всем хостам.
                # Для фронта по-прежнему удобно иметь плоскую структуру id -> data.
                containers[container_id] = data
        return containers

    def get_container(self, container_id: str, host_name: str) -> dict:
        """
        Возвращает один контейнер по id и имени хоста.
        """
        key = f"container:{host_name}:{container_id}"
        value = self.client.get(key)
        if not value:
            return {}
        data = json.loads(value)
        if isinstance(data, dict):
            data.setdefault("host_name", host_name)
        return data

    def delete_all_containers_by_host(self, host_name: str = None) -> int:
        """
        Удаляет все ключи с префиксом 'container:'
        Возвращает количество удаленных ключей
        """
        pattern = f"container:{host_name}:*" if host_name else "container:*"
        container_keys = self.client.keys(pattern)
        if not container_keys:
            print("Контейнеры не найдены")
            return 0
        deleted_count = self.client.delete(*container_keys)
        return deleted_count
