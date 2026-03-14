import logging
import os

import docker
import yaml

logger = logging.getLogger(__name__)


class PrometheusManager:
    def __init__(self, config_path: str = None):
        self.client = docker.from_env()

        host_config_path = os.environ.get('PROMETHEUS_CONFIG_HOST_PATH')
        if host_config_path:
            self.config_dir = host_config_path
            self.config_path = os.path.join(host_config_path, 'prometheus.yml')
        elif config_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(current_dir, 'prometheus', 'prometheus.yml')
            self.config_path = os.path.abspath(config_path)
            self.config_dir = os.path.dirname(self.config_path)
        else:
            self.config_path = os.path.abspath(config_path)
            self.config_dir = os.path.dirname(self.config_path)
        
        self.container = None
        self.prometheus_settings = self.get_prometheus_settings()
        self.container_name = self.prometheus_settings["prometheus-settings"]["name"]

    def start(self):
        """
        Запускает контейнер с монтированием всей директории prometheus/.

        Returns:
            bool: True если контейнер запущен успешно, False при ошибке
        """
        self.stop()

        try:


            volumes = {
                self.config_dir: {
                    'bind': '/etc/prometheus',
                    'mode': 'ro'
                }
            }


            self.container = self.client.containers.run(
                image=self.prometheus_settings["prometheus-settings"]["image"],
                name=self.container_name,
                network_mode='host',
                volumes=volumes,
                detach=True,
                restart_policy={"Name": "unless-stopped"}
            )

            return True

        except Exception as e:
            logger.error(f"Ошибка запуска: {e}", exc_info=True)
            return False

    def stop(self) -> bool:
        """
        Останавливает и удаляет контейнер.

        Returns:
            bool: True если контейнер остановлен успешно, False при ошибке
        """
        try:
            container = self.client.containers.get(self.container_name)
            container.stop()
            container.remove()
            return True
        except Exception as e:
            logger.error(f"Ошибка при остановке: {e}")
            return False

    def status(self) -> dict:
        """
        Проверяет статус контейнера.

        Returns:
            dict: Статус контейнера
        """
        try:
            container = self.client.containers.get(self.container_name)
            return {
                'status': container.status,
                'created': container.attrs['Created']
            }
        except docker.errors.NotFound:
            return {'status': 'not found'}

    @staticmethod
    def get_prometheus_settings(file_path: str = None) -> dict[str, dict[str, str]]:
        """
        Извлекает все переменные из YAML файла с настройками Prometheus.

        Args:
            file_path: Путь к файлу настроек. Если None, используется файл в текущей директории.

        Returns:
            dict[str, dict[str, str]]: Настройки Prometheus
        """
        if file_path is None:
            file_path = os.path.join(os.path.dirname(__file__), 'prometheus_settings.yml')
        with open(file_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
        return data

    @staticmethod
    def update_prometheus_settings(settings: dict[str, dict[str, str]],
                                   file_path: str = None):
        """
        Обновляет YAML файл с настройками Prometheus.

        Args:
            settings: Новые настройки Prometheus
            file_path: Путь к файлу настроек. Если None, используется файл в текущей директории.

        Returns:
            bool: True при успешном обновлении
        """
        if file_path is None:
            file_path = os.path.join(os.path.dirname(__file__), 'prometheus_settings.yml')
        with open(file_path, 'w', encoding='utf-8') as file:
            yaml.dump(settings, file)
        return True
