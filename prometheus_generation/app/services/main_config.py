import logging

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
            logger.warning("Основной конфиг не найден")
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
        deleted = self.minio_client.delete_file(target_path)

        if not deleted:
            logger.warning(f"Не удалось удалить файл targets: {target_path}")

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
