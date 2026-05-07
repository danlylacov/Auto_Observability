"""Тесты для Redis классов API Aggregator."""

import sys
from unittest.mock import MagicMock, patch
import json

# Настраиваем алиас 'app' для api_agregator перед импортами
import api_agregator.app as api_app_module
sys.modules["app"] = api_app_module

from api_agregator.app.db.redis.docker_containers import DockerContainers
from api_agregator.app.db.redis.hosts import Hosts


class TestDockerContainers:
    """Тесты для DockerContainers."""

    @patch('api_agregator.app.db.redis.redis_connection.RedisConnection.connect')
    def test_init(self, mock_connect):
        """Тест инициализации DockerContainers."""
        mock_redis_client = MagicMock()
        mock_connect.return_value = mock_redis_client
        
        containers = DockerContainers()
        
        assert containers.client == mock_redis_client

    @patch('api_agregator.app.db.redis.redis_connection.RedisConnection.connect')
    def test_upload_containers(self, mock_connect):
        """Тест загрузки контейнеров."""
        mock_redis_client = MagicMock()
        mock_pipeline = MagicMock()
        mock_redis_client.pipeline.return_value = mock_pipeline
        mock_connect.return_value = mock_redis_client
        
        containers = DockerContainers()
        containers_data = {
            "container1": {"info": {"Id": "c1"}},
            "container2": {"info": {"Id": "c2"}}
        }
        
        containers.upload_containers(containers_data, "host1")
        
        assert mock_pipeline.set.call_count == 2
        mock_pipeline.execute.assert_called_once()

    @patch('api_agregator.app.db.redis.redis_connection.RedisConnection.connect')
    def test_upload_container(self, mock_connect):
        """Тест загрузки одного контейнера."""
        mock_redis_client = MagicMock()
        mock_connect.return_value = mock_redis_client
        
        containers = DockerContainers()
        container_data = {"info": {"Id": "c1"}}
        
        containers.upload_container("container1", container_data, "host1")
        
        mock_redis_client.set.assert_called_once()
        call_args = mock_redis_client.set.call_args
        assert "container:host1:container1" in call_args[0][0]

    @patch('api_agregator.app.db.redis.redis_connection.RedisConnection.connect')
    def test_get_containers(self, mock_connect):
        """Тест получения контейнеров."""
        mock_redis_client = MagicMock()
        mock_pipeline = MagicMock()
        mock_redis_client.pipeline.return_value = mock_pipeline
        mock_redis_client.keys.return_value = [b"container:host1:c1", b"container:host1:c2"]
        mock_pipeline.execute.return_value = [
            json.dumps({"info": {"Id": "c1"}}).encode(),
            json.dumps({"info": {"Id": "c2"}}).encode()
        ]
        mock_connect.return_value = mock_redis_client
        
        containers = DockerContainers()
        result = containers.get_containers("host1")
        
        assert len(result) == 2
        assert "c1" in result
        assert "c2" in result

    @patch('api_agregator.app.db.redis.redis_connection.RedisConnection.connect')
    def test_get_container(self, mock_connect):
        """Тест получения одного контейнера."""
        mock_redis_client = MagicMock()
        mock_redis_client.get.return_value = json.dumps({"info": {"Id": "c1"}}).encode()
        mock_connect.return_value = mock_redis_client
        
        containers = DockerContainers()
        result = containers.get_container("c1", "host1")
        
        assert result["info"]["Id"] == "c1"

    @patch('api_agregator.app.db.redis.redis_connection.RedisConnection.connect')
    def test_delete_all_containers_by_host(self, mock_connect):
        """Тест удаления всех контейнеров хоста."""
        mock_redis_client = MagicMock()
        mock_redis_client.keys.return_value = [b"container:host1:c1", b"container:host1:c2"]
        mock_redis_client.delete.return_value = 2
        mock_connect.return_value = mock_redis_client
        
        containers = DockerContainers()
        result = containers.delete_all_containers_by_host("host1")
        
        assert result == 2
        # delete вызывается один раз с несколькими ключами
        assert mock_redis_client.delete.call_count == 1


class TestHosts:
    """Тесты для Hosts."""

    @patch('api_agregator.app.db.redis.hosts.RedisConnection.connect')
    def test_init(self, mock_connect):
        """Тест инициализации Hosts."""
        mock_redis_client = MagicMock()
        mock_connect.return_value = mock_redis_client
        
        hosts = Hosts()
        
        assert hosts.client == mock_redis_client

    @patch('api_agregator.app.db.redis.hosts.RedisConnection.connect')
    def test_upload_hosts(self, mock_connect):
        """Тест загрузки хостов."""
        mock_redis_client = MagicMock()
        mock_pipeline = MagicMock()
        mock_redis_client.pipeline.return_value = mock_pipeline
        mock_connect.return_value = mock_redis_client
        
        hosts = Hosts()
        hosts_data = {
            "host1": {"name": "Host1", "host": "localhost", "port": 8000},
            "host2": {"name": "Host2", "host": "192.168.1.1", "port": 8000}
        }
        
        hosts.upload_hosts(hosts_data)
        
        # Проверяем что pipeline.set был вызван для каждого хоста
        assert mock_pipeline.set.call_count == 2
        mock_pipeline.execute.assert_called_once()

    @patch('api_agregator.app.db.redis.redis_connection.RedisConnection.connect')
    def test_get_hosts(self, mock_connect):
        """Тест получения хостов."""
        mock_redis_client = MagicMock()
        mock_pipeline = MagicMock()
        mock_redis_client.pipeline.return_value = mock_pipeline
        
        # Настраиваем keys для возврата списка ключей
        mock_redis_client.keys.return_value = [b"host:host1", b"host:host2"]
        # Настраиваем pipeline.execute для возврата значений
        mock_pipeline.execute.return_value = [
            json.dumps({"name": "Host1"}).encode(),
            json.dumps({"name": "Host2"}).encode()
        ]
        mock_connect.return_value = mock_redis_client
        
        hosts = Hosts()
        result = hosts.get_hosts()
        
        assert len(result) == 2
        assert "host1" in result
        assert "host2" in result

    @patch('api_agregator.app.db.redis.redis_connection.RedisConnection.connect')
    def test_delete_hosts(self, mock_connect):
        """Тест удаления хостов."""
        mock_redis_client = MagicMock()
        mock_connect.return_value = mock_redis_client
        
        hosts = Hosts()
        hosts.delete_hosts()
        
        mock_redis_client.delete.assert_called_once()

