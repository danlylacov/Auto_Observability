import docker
import time
import os
import yaml


class PrometheusManager:
    def __init__(self, config_path: str = None):
        self.client = docker.from_env()
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), 'prometheus', 'prometheus.yml')
        self.config_path = os.path.abspath(config_path)
        self.config_dir = os.path.dirname(self.config_path)  # директория prometheus/
        self.container = None
        self.prometheus_settings = self.get_prometheus_settings()
        self.container_name = self.prometheus_settings["prometheus-settings"]["name"]

    def start(self):
        """Запускает контейнер с монтированием всей директории prometheus/"""
        self.stop()

        try:
            volumes = {
                self.config_dir: {
                    'bind': '/etc/prometheus',
                    'mode': 'ro'
                }
            }

            # Используем network_mode: host для прямого доступа к хосту
            # Это позволяет Prometheus обращаться к localhost:9187 напрямую
            self.container = self.client.containers.run(
                image=self.prometheus_settings["prometheus-settings"]["image"],
                name=self.container_name,
                network_mode='host',  # Использует сеть хоста напрямую
                volumes=volumes,
                detach=True,
                restart_policy={"Name": "unless-stopped"}
            )

            return True

        except Exception as e:
            print(f"Ошибка запуска: {e}")
            return False

    def stop(self) -> bool:
        """Останавливает и удаляет контейнер"""
        try:
            container = self.client.containers.get(self.container_name)
            container.stop()
            container.remove()
            return True
        except Exception as e:
            print(f"Ошибка при остановке: {e}")
            return False

    def status(self) -> dict:
        """Проверяет статус контейнера"""
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
        Извлекает все переменные из YAML файла с настройками Prometheus
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
        Обновляет YAML файл с настройками Prometheus
        """
        if file_path is None:
            file_path = os.path.join(os.path.dirname(__file__), 'prometheus_settings.yml')
        with open(file_path, 'w', encoding='utf-8') as file:
            yaml.dump(settings, file)
        return True
