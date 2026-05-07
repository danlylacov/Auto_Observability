"""Тесты для сервисов Docker API."""

import pytest
from unittest.mock import MagicMock, patch
import docker.errors

from docker_api.app.services.docker_manager import DockerManager


class TestDockerManagerServices:
    """Тесты для DockerManager services."""

    @patch('docker_api.app.services.docker_manager.docker')
    def test_init(self, mock_docker):
        """Тест инициализации DockerManager."""
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        
        manager = DockerManager()
        
        assert manager.client == mock_client

    @patch('docker_api.app.services.docker_manager.docker')
    def test_discover_containers(self, mock_docker):
        """Тест обнаружения контейнеров."""
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
        NotFound = type('NotFound', (Exception,), {})
        mock_docker.errors = MagicMock()
        mock_docker.errors.NotFound = NotFound
        
        mock_client = MagicMock()
        mock_client.containers.get.side_effect = NotFound("Not found")
        mock_docker.from_env.return_value = mock_client
        
        manager = DockerManager()
        result = manager.start_container("nonexistent")
        
        assert "не найден" in result

    @patch('docker_api.app.services.docker_manager.docker')
    def test_stop_container_success(self, mock_docker):
        """Тест успешной остановки контейнера."""
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_client.containers.get.return_value = mock_container
        mock_docker.from_env.return_value = mock_client
        
        manager = DockerManager()
        result = manager.stop_container("container1")
        
        assert "остановлен" in result
        mock_container.stop.assert_called_once()

    @patch('docker_api.app.services.docker_manager.docker')
    def test_remove_container_success(self, mock_docker):
        """Тест успешного удаления контейнера."""
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_client.containers.get.return_value = mock_container
        mock_docker.from_env.return_value = mock_client
        
        manager = DockerManager()
        result = manager.remove_container("container1", force=False)
        
        assert "удален" in result
        mock_container.remove.assert_called_once()

    @patch('docker_api.app.services.docker_manager.docker')
    def test_pull_and_run_container_local_image(self, mock_docker):
        """Тест запуска контейнера с локальным образом."""
        mock_client = MagicMock()
        mock_image = MagicMock()
        mock_client.images.get.return_value = mock_image
        
        mock_container = MagicMock()
        mock_container.short_id = "abc123"
        mock_client.containers.run.return_value = mock_container
        mock_docker.from_env.return_value = mock_client
        
        manager = DockerManager()
        result = manager.pull_and_run_container("nginx:latest")
        
        assert "container_id" in result
        assert result["pull_status"] == "использован локальный образ"

    @patch('docker_api.app.services.docker_manager.docker')
    def test_pull_and_run_container_pull_image(self, mock_docker):
        """Тест запуска контейнера с загрузкой образа."""
        NotFound = type('ImageNotFound', (Exception,), {})
        mock_docker.errors = MagicMock()
        mock_docker.errors.ImageNotFound = NotFound
        
        mock_client = MagicMock()
        mock_client.images.get.side_effect = NotFound("Not found")
        mock_client.images.pull.return_value = None
        
        mock_container = MagicMock()
        mock_container.short_id = "abc123"
        mock_client.containers.run.return_value = mock_container
        mock_docker.from_env.return_value = mock_client
        
        manager = DockerManager()
        result = manager.pull_and_run_container("nginx:latest")
        
        assert "container_id" in result
        assert result["pull_status"] == "образ успешно загружен"
        mock_client.images.pull.assert_called_once()

    @patch('docker_api.app.services.docker_manager.docker')
    def test_pull_and_run_container_existing_running(self, mock_docker):
        """Тест запуска уже запущенного контейнера."""
        NotFound = type('NotFound', (Exception,), {})
        mock_docker.errors = MagicMock()
        mock_docker.errors.NotFound = NotFound
        mock_docker.errors.ImageNotFound = NotFound
        
        mock_client = MagicMock()
        mock_client.images.get.return_value = MagicMock()
        
        mock_existing_container = MagicMock()
        mock_existing_container.status = "running"
        mock_existing_container.short_id = "existing123"
        mock_client.containers.get.return_value = mock_existing_container
        mock_docker.from_env.return_value = mock_client
        
        manager = DockerManager()
        result = manager.pull_and_run_container("nginx:latest", name="test-container")
        
        assert result["status"] == "Контейнер уже запущен"
        assert result["container_id"] == "existing123"

    @patch('docker_api.app.services.docker_manager.docker')
    def test_remove_volume_success(self, mock_docker):
        """Тест успешного удаления тома."""
        mock_client = MagicMock()
        mock_volume = MagicMock()
        mock_client.volumes.get.return_value = mock_volume
        mock_docker.from_env.return_value = mock_client
        
        manager = DockerManager()
        result = manager.remove_volume("test-volume", force=False)
        
        assert "удален" in result
        mock_volume.remove.assert_called_once()

    @patch('docker_api.app.services.docker_manager.docker')
    def test_prune_volumes_success(self, mock_docker):
        """Тест очистки неиспользуемых томов."""
        mock_client = MagicMock()
        mock_client.volumes.prune.return_value = {"VolumesDeleted": ["vol1"], "SpaceReclaimed": 100}
        mock_docker.from_env.return_value = mock_client
        
        manager = DockerManager()
        result = manager.prune_volumes()
        
        assert "VolumesDeleted" in result
        mock_client.volumes.prune.assert_called_once()

    @patch('docker_api.app.services.docker_manager.docker')
    def test_remove_image_success(self, mock_docker):
        """Тест успешного удаления образа."""
        mock_client = MagicMock()
        mock_client.images.remove.return_value = None
        mock_docker.from_env.return_value = mock_client
        
        manager = DockerManager()
        result = manager.remove_image("nginx:latest", force=False)
        
        assert "удален" in result
        mock_client.images.remove.assert_called_once_with(image="nginx:latest", force=False)

    @patch('docker_api.app.services.docker_manager.docker')
    def test_cleanup_system_success(self, mock_docker):
        """Тест очистки системы."""
        mock_client = MagicMock()
        mock_client.containers.prune.return_value = {"ContainersDeleted": ["c1"]}
        mock_client.images.prune.return_value = {"ImagesDeleted": ["i1"]}
        mock_client.networks.prune.return_value = {"NetworksDeleted": ["n1"]}
        mock_client.volumes.prune.return_value = {"VolumesDeleted": ["v1"]}
        mock_docker.from_env.return_value = mock_client
        
        manager = DockerManager()
        result = manager.cleanup_system()
        
        assert "containers" in result
        assert "images" in result
        assert "networks" in result
        assert "volumes" in result
        assert result["containers"]["ContainersDeleted"] == ["c1"]

