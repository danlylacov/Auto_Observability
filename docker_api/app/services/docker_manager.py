import re

import docker


class DockerManager:
    def __init__(self):
        self.client = docker.from_env()

    def discover_containers(self) -> list:
        """
        Возвращает список словарей со всеми данными каждого контейнера
        """
        all_data = []
        for container in self.client.containers.list(all=True):
            all_data.append(container.attrs)
        return all_data

    def start_container(self, container_id_or_name: str) -> str:
        """Запустить контейнер"""
        try:
            container = self.client.containers.get(container_id_or_name)
            container.start()
            return f"Контейнер {container_id_or_name} запущен."
        except docker.errors.NotFound:
            return "Ошибка: Контейнер не найден."

    def stop_container(self, container_id_or_name: str) -> None:
        """Остановить контейнер"""
        try:
            container = self.client.containers.get(container_id_or_name)
            container.stop()
            return f"Контейнер {container_id_or_name} остановлен."
        except Exception as e:
            return f"Ошибка при остановке: {e}"

    def remove_container(self, container_id_or_name: str, force: bool = False) -> None:
        """Удалить контейнер (force=True удалит даже запущенный)"""
        try:
            container = self.client.containers.get(container_id_or_name)
            container.remove(force=force)
            return f"Контейнер {container_id_or_name} удален."
        except Exception as e:
            return f"Ошибка при удалении: {e}"

    def remove_volume(self, volume_name: str, force: bool = False) -> None:
        """Удалить volume"""
        try:
            volume = self.client.volumes.get(volume_name)
            volume.remove(force=force)
            return f"Том {volume_name} удален."
        except Exception as e:
            return f"Ошибка при удалении тома: {e}"

    def prune_volumes(self) -> dict:
        """Удалить ВСЕ неиспользуемые тома (очистка)"""
        return self.client.volumes.prune()

    def remove_image(self, image_id_or_name: str, force: bool = False) -> str:
        """Удалить образ"""
        try:
            self.client.images.remove(image=image_id_or_name, force=force)
            return f"Образ {image_id_or_name} удален."
        except Exception as e:
            return f"Ошибка при удалении образа: {e}"

    def cleanup_system(self) -> dict[str, str]:
        """Очистка системы: удаление всех остановленных контейнеров,
        неиспользуемых сетей и образов без тегов."""
        report = {
            "containers": self.client.containers.prune(),
            "networks": self.client.networks.prune(),
            "images": self.client.images.prune(),
            "volumes": self.client.volumes.prune()
        }
        return report
