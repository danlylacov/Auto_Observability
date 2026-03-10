import os
import yaml
import boto3
from typing import Optional, Dict, Any, List
from botocore.client import Config
from botocore.exceptions import ClientError
from dotenv import load_dotenv


class UpdateConfig:
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

        self.prometheus_dir = os.path.join(
            os.path.dirname(__file__),
            'prometheus'
        )
        self.targets_dir = os.path.join(self.prometheus_dir, 'targets')

    def _get_yaml_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Получает YAML файл из MinIO"""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_path)
            content = response['Body'].read().decode('utf-8')
            return yaml.safe_load(content)
        except Exception as e:
            print(f"Ошибка при получении файла {file_path}: {e}")
            return None

    def _list_files(self, prefix: str) -> List[str]:
        """Получает список файлов из MinIO"""
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
            if 'Contents' in response:
                return [obj['Key'] for obj in response['Contents']]
            return []
        except ClientError as e:
            print(f"Ошибка при получении списка файлов: {e}")
            return []

    def _fix_target_for_host_network(self, target: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Исправляет адрес target для работы с network_mode: host.
        Заменяет IP хоста (172.17.0.1, 172.17.0.2 и т.д.) на localhost,
        так как Prometheus использует network_mode: host и может обращаться к хосту напрямую.
        """
        if not target or not target[0].get('targets'):
            return target
        
        target_address = target[0]['targets'][0]
        host_part = target_address.split(':')[0]
        port_part = target_address.split(':')[-1] if ':' in target_address else '9187'
        
        # Заменяем IP хоста Docker сети на localhost для network_mode: host
        if host_part.startswith('172.17.') or host_part == '127.0.0.1' or host_part == 'localhost':
            target[0]['targets'][0] = f"localhost:{port_part}"
            print(f"Исправлен target адрес для host network: {target_address} -> {target[0]['targets'][0]}")
        
        return target

    def update(self) -> None:
        """Обновляет конфигурацию Prometheus из MinIO"""
        main_config = self._get_yaml_file('mainConfig/prometheus.yml')
        if not main_config:
            print("Основной конфиг не найден в MinIO")
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
                    yaml.dump(target_content, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        print(f"Конфигурация обновлена: {len(target_files)} файлов targets")

a = UpdateConfig()
a.update()
