import logging
import os
from typing import Any, Dict, List, Optional

import boto3
import yaml
from botocore.client import Config
from botocore.exceptions import ClientError
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class UpdateConfig:
    """
    Класс для обновления конфигурации Prometheus из MinIO.

    Предоставляет методы для загрузки основного конфига и файлов targets
    из MinIO и сохранения их в локальную директорию prometheus/.
    """

    def __init__(self):
        """
        Инициализация класса UpdateConfig.

        Загружает параметры подключения к MinIO из переменных окружения
        и определяет пути к директориям prometheus/.
        """
        load_dotenv()
        endpoint = os.getenv('MINIO_ENDPOINT')
        access_key = os.getenv('MINIO_USR')
        secret_key = os.getenv('MINIO_PWD')
        self.bucket_name = 'prometheus'

        self.s3_client = boto3.client(
            's3',
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version='s3v4'),
            region_name='us-east-1'
        )

        self.prometheus_dir = os.path.join(
            os.path.dirname(__file__),
            'prometheus'
        )
        self.targets_dir = os.path.join(self.prometheus_dir, 'targets')

    def _get_yaml_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Получает YAML файл из MinIO.

        Args:
            file_path: Путь к файлу в MinIO

        Returns:
            Optional[Dict[str, Any]]: Распарсенный YAML или None при ошибке
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_path)
            content = response['Body'].read().decode('utf-8')
            return yaml.safe_load(content)
        except Exception as e:
            logger.error(f"Ошибка при получении файла {file_path}: {e}")
            return None

    def _list_files(self, prefix: str) -> List[str]:
        """
        Получает список файлов из MinIO.

        Args:
            prefix: Префикс для фильтрации файлов

        Returns:
            List[str]: Список путей к файлам
        """
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
            if 'Contents' in response:
                return [obj['Key'] for obj in response['Contents']]
            return []
        except ClientError as e:
            logger.error(f"Ошибка при получении списка файлов: {e}")
            return []

    def _fix_target_for_host_network(self, target: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Исправляет адрес target для работы с network_mode: host.

        Заменяет IP хоста на localhost, так как Prometheus использует
        network_mode: host и может обращаться к хосту напрямую.

        Args:
            target: Список с конфигурацией target

        Returns:
            List[Dict[str, Any]]: Исправленная конфигурация target
        """
        if not target or not target[0].get('targets'):
            return target

        target_address = target[0]['targets'][0]
        host_part = target_address.split(':')[0]
        port_part = target_address.split(':')[-1] if ':' in target_address else '9187'

        if host_part.startswith('172.17.') or host_part == '127.0.0.1' or host_part == 'localhost':
            target[0]['targets'][0] = f"localhost:{port_part}"
            logger.info(
                f"Исправлен target адрес для host network: "
                f"{target_address} -> {target[0]['targets'][0]}"
            )

        return target

    def update(self) -> None:
        """
        Обновляет конфигурацию Prometheus из MinIO.

        Загружает основной конфиг и файлы targets из MinIO
        и сохраняет их в локальную директорию prometheus/.
        """
        main_config = self._get_yaml_file('mainConfig/prometheus.yml')
        if not main_config:
            logger.warning("Основной конфиг не найден в MinIO")
            return

        prometheus_yml_path = os.path.join(self.prometheus_dir, 'prometheus.yml')
        with open(prometheus_yml_path, 'w', encoding='utf-8') as f:
            yaml.dump(main_config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        target_files = self._list_files('mainConfig/targets/')

        os.makedirs(self.targets_dir, exist_ok=True)

        for file_path in target_files:
            target_content = self._get_yaml_file(file_path)
            if target_content:
                target_content = self._fix_target_for_host_network(target_content)
                file_name = file_path.split('/')[-1]
                target_path = os.path.join(self.targets_dir, file_name)
                with open(target_path, 'w', encoding='utf-8') as f:
                    yaml.dump(
                        target_content,
                        f,
                        allow_unicode=True,
                        default_flow_style=False,
                        sort_keys=False
                    )

        logger.info(f"Конфигурация обновлена: {len(target_files)} файлов targets")
