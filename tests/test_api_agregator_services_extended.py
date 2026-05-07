"""Расширенные тесты для сервисов API Aggregator."""

import sys
from unittest.mock import MagicMock, Mock, patch, PropertyMock

import pytest

# Настраиваем алиас 'app' для api_agregator перед импортами
import api_agregator.app as api_app_module
sys.modules["app"] = api_app_module

from api_agregator.app.services.minio_service import MinioService
from api_agregator.app.services.update_containers import UpdateContainers


class TestMinioService:
    """Тесты для MinioService."""

    @patch('api_agregator.app.services.minio_service.boto3')
    @patch('api_agregator.app.services.minio_service.os.getenv')
    def test_init(self, mock_getenv, mock_boto3):
        """Тест инициализации MinioService."""
        mock_getenv.side_effect = lambda key: {
            'MINIO_ENDPOINT': 'http://localhost:9000',
            'MINIO_USR': 'minioadmin',
            'MINIO_PWD': 'minioadmin'
        }.get(key)
        
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client
        
        service = MinioService()
        
        assert service.bucket_name == 'prometheus'
        assert service.s3_client == mock_s3_client

    @patch('api_agregator.app.services.minio_service.boto3')
    @patch('api_agregator.app.services.minio_service.os.getenv')
    def test_get_file_success(self, mock_getenv, mock_boto3):
        """Тест успешного получения файла."""
        mock_getenv.side_effect = lambda key: {
            'MINIO_ENDPOINT': 'http://localhost:9000',
            'MINIO_USR': 'minioadmin',
            'MINIO_PWD': 'minioadmin'
        }.get(key)
        
        mock_s3_client = MagicMock()
        mock_response = {'Body': MagicMock()}
        mock_response['Body'].read.return_value = b'test content'
        mock_s3_client.get_object.return_value = mock_response
        mock_boto3.client.return_value = mock_s3_client
        
        service = MinioService()
        result = service._get_file('test/path/file.yml')
        
        assert result == 'test content'
        mock_s3_client.get_object.assert_called_once()

    @patch('api_agregator.app.services.minio_service.boto3')
    @patch('api_agregator.app.services.minio_service.os.getenv')
    def test_get_yaml_file_success(self, mock_getenv, mock_boto3):
        """Тест успешного получения YAML файла."""
        mock_getenv.side_effect = lambda key: {
            'MINIO_ENDPOINT': 'http://localhost:9000',
            'MINIO_USR': 'minioadmin',
            'MINIO_PWD': 'minioadmin'
        }.get(key)
        
        mock_s3_client = MagicMock()
        mock_response = {'Body': MagicMock()}
        mock_response['Body'].read.return_value = b'key: value'
        mock_s3_client.get_object.return_value = mock_response
        mock_boto3.client.return_value = mock_s3_client
        
        service = MinioService()
        result = service._get_yaml_file('test/path/file.yml')
        
        assert result == {'key': 'value'}

    @patch('api_agregator.app.services.minio_service.boto3')
    @patch('api_agregator.app.services.minio_service.os.getenv')
    def test_list_files_success(self, mock_getenv, mock_boto3):
        """Тест успешного получения списка файлов."""
        mock_getenv.side_effect = lambda key: {
            'MINIO_ENDPOINT': 'http://localhost:9000',
            'MINIO_USR': 'minioadmin',
            'MINIO_PWD': 'minioadmin'
        }.get(key)
        
        mock_s3_client = MagicMock()
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [
                {'Key': 'test/file1.yml'},
                {'Key': 'test/file2.yml'}
            ]
        }
        mock_boto3.client.return_value = mock_s3_client
        
        service = MinioService()
        result = service._list_files('test/')
        
        assert len(result) == 2
        assert 'test/file1.yml' in result

    @patch('api_agregator.app.services.minio_service.boto3')
    @patch('api_agregator.app.services.minio_service.os.getenv')
    def test_get_yml_files(self, mock_getenv, mock_boto3):
        """Тест получения всех YAML файлов."""
        mock_getenv.side_effect = lambda key: {
            'MINIO_ENDPOINT': 'http://localhost:9000',
            'MINIO_USR': 'minioadmin',
            'MINIO_PWD': 'minioadmin'
        }.get(key)
        
        mock_s3_client = MagicMock()
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [{'Key': 'test/file1.yml'}]
        }
        mock_response = {'Body': MagicMock()}
        mock_response['Body'].read.return_value = b'key: value'
        mock_s3_client.get_object.return_value = mock_response
        mock_boto3.client.return_value = mock_s3_client
        
        service = MinioService()
        result = service.get_yml_files('test/')
        
        assert 'file1.yml' in result
        assert result['file1.yml'] == {'key': 'value'}

    @patch('api_agregator.app.services.minio_service.boto3')
    @patch('api_agregator.app.services.minio_service.os.getenv')
    def test_delete_file_success(self, mock_getenv, mock_boto3):
        """Тест успешного удаления файла."""
        mock_getenv.side_effect = lambda key: {
            'MINIO_ENDPOINT': 'http://localhost:9000',
            'MINIO_USR': 'minioadmin',
            'MINIO_PWD': 'minioadmin'
        }.get(key)
        
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client
        
        service = MinioService()
        result = service.delete_file('test/file.yml')
        
        assert result is True
        mock_s3_client.delete_object.assert_called_once()

    @patch('api_agregator.app.services.minio_service.boto3')
    @patch('api_agregator.app.services.minio_service.os.getenv')
    def test_delete_files_by_prefix(self, mock_getenv, mock_boto3):
        """Тест удаления файлов по префиксу."""
        mock_getenv.side_effect = lambda key: {
            'MINIO_ENDPOINT': 'http://localhost:9000',
            'MINIO_USR': 'minioadmin',
            'MINIO_PWD': 'minioadmin'
        }.get(key)
        
        mock_s3_client = MagicMock()
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [
                {'Key': 'test/file1.yml'},
                {'Key': 'test/file2.yml'}
            ]
        }
        mock_boto3.client.return_value = mock_s3_client
        
        service = MinioService()
        result = service.delete_files_by_prefix('test/')
        
        assert result == 2
        assert mock_s3_client.delete_object.call_count == 2


class TestUpdateContainers:
    """Тесты для UpdateContainers."""

    @patch('api_agregator.app.services.update_containers.os.getenv')
    def test_init(self, mock_getenv):
        """Тест инициализации UpdateContainers."""
        mock_getenv.return_value = "http://classification:8000"
        
        service = UpdateContainers(db=None)
        
        assert service._external_db is None
        assert service._classification_gateway is not None

    @patch('api_agregator.app.services.update_containers.get_db')
    @patch('api_agregator.app.services.update_containers.APIGateway')
    @patch('api_agregator.app.services.update_containers.HostsService')
    @patch('api_agregator.app.services.update_containers.DockerContainers')
    @patch('api_agregator.app.services.update_containers.os.getenv')
    @patch('api_agregator.app.services.update_containers.os.path.exists')
    def test_upload_containers_no_hosts(self, mock_exists, mock_getenv, mock_docker_containers_class,
                                       mock_hosts_service_class, mock_api_gateway_class, mock_get_db):
        """Тест загрузки контейнеров при отсутствии хостов."""
        mock_getenv.return_value = "http://classification:8000"
        mock_exists.return_value = False
        
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        
        mock_hosts_service = MagicMock()
        mock_hosts_service.get_all_hosts.return_value = {}
        mock_hosts_service_class.return_value = mock_hosts_service
        
        mock_docker_containers = MagicMock()
        mock_client = MagicMock()
        mock_client.pipeline.return_value = MagicMock()
        mock_client.keys.return_value = []
        mock_docker_containers.client = mock_client
        mock_docker_containers_class.return_value = mock_docker_containers
        
        service = UpdateContainers(db=mock_db)
        service.upload_containers()
        
        # Не должно быть ошибок при отсутствии хостов

    @patch('api_agregator.app.services.update_containers.get_db')
    @patch('api_agregator.app.services.update_containers.APIGateway')
    @patch('api_agregator.app.services.update_containers.HostsService')
    @patch('api_agregator.app.services.update_containers.DockerContainers')
    @patch('api_agregator.app.services.update_containers.os.getenv')
    @patch('api_agregator.app.services.update_containers.os.path.exists')
    def test_upload_containers_with_hosts(self, mock_exists, mock_getenv, mock_docker_containers_class,
                                         mock_hosts_service_class, mock_api_gateway_class, mock_get_db):
        """Тест загрузки контейнеров с хостами."""
        mock_getenv.return_value = "http://classification:8000"
        mock_exists.return_value = False
        
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        
        mock_hosts_service = MagicMock()
        mock_hosts_service.get_all_hosts.return_value = {
            "host1": {"host": "localhost", "port": 8000, "name": "Test Host"}
        }
        mock_hosts_service_class.return_value = mock_hosts_service
        
        mock_gateway = MagicMock()
        mock_gateway.make_request.return_value = {
            "containers": [
                {"Id": "container1", "Name": "test-container"}
            ]
        }
        mock_api_gateway_class.return_value = mock_gateway
        
        mock_docker_containers = MagicMock()
        mock_pipeline = MagicMock()
        mock_pipeline.execute.return_value = None
        mock_client = MagicMock()
        mock_client.pipeline.return_value = mock_pipeline
        mock_client.keys.return_value = []
        mock_client.delete.return_value = 0
        mock_docker_containers.client = mock_client
        mock_docker_containers_class.return_value = mock_docker_containers
        
        service = UpdateContainers(db=mock_db)
        service._classification_gateway = None  # Упрощаем тест
        service.upload_containers()
        
        mock_gateway.make_request.assert_called()

    @patch('api_agregator.app.services.update_containers.APIGateway')
    def test_classificate_container(self, mock_api_gateway_class):
        """Тест классификации контейнера."""
        mock_gateway = MagicMock()
        mock_gateway.make_request.return_value = {"result": [["postgresql", 100]]}
        mock_api_gateway_class.return_value = mock_gateway
        
        service = UpdateContainers(db=None)
        service._classification_gateway = mock_gateway
        
        container = {
            "Config": {
                "Labels": {},
                "Env": [],
                "Image": "postgres:latest",
                "ExposedPorts": {"5432/tcp": {}}
            }
        }
        
        result = service._classificate_container(container, mock_gateway)
        
        assert "result" in result
        mock_gateway.make_request.assert_called_once()

