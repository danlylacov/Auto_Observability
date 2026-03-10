import os
import logging
from typing import Optional, Dict, Any, List

import boto3
import yaml
from botocore.client import Config
from botocore.exceptions import ClientError
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

        Загружает параметры подключения из переменных окружения.
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

    def _get_yaml_file(self, file_path: str, bucket: Optional[str] = None) -> Optional[Dict[str, Any]]:
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

    def _list_files(self, prefix: str = "", bucket: Optional[str] = None) -> List:
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

    def get_yml_files(self, conf_path: str = "", bucket: Optional[str] = None) -> Dict:
        """
        Получает все YAML файлы с заданным префиксом.

        Args:
            conf_path: Префикс пути к файлам
            bucket: Имя бакета. Если None, используется bucket_name по умолчанию.

        Returns:
            Dict: Словарь с именами файлов и их содержимым (filename -> parsed_yaml)
        """
        bucket = bucket or self.bucket_name
        files_paths = self._list_files(prefix=conf_path, bucket=bucket)
        result = {}
        for file_path in files_paths:
            content = self._get_yaml_file(file_path, bucket)
            result[file_path.split('/')[-1]] = content
        return result

    def delete_file(self, file_path: str, bucket: Optional[str] = None) -> bool:
        """
        Удаляет один файл из MinIO.

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
        except ClientError as e:
            logger.error(f"Ошибка при удалении файла {file_path}: {e}")
            return False

    def delete_files_by_prefix(self, prefix: str, bucket: Optional[str] = None) -> int:
        """
        Удаляет все файлы с заданным префиксом из MinIO.

        Args:
            prefix: Префикс для фильтрации файлов
            bucket: Имя бакета. Если None, используется bucket_name по умолчанию.

        Returns:
            int: Количество удаленных файлов
        """
        bucket = bucket or self.bucket_name
        try:
            files_to_delete = self._list_files(prefix=prefix, bucket=bucket)

            if not files_to_delete:
                return 0

            deleted_count = 0
            for file_path in files_to_delete:
                try:
                    self.s3_client.delete_object(Bucket=bucket, Key=file_path)
                    deleted_count += 1
                except ClientError as e:
                    logger.error(f"Ошибка при удалении файла {file_path}: {e}")

            return deleted_count
        except Exception as e:
            logger.error(f"Ошибка при удалении файлов с префиксом {prefix}: {e}")
            return 0
