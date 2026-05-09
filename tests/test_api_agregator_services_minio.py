"""Тесты для MinioService."""

import sys
from unittest.mock import MagicMock, patch, mock_open
import yaml

# Настраиваем алиас 'app' для api_agregator перед импортами
import api_agregator.app as api_app_module
sys.modules["app"] = api_app_module

# Импортируем через полный путь
from api_agregator.app.services.minio_service import MinioService


class TestMinioService:
    """Тесты для MinioService."""

    @patch('boto3.client')
    @patch('api_agregator.app.services.minio_service.os.getenv')
    def test_init(self, mock_getenv, mock_boto3_client):
        """Тест инициализации MinioService."""
        mock_getenv.side_effect = lambda key: {
            'MINIO_ENDPOINT': 'http://localhost:9000',
            'MINIO_USR': 'user',
            'MINIO_PWD': 'password'
        }.get(key)
        
        mock_s3_client = MagicMock()
        mock_boto3_client.return_value = mock_s3_client
        
        service = MinioService()
        
        assert service.bucket_name == 'prometheus'
        assert service.s3_client == mock_s3_client

    @patch('boto3.client')
    @patch('api_agregator.app.services.minio_service.os.getenv')
    def test_get_file_success(self, mock_getenv, mock_boto3_client):
        """Тест успешного получения файла."""
        mock_getenv.side_effect = lambda key: {
            'MINIO_ENDPOINT': 'http://localhost:9000',
            'MINIO_USR': 'user',
            'MINIO_PWD': 'password'
        }.get(key)
        
        mock_s3_client = MagicMock()
        mock_response = MagicMock()
        mock_response['Body'].read.return_value = b"file content"
        mock_s3_client.get_object.return_value = mock_response
        mock_boto3_client.return_value = mock_s3_client
        
        service = MinioService()
        result = service._get_file("test/file.txt")
        
        assert result == "file content"
        mock_s3_client.get_object.assert_called_once()

    @patch('boto3.client')
    @patch('api_agregator.app.services.minio_service.os.getenv')
    def test_get_yaml_file_success(self, mock_getenv, mock_boto3_client):
        """Тест успешного получения YAML файла."""
        mock_getenv.side_effect = lambda key: {
            'MINIO_ENDPOINT': 'http://localhost:9000',
            'MINIO_USR': 'user',
            'MINIO_PWD': 'password'
        }.get(key)
        
        mock_s3_client = MagicMock()
        mock_response = MagicMock()
        mock_response['Body'].read.return_value = b"key: value"
        mock_s3_client.get_object.return_value = mock_response
        mock_boto3_client.return_value = mock_s3_client
        
        service = MinioService()
        result = service._get_yaml_file("test/config.yml")
        
        assert result == {"key": "value"}

    @patch('boto3.client')
    @patch('api_agregator.app.services.minio_service.os.getenv')
    def test_list_files_success(self, mock_getenv, mock_boto3_client):
        """Тест успешного получения списка файлов."""
        mock_getenv.side_effect = lambda key: {
            'MINIO_ENDPOINT': 'http://localhost:9000',
            'MINIO_USR': 'user',
            'MINIO_PWD': 'password'
        }.get(key)
        
        mock_s3_client = MagicMock()
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [
                {'Key': 'path/to/file1.yml'},
                {'Key': 'path/to/file2.yml'}
            ]
        }
        mock_boto3_client.return_value = mock_s3_client
        
        service = MinioService()
        result = service._list_files("path/to/")
        
        assert len(result) == 2
        assert 'path/to/file1.yml' in result

    @patch('boto3.client')
    @patch('api_agregator.app.services.minio_service.os.getenv')
    def test_list_files_empty(self, mock_getenv, mock_boto3_client):
        """Тест получения пустого списка файлов."""
        mock_getenv.side_effect = lambda key: {
            'MINIO_ENDPOINT': 'http://localhost:9000',
            'MINIO_USR': 'user',
            'MINIO_PWD': 'password'
        }.get(key)
        
        mock_s3_client = MagicMock()
        mock_s3_client.list_objects_v2.return_value = {}
        mock_boto3_client.return_value = mock_s3_client
        
        service = MinioService()
        result = service._list_files("nonexistent/")
        
        assert result == []

    @patch('boto3.client')
    @patch('api_agregator.app.services.minio_service.os.getenv')
    def test_get_yml_files_success(self, mock_getenv, mock_boto3_client):
        """Тест успешного получения YAML файлов."""
        mock_getenv.side_effect = lambda key: {
            'MINIO_ENDPOINT': 'http://localhost:9000',
            'MINIO_USR': 'user',
            'MINIO_PWD': 'password'
        }.get(key)
        
        mock_s3_client = MagicMock()
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [
                {'Key': 'path/to/file1.yml'},
                {'Key': 'path/to/file2.yml'}
            ]
        }
        mock_response = MagicMock()
        mock_response['Body'].read.return_value = b"key: value"
        mock_s3_client.get_object.return_value = mock_response
        mock_boto3_client.return_value = mock_s3_client
        
        service = MinioService()
        result = service.get_yml_files("path/to/")
        
        assert len(result) == 2
        assert 'file1.yml' in result

    @patch('boto3.client')
    @patch('api_agregator.app.services.minio_service.os.getenv')
    def test_delete_file_success(self, mock_getenv, mock_boto3_client):
        """Тест успешного удаления файла."""
        mock_getenv.side_effect = lambda key: {
            'MINIO_ENDPOINT': 'http://localhost:9000',
            'MINIO_USR': 'user',
            'MINIO_PWD': 'password'
        }.get(key)
        
        mock_s3_client = MagicMock()
        mock_boto3_client.return_value = mock_s3_client
        
        service = MinioService()
        result = service.delete_file("test/file.txt")
        
        assert result is True
        mock_s3_client.delete_object.assert_called_once()

    @patch('boto3.client')
    @patch('api_agregator.app.services.minio_service.os.getenv')
    def test_delete_files_by_prefix_success(self, mock_getenv, mock_boto3_client):
        """Тест успешного удаления файлов по префиксу."""
        mock_getenv.side_effect = lambda key: {
            'MINIO_ENDPOINT': 'http://localhost:9000',
            'MINIO_USR': 'user',
            'MINIO_PWD': 'password'
        }.get(key)
        
        mock_s3_client = MagicMock()
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [
                {'Key': 'prefix/file1.txt'},
                {'Key': 'prefix/file2.txt'}
            ]
        }
        mock_boto3_client.return_value = mock_s3_client
        
        service = MinioService()
        result = service.delete_files_by_prefix("prefix/")
        
        assert result == 2
        assert mock_s3_client.delete_object.call_count == 2

    @patch('boto3.client')
    @patch('api_agregator.app.services.minio_service.os.getenv')
    def test_get_yaml_file_none_content(self, mock_getenv, mock_boto3_client):
        """Тест получения YAML файла когда контент None."""
        mock_getenv.side_effect = lambda key: {
            'MINIO_ENDPOINT': 'http://localhost:9000',
            'MINIO_USR': 'user',
            'MINIO_PWD': 'password'
        }.get(key)
        
        mock_s3_client = MagicMock()
        mock_boto3_client.return_value = mock_s3_client
        
        service = MinioService()
        with patch.object(service, '_get_file', return_value=None):
            result = service._get_yaml_file("test/config.yml")
            assert result is None

