import os
import yaml
import boto3
from botocore.exceptions import ClientError
from botocore.client import Config
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List


class MinioService:
    def __init__(self):

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
        Получает файл из MinIO и возвращает его содержимое как строку
        """
        bucket = bucket or self.bucket_name
        response = self.s3_client.get_object(Bucket=bucket, Key=file_path)
        content = response['Body'].read().decode('utf-8')
        return content


    def _get_yaml_file(self, file_path: str, bucket: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Получает YAML файл из MinIO и возвращает его как словарь
        """
        content = self._get_file(file_path, bucket)
        if content is None:
            return None
        try:
            return yaml.safe_load(content)
        except yaml.YAMLError:
            return None

    def _list_files(self, prefix: str = "", bucket: Optional[str] = None) -> List:
        """Выводит список файлов в бакете с заданным префиксом"""
        bucket = bucket or self.bucket_name
        result = []
        try:
            response = self.s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
            if 'Contents' in response:
                for obj in response['Contents']:
                    result.append(obj['Key'])
            return result
        except ClientError as e:
            print(f"Ошибка при получении списка файлов: {e}")
            return []

    def get_yml_files(self, conf_path: str = "", bucket: Optional[str] = None) -> Dict:
        bucket = bucket or self.bucket_name
        files_paths = self._list_files(prefix=conf_path, bucket=bucket)
        result = {}
        for file_path in files_paths:
            content = self._get_yaml_file(file_path, bucket)
            result[file_path.split('/')[-1]] = content
        return result
