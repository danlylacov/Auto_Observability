import logging
import os
from typing import Any, Dict, List, Optional

import boto3
import yaml
from aiohttp import ClientError
from botocore.client import Config
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class MinioService:
    """
    Класс для работы с MinIO хранилищем.

    Предоставляет методы для загрузки, получения и удаления файлов из MinIO.
    """

    def __init__(self):
        """
        Инициализация сервиса MinIO.

        Загружает параметры подключения из переменных окружения
        и создает бакет, если его нет.
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
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except (Exception,):
            self.s3_client.create_bucket(Bucket=self.bucket_name)

    def upload_main(self, yml_file: dict, path: str, file_name: str) -> dict[str, str]:
        """
        Загружает YAML файл в MinIO.

        Args:
            yml_file: Словарь с данными для сериализации в YAML
            path: Путь в MinIO
            file_name: Имя файла

        Returns:
            dict[str, str]: Информация о загруженном файле
        """
        yaml_string = yaml.dump(yml_file, allow_unicode=True, default_flow_style=False, sort_keys=False)
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=f'{path}/{file_name}',
            Body=yaml_string.encode('utf-8'),
            ContentType='application/x-yaml',
            Metadata={
                'format': 'yaml',
                'version': '1.0',
                'generated-by': 'prometheus-generation',
                'schema-version': '1.0'
            }
        )

        return {
            'file': f'configs/{file_name}',
            'bucket': self.bucket_name
        }

    def upload_config(self, scrape_config: dict, target: dict, container_id: str) -> dict[str, str]:
        """
        Загружает конфигурацию Prometheus для сервиса в MinIO.

        Загружает scrape_config.yml и файл targets для контейнера.

        Args:
            scrape_config: Конфигурация scrape для Prometheus
            target: Конфигурация target
            container_id: Идентификатор контейнера

        Returns:
            dict[str, str]: Информация о загруженных файлах
        """
        prometheus_config = {
            'scrape_configs': [scrape_config]
        }

        target_array = [target]

        logger.debug(f"Uploading scrape_config: {scrape_config}")

        scrape_config_yaml = yaml.dump(
            prometheus_config,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False
        )
        target_yaml = yaml.dump(target_array, allow_unicode=True, default_flow_style=False, sort_keys=False)

        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=f'configs/{container_id}/scrape_config.yml',
            Body=scrape_config_yaml.encode('utf-8'),
            ContentType='application/x-yaml',
            Metadata={
                'format': 'yaml',
                'version': '1.0',
                'generated-by': 'prometheus-generation',
                'schema-version': '1.0'
            }
        )

        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=f'configs/{container_id}/{scrape_config["job_name"]}.yml',
            Body=target_yaml.encode('utf-8'),
            ContentType='application/x-yaml',
            Metadata={
                'format': 'yaml',
                'version': '1.0',
                'generated-by': 'prometheus-generation',
                'schema-version': '1.0'
            }
        )

        return {
            'file': f'configs/{container_id}',
            'bucket': self.bucket_name
        }

    def _get_file(self, file_path: str, bucket: Optional[str] = None) -> Optional[str]:
        """
        Получает файл из MinIO и возвращает его содержимое как строку.

        Args:
            file_path: Путь к файлу в MinIO
            bucket: Имя бакета. Если None, используется bucket_name по умолчанию.

        Returns:
            Optional[str]: Содержимое файла или None при ошибке
        """
        bucket = bucket or self.bucket_name
        response = self.s3_client.get_object(Bucket=bucket, Key=file_path)
        content = response['Body'].read().decode('utf-8')
        return content

    def get_yaml_file(self, file_path: str, bucket: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Получает YAML файл из MinIO и возвращает его как словарь.

        Args:
            file_path: Путь к файлу в MinIO
            bucket: Имя бакета. Если None, используется bucket_name по умолчанию.

        Returns:
            Optional[Dict[str, Any]]: Распарсенный YAML или None при ошибке
        """
        content = self._get_file(file_path, bucket)
        if content is None:
            return None
        try:
            return yaml.safe_load(content)
        except yaml.YAMLError:
            return None

    def list_files(self, prefix: str = "", bucket: Optional[str] = None) -> List:
        """
        Выводит список файлов в бакете с заданным префиксом.

        Args:
            prefix: Префикс для фильтрации файлов
            bucket: Имя бакета. Если None, используется bucket_name по умолчанию.

        Returns:
            List: Список путей к файлам
        """
        bucket = bucket or self.bucket_name
        result = []
        try:
            response = self.s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
            if 'Contents' in response:
                for obj in response['Contents']:
                    result.append(obj['Key'])
            return result
        except ClientError as e:
            logger.error(f"Ошибка при получении списка файлов: {e}")
            return []

    def delete_file(self, file_path: str, bucket: Optional[str] = None) -> bool:
        """
        Удаляет файл из MinIO.

        Args:
            file_path: Путь к файлу в MinIO
            bucket: Имя бакета. Если None, используется bucket_name по умолчанию.

        Returns:
            bool: True если файл удален успешно, False при ошибке
        """
        bucket = bucket or self.bucket_name
        try:
            self.s3_client.delete_object(Bucket=bucket, Key=file_path)
            return True
        except Exception as e:
            logger.error(f"Ошибка при удалении файла {file_path}: {e}")
            return False

