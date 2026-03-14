import logging
from typing import Any, Dict, List, Optional

import docker

from app.services.minio import MinioService

logger = logging.getLogger(__name__)


class MainPrometheusConfig:
    """
    Класс для управления главным конфигом Prometheus.

    Предоставляет методы для добавления, удаления сервисов
    и получения полной конфигурации Prometheus.
    """

    def __init__(self):
        """
        Инициализация класса MainPrometheusConfig.
        """
        self.bucket = 'prometheus'
        self.minio_client = MinioService()

    def _get_exporter_host_port(self) -> Optional[str]:
        """
        Получает внешний порт экспортера на хосте.
        Убирает выбор порта - всегда использует первый найденный внешний порт экспортера.

        Returns:
            Optional[str]: Внешний порт на хосте или None, если не найден
        """
        try:
            docker_client = docker.from_env()
            for container in docker_client.containers.list(all=True):
                if 'exporter' in container.name.lower():
                    ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
                    for internal_port, port_bindings in ports.items():
                        if port_bindings and len(port_bindings) > 0:
                            host_port = port_bindings[0].get('HostPort')
                            if host_port:
                                return host_port
        except Exception as e:
            pass

    def _fix_target_port(self, target: List[Dict[str, Any]] | Dict[str, Any]) -> List[Dict[str, Any]] | Dict[str, Any]:
        """
        Исправляет порт в target на внешний порт хоста экспортера.
        Всегда использует внешний порт хоста вместо внутреннего порта контейнера.

        Args:
            target: Конфигурация target (может быть списком или словарем)

        Returns:
            Исправленная конфигурация target
        """
        if isinstance(target, dict):
            target = [target]
        
        host_port = self._get_exporter_host_port()
        if not host_port:
            return target if isinstance(target, list) else target[0] if target else {}
        
        for target_item in target:
            if isinstance(target_item, dict) and 'targets' in target_item:
                targets_list = target_item.get('targets', [])
                for i, target_address in enumerate(targets_list):
                    if isinstance(target_address, str) and ':' in target_address:
                        host_part = target_address.split(':')[0]
                        port_part = target_address.split(':')[-1]
                        new_target = f"{host_part}:{host_port}"
                        if target_address != new_target:
                            targets_list[i] = new_target
        
        return target if isinstance(target, list) else target[0] if target else {}

    def first_init(self):
        """
        Начальная инициализация конфига Prometheus.

        Создает базовую конфигурацию с пустым списком scrape_configs.
        """
        config = {
            'global': {
                'scrape_interval': '15s'
            },
            'scrape_configs': []
        }
        self.minio_client.upload_main(
            config,
            'mainConfig',
            'prometheus.yml'
        )

    def add_service(self, scrape_config: dict, target: list | dict, target_name: str) -> bool:
        """
        Добавляет сервис в конфиг Prometheus.

        Args:
            scrape_config: Конфигурация scrape для сервиса
            target: Конфигурация target для сервиса
            target_name: Имя файла target

        Returns:
            bool: True при успешном добавлении
        """
        main_config = self.minio_client.get_yaml_file('mainConfig/prometheus.yml')
        if main_config is None:
            self.first_init()
        if scrape_config.get('scrape_configs') and len(scrape_config['scrape_configs']) > 0:
            main_config['scrape_configs'].append(scrape_config['scrape_configs'][0])

        self.minio_client.upload_main(
            main_config,
            'mainConfig',
            'prometheus.yml'
        )

        self.minio_client.upload_main(
            target,
            'mainConfig/targets',
            target_name
        )

        return True

    def remove_service(self, job_name: str, target_name: str) -> bool:
        """
        Удаляет сервис из основного конфига Prometheus.

        Args:
            job_name: Имя job для удаления
            target_name: Имя файла target для удаления

        Returns:
            bool: True при успешном удалении
        """
        main_config = self.minio_client.get_yaml_file('mainConfig/prometheus.yml')

        if main_config is None:
            return False

        if 'scrape_configs' in main_config:
            main_config['scrape_configs'] = [
                config for config in main_config['scrape_configs']
                if config.get('job_name') != job_name
            ]

        self.minio_client.upload_main(
            main_config,
            'mainConfig',
            'prometheus.yml'
        )

        target_path = f'mainConfig/targets/{target_name}'
        self.minio_client.delete_file(target_path)

        return True

    def get_full_config(self) -> dict:
        """
        Получает полный конфиг Prometheus и все файлы targets.

        Returns:
            dict: Словарь с main_config и targets
        """
        main_config = self.minio_client.get_yaml_file('mainConfig/prometheus.yml')

        if main_config is None:
            return {
                'main_config': None,
                'targets': {}
            }

        target_files = self.minio_client.list_files('mainConfig/targets/')

        targets = {}
        for file_path in target_files:
            file_name = file_path.split('/')[-1]
            target_content = self.minio_client.get_yaml_file(file_path)
            if target_content is not None:
                targets[file_name] = target_content

        return {
            'main_config': main_config,
            'targets': targets
        }
