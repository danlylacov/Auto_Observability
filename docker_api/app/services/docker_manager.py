import logging
from typing import Optional, Dict

import docker

logger = logging.getLogger(__name__)


class DockerManager:
    """
    Класс для управления Docker контейнерами.

    Предоставляет методы для работы с контейнерами, образами, томами и сетями Docker.
    """

    def __init__(self):
        """
        Инициализация DockerManager.

        Создает клиент Docker из переменных окружения.
        """
        self.client = docker.from_env()

    def discover_containers(self) -> list:
        """
        Возвращает список словарей со всеми данными каждого контейнера.

        Returns:
            list: Список словарей с данными контейнеров
        """
        all_data = []
        for container in self.client.containers.list(all=True):
            all_data.append(container.attrs)
        return all_data

    def start_container(self, container_id_or_name: str) -> str:
        """
        Запустить контейнер.

        Args:
            container_id_or_name: Идентификатор или имя контейнера

        Returns:
            str: Сообщение о результате операции
        """
        try:
            container = self.client.containers.get(container_id_or_name)
            container.start()
            return f"Контейнер {container_id_or_name} запущен."
        except docker.errors.NotFound:
            return "Ошибка: Контейнер не найден."

    def pull_and_run_container(
            self,
            image_name: str,
            command: Optional[str] = None,
            name: Optional[str] = None,
            detach: bool = True,
            ports: Optional[Dict[str, int]] = None,
            volumes: Optional[Dict[str, Dict[str, str]]] = None,
            environment: Optional[Dict[str, str]] = None,
            network: Optional[str] = None,
            network_mode: Optional[str] = None
    ) -> dict:
        """
        Загружает образ и запускает контейнер.

        Args:
            image_name: Имя образа Docker
            command: Команда для запуска контейнера
            name: Имя контейнера
            detach: Запуск в фоновом режиме
            ports: Маппинг портов
            volumes: Маппинг томов
            environment: Переменные окружения
            network: Имя сети
            network_mode: Режим сети

        Returns:
            dict: Результат операции с container_id и pull_status или ошибка
        """
        try:
            try:
                self.client.images.get(image_name)
                pull_status = "использован локальный образ"
            except docker.errors.ImageNotFound:
                logger.info(f"Образ {image_name} не найден локально. Выполняется pull...")
                self.client.images.pull(image_name)
                pull_status = "образ успешно загружен"

            if name:
                try:
                    container = self.client.containers.get(name)
                    if container.status == "running":
                        container_id = (
                            container.short_id if hasattr(container, 'short_id')
                            else str(container.id)[:12]
                        )
                        return {
                            "status": "Контейнер уже запущен",
                            "container_id": container_id
                        }
                    else:
                        container.start()
                        container_id = (
                            container.short_id if hasattr(container, 'short_id')
                            else str(container.id)[:12]
                        )
                        return {
                            "status": "Контейнер перезапущен",
                            "container_id": container_id,
                            "pull_status": pull_status
                        }
                except docker.errors.NotFound:
                    pass
                except Exception as e:
                    return {'error': f"Ошибка при проверке существующего контейнера: {e}"}

            run_kwargs = {
                "image": image_name,
                "detach": detach
            }

            if command is not None:
                run_kwargs["command"] = command
            if name is not None:
                run_kwargs["name"] = name
            if ports is not None:
                run_kwargs["ports"] = ports
            if volumes is not None:
                run_kwargs["volumes"] = volumes
            if environment is not None:
                run_kwargs["environment"] = environment
            if network_mode is not None:
                run_kwargs["network_mode"] = network_mode
            if network is not None and network_mode is None:
                run_kwargs["network"] = network

            container = self.client.containers.run(**run_kwargs)

            container_id = (
                container.short_id if hasattr(container, 'short_id')
                else str(container.id)[:12]
            )
            return {'container_id': container_id, 'pull_status': pull_status}

        except Exception as e:
            return {'error': f"Неожиданная ошибка при запуске контейнера: {e}"}

    def stop_container(self, container_id_or_name: str) -> str:
        """
        Остановить контейнер.

        Args:
            container_id_or_name: Идентификатор или имя контейнера

        Returns:
            str: Сообщение о результате операции
        """
        try:
            container = self.client.containers.get(container_id_or_name)
            container.stop()
            return f"Контейнер {container_id_or_name} остановлен."
        except Exception as e:
            return f"Ошибка при остановке: {e}"

    def remove_container(self, container_id_or_name: str, force: bool = False) -> None:
        """
        Удалить контейнер.

        Args:
            container_id_or_name: Идентификатор или имя контейнера
            force: Принудительное удаление (удалит даже запущенный)

        Returns:
            str: Сообщение о результате операции
        """
        try:
            container = self.client.containers.get(container_id_or_name)
            container.remove(force=force)
            return f"Контейнер {container_id_or_name} удален."
        except Exception as e:
            return f"Ошибка при удалении: {e}"

    def remove_volume(self, volume_name: str, force: bool = False) -> None:
        """
        Удалить том.

        Args:
            volume_name: Имя тома
            force: Принудительное удаление

        Returns:
            str: Сообщение о результате операции
        """
        try:
            volume = self.client.volumes.get(volume_name)
            volume.remove(force=force)
            return f"Том {volume_name} удален."
        except Exception as e:
            return f"Ошибка при удалении тома: {e}"

    def prune_volumes(self) -> dict:
        """
        Удалить все неиспользуемые тома.

        Returns:
            dict: Результат операции очистки
        """
        return self.client.volumes.prune()

    def remove_image(self, image_id_or_name: str, force: bool = False) -> str:
        """
        Удалить образ.

        Args:
            image_id_or_name: Идентификатор или имя образа
            force: Принудительное удаление

        Returns:
            str: Сообщение о результате операции
        """
        try:
            self.client.images.remove(image=image_id_or_name, force=force)
            return f"Образ {image_id_or_name} удален."
        except Exception as e:
            return f"Ошибка при удалении образа: {e}"

    def cleanup_system(self) -> dict[str, str]:
        """
        Очистка системы: удаление всех остановленных контейнеров,
        неиспользуемых сетей и образов без тегов.

        Returns:
            dict[str, str]: Отчет об очистке системы
        """
        report = {
            "containers": self.client.containers.prune(),
            "networks": self.client.networks.prune(),
            "images": self.client.images.prune(),
            "volumes": self.client.volumes.prune()
        }
        return report
