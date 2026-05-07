"""Тесты для роутеров Docker API."""

import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from tests.conftest import import_service_app

docker_api_app = import_service_app("docker_api")


@pytest.fixture
def client():
    """Фикстура для тестового клиента FastAPI."""
    return TestClient(docker_api_app)


class TestDiscoverRouter:
    """Тесты для роутера discover."""

    @patch('docker_api.app.routers.discover.DockerManager')
    def test_get_containers_success(self, mock_docker_manager_class, client):
        """Тест успешного получения контейнеров."""
        mock_manager = MagicMock()
        mock_manager.client.ping.return_value = True
        mock_manager.discover_containers.return_value = [
            {"Id": "container1", "Name": "test-container"}
        ]
        mock_docker_manager_class.return_value = mock_manager

        response = client.post("/api/v1/discover/")
        
        assert response.status_code == 201
        assert "containers" in response.json()
        assert response.json()["count"] == 1

    @patch('docker_api.app.routers.discover.DockerManager')
    def test_get_containers_empty(self, mock_docker_manager_class, client):
        """Тест получения пустого списка контейнеров."""
        mock_manager = MagicMock()
        mock_manager.client.ping.return_value = True
        mock_manager.discover_containers.return_value = []
        mock_docker_manager_class.return_value = mock_manager

        response = client.post("/api/v1/discover/")
        
        assert response.status_code == 201
        assert response.json()["containers"] == []

    @patch('docker_api.app.routers.discover.DockerManager')
    def test_get_containers_docker_not_responding(self, mock_docker_manager_class, client):
        """Тест получения контейнеров при недоступности Docker."""
        mock_manager = MagicMock()
        mock_manager.client.ping.side_effect = Exception("Connection error")
        mock_docker_manager_class.return_value = mock_manager

        response = client.post("/api/v1/discover/")
        
        assert response.status_code == 503


class TestManageRouter:
    """Тесты для роутера manage."""

    @patch('docker_api.app.routers.manage.DockerManager')
    def test_stop_container_success(self, mock_docker_manager_class, client):
        """Тест успешной остановки контейнера."""
        mock_manager = MagicMock()
        mock_manager.stop_container.return_value = "Container stopped"
        mock_docker_manager_class.return_value = mock_manager

        response = client.post(
            "/api/v1/manage/container/stop",
            json={"id": "container1"}
        )
        
        assert response.status_code == 200
        assert "stopped successfully" in response.json()["message"]

    @patch('docker_api.app.routers.manage.DockerManager')
    def test_start_container_success(self, mock_docker_manager_class, client):
        """Тест успешного запуска контейнера."""
        mock_manager = MagicMock()
        mock_manager.start_container.return_value = "Container started"
        mock_docker_manager_class.return_value = mock_manager

        response = client.post(
            "/api/v1/manage/container/start",
            json={"id": "container1"}
        )
        
        assert response.status_code == 200
        assert "started successfully" in response.json()["message"]

    @patch('docker_api.app.routers.manage.DockerManager')
    def test_remove_container_success(self, mock_docker_manager_class, client):
        """Тест успешного удаления контейнера."""
        mock_manager = MagicMock()
        mock_manager.remove_container.return_value = "Container removed"
        mock_docker_manager_class.return_value = mock_manager

        response = client.delete(
            "/api/v1/manage/container/remove",
            params={"force": False},
            json={"id": "container1"}
        )
        
        assert response.status_code == 200
        assert "removed successfully" in response.json()["message"]

    @patch('docker_api.app.routers.manage.DockerManager')
    def test_run_container_success(self, mock_docker_manager_class, client):
        """Тест успешного запуска нового контейнера."""
        mock_manager = MagicMock()
        mock_manager.pull_and_run_container.return_value = {
            "container_id": "new_container",
            "pull_status": "success"
        }
        mock_docker_manager_class.return_value = mock_manager

        response = client.post(
            "/api/v1/manage/container/pull_and_run",
            json={
                "image_name": "nginx:latest",
                "name": "test-nginx",
                "detach": True
            }
        )
        
        assert response.status_code in [200, 201]
        result = response.json()
        assert "result" in result or "container_id" in result


class TestDockerManager:
    """Тесты для DockerManager."""

    @patch('docker_api.app.services.docker_manager.docker')
    def test_discover_containers(self, mock_docker):
        """Тест обнаружения контейнеров."""
        from docker_api.app.services.docker_manager import DockerManager
        
        mock_client = MagicMock()
        mock_container1 = MagicMock()
        mock_container1.attrs = {
            "Id": "container1", 
            "Name": "test-container",
            "Config": {"Labels": {}}
        }
        
        mock_container2 = MagicMock()
        mock_container2.attrs = {
            "Id": "container2",
            "Name": "/auto_observability_test",
            "Config": {"Labels": {"com.docker.compose.project": "auto_observability"}}
        }
        
        mock_client.containers.list.return_value = [mock_container1, mock_container2]
        mock_docker.from_env.return_value = mock_client
        
        manager = DockerManager()
        result = manager.discover_containers()
        
        assert len(result) == 1
        assert result[0]["Id"] == "container1"

    @patch('docker_api.app.services.docker_manager.docker')
    def test_start_container_success(self, mock_docker):
        """Тест успешного запуска контейнера."""
        from docker_api.app.services.docker_manager import DockerManager
        
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_client.containers.get.return_value = mock_container
        mock_docker.from_env.return_value = mock_client
        
        manager = DockerManager()
        result = manager.start_container("container1")
        
        assert "запущен" in result
        mock_container.start.assert_called_once()

    @patch('docker_api.app.services.docker_manager.docker')
    def test_start_container_not_found(self, mock_docker):
        """Тест запуска несуществующего контейнера."""
        from docker_api.app.services.docker_manager import DockerManager
        
        # Создаем класс исключения NotFound
        NotFound = type('NotFound', (Exception,), {})
        mock_docker.errors = MagicMock()
        mock_docker.errors.NotFound = NotFound
        
        mock_client = MagicMock()
        mock_client.containers.get.side_effect = NotFound("Container not found")
        mock_docker.from_env.return_value = mock_client
        
        manager = DockerManager()
        result = manager.start_container("nonexistent")
        
        assert "не найден" in result or "Ошибка" in result

