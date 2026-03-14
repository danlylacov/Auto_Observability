import os

import docker
import time
from typing import Optional

import yaml


class GrafanaManager:
    def __init__(self):
        self.client = docker.from_env()
        self.container: Optional[docker.models.containers.Container] = None

        grafana_settings = self.get_grafana_settings()
        self.image = grafana_settings['grafana-settings']['image']
        self.container_name = grafana_settings['grafana-settings']['name']
        self.port = grafana_settings['grafana-settings']['port']
        self.user = grafana_settings['grafana-settings']['usr']
        self.password = grafana_settings['grafana-settings']['pwd']

    def start_grafana(self) -> bool:
        """Запуск контейнера Grafana"""
        try:
            # Проверяем, существует ли уже контейнер с таким именем
            try:
                existing_container = self.client.containers.get(self.container_name)

                if existing_container.status == 'running':
                    self.container = existing_container
                    return True
                else:
                    existing_container.start()
                    self.container = existing_container
                    return True

            except docker.errors.NotFound:
                run_params = {
                    "image": self.image,
                    "name": self.container_name,
                    "ports": {'3000/tcp': self.port},
                    "environment": {
                        "GF_SECURITY_ADMIN_PASSWORD": self.password,
                        "GF_SECURITY_ADMIN_USER": self.user,
                    },
                    "detach": True,
                    "restart_policy": {"Name": "unless-stopped"}
                }

                self.container = self.client.containers.run(**run_params)
                print(f"Контейнер {self.container_name} успешно создан и запущен")
                return True

        except Exception as e:
            print(f"Ошибка при запуске: {e}")
            return False

    def stop_grafana(self, remove: bool = False) -> bool:
        """Остановка контейнера Grafana"""
        try:
            if not self.container:
                self.container = self.client.containers.get(self.container_name)

            if self.container.status == 'running':
                self.container.stop()

                if remove:
                    self.container.remove()
                return True
            else:
                return False
        except Exception as e:
            print(f"Ошибка при остановке: {e}")
            return False

    def restart_grafana(self) -> bool:
        """Перезапуск контейнера"""
        try:
            if not self.container:
                self.container = self.client.containers.get(self.container_name)

            self.container.restart()
            return True

        except Exception as e:
            print(f"Ошибка при перезапуске: {e}")
            return False

    def get_status(self) -> Optional[str]:
        """Получение статуса контейнера"""
        try:
            if not self.container:
                self.container = self.client.containers.get(self.container_name)

            self.container.reload()
            return self.container.status

        except Exception as e:
            print(f"Ошибка при получении статуса: {e}")
            return None

    def get_logs(self, tail: int = 100) -> str:
        """Получение логов контейнера"""
        try:
            if not self.container:
                self.container = self.client.containers.get(self.container_name)

            logs = self.container.logs(tail=tail).decode('utf-8')
            return logs

        except Exception as e:
            print(f"Ошибка при получении логов: {e}")
            return ""


    @staticmethod
    def get_grafana_settings(file_path: str = None) -> dict[str, dict[str, str]]:
        """
        Извлекает все переменные из YAML файла с настройками Grafana.

        Args:
            file_path: Путь к файлу настроек. Если None, используется файл в текущей директории.

        Returns:
            dict[str, dict[str, str]]: Настройки Grafana
        """
        if file_path is None:
            file_path = os.path.join(os.path.dirname(__file__), 'grafana_settings.yml')
        with open(file_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
        return data

    @staticmethod
    def update_grafana_settings(settings: dict[str, dict[str, str]],
                                   file_path: str = None):
        """
        Обновляет YAML файл с настройками grafana.

        Args:
            settings: Новые настройки grafana
            file_path: Путь к файлу настроек. Если None, используется файл в текущей директории.

        Returns:
            bool: True при успешном обновлении
        """
        if file_path is None:
            file_path = os.path.join(os.path.dirname(__file__), 'grafana_settings.yml')
        with open(file_path, 'w', encoding='utf-8') as file:
            yaml.dump(settings, file)
        return True
