import os

import boto3
import yaml
from botocore.client import Config
from dotenv import load_dotenv


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
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except (Exception,):
            self.s3_client.create_bucket(Bucket=self.bucket_name)

    def upload_yml(self, yml_file: str, file_name: str) -> dict[str, str]:
        yaml_string = yaml.dump(yml_file, allow_unicode=True, default_flow_style=False)
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=f'configs/{file_name}',
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


