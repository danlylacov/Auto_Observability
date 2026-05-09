"""Тесты для сервисов Grafana Manager."""

import pytest
from unittest.mock import MagicMock, patch, mock_open
import docker.errors

from grafana_manager.app.services.grafana_manager import GrafanaManager


class TestGrafanaManager:
    """Тесты для GrafanaManager."""

    @patch('grafana_manager.app.services.grafana_manager.docker')
    @patch('grafana_manager.app.services.grafana_manager.GrafanaManager.get_grafana_settings')
    def test_init(self, mock_get_settings, mock_docker):
        """Тест инициализации GrafanaManager."""
        mock_get_settings.return_value = {
            "grafana-settings": {
                "name": "test-grafana",
                "image": "grafana/grafana",
                "port": 3000,
                "usr": "admin",
                "pwd": "admin"
            }
        }
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        
        manager = GrafanaManager()
        
        assert manager.client == mock_client
        assert manager.container_name == "test-grafana"
        assert manager.image == "grafana/grafana"
        assert manager.port == 3000

    @patch('grafana_manager.app.services.grafana_manager.docker')
    @patch('grafana_manager.app.services.grafana_manager.GrafanaManager.get_grafana_settings')
    def test_start_grafana_new_container(self, mock_get_settings, mock_docker):
        """Тест запуска нового контейнера Grafana."""
        mock_get_settings.return_value = {
            "grafana-settings": {
                "name": "test-grafana",
                "image": "grafana/grafana",
                "port": 3000,
                "usr": "admin",
                "pwd": "admin"
            }
        }
        mock_client = MagicMock()
        mock_client.containers.get.side_effect = docker.errors.NotFound("Not found")
        mock_container = MagicMock()
        mock_client.containers.run.return_value = mock_container
        mock_docker.from_env.return_value = mock_client
        
        manager = GrafanaManager()
        result = manager.start_grafana()
        
        assert result is True
        mock_client.containers.run.assert_called_once()

    @patch('grafana_manager.app.services.grafana_manager.docker')
    @patch('grafana_manager.app.services.grafana_manager.GrafanaManager.get_grafana_settings')
    def test_start_grafana_existing_running(self, mock_get_settings, mock_docker):
        """Тест запуска уже запущенного контейнера Grafana."""
        mock_get_settings.return_value = {
            "grafana-settings": {
                "name": "test-grafana",
                "image": "grafana/grafana",
                "port": 3000,
                "usr": "admin",
                "pwd": "admin"
            }
        }
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.status = "running"
        mock_client.containers.get.return_value = mock_container
        mock_docker.from_env.return_value = mock_client
        
        manager = GrafanaManager()
        result = manager.start_grafana()
        
        assert result is True
        mock_client.containers.run.assert_not_called()

    @patch('grafana_manager.app.services.grafana_manager.docker')
    @patch('grafana_manager.app.services.grafana_manager.GrafanaManager.get_grafana_settings')
    def test_start_grafana_existing_stopped(self, mock_get_settings, mock_docker):
        """Тест запуска остановленного контейнера Grafana."""
        mock_get_settings.return_value = {
            "grafana-settings": {
                "name": "test-grafana",
                "image": "grafana/grafana",
                "port": 3000,
                "usr": "admin",
                "pwd": "admin"
            }
        }
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.status = "stopped"
        mock_client.containers.get.return_value = mock_container
        mock_docker.from_env.return_value = mock_client
        
        manager = GrafanaManager()
        result = manager.start_grafana()
        
        assert result is True
        mock_container.start.assert_called_once()

    @patch('grafana_manager.app.services.grafana_manager.docker')
    @patch('grafana_manager.app.services.grafana_manager.GrafanaManager.get_grafana_settings')
    def test_start_grafana_exception(self, mock_get_settings, mock_docker):
        """Тест исключения при запуске Grafana."""
        mock_get_settings.return_value = {
            "grafana-settings": {
                "name": "test-grafana",
                "image": "grafana/grafana",
                "port": 3000,
                "usr": "admin",
                "pwd": "admin"
            }
        }
        mock_client = MagicMock()
        mock_client.containers.get.side_effect = Exception("Error")
        mock_docker.from_env.return_value = mock_client
        
        manager = GrafanaManager()
        result = manager.start_grafana()
        
        assert result is False

    @patch('grafana_manager.app.services.grafana_manager.docker')
    @patch('grafana_manager.app.services.grafana_manager.GrafanaManager.get_grafana_settings')
    def test_stop_grafana_success(self, mock_get_settings, mock_docker):
        """Тест успешной остановки Grafana."""
        mock_get_settings.return_value = {
            "grafana-settings": {"name": "test-grafana"}
        }
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.status = "running"
        mock_client.containers.get.return_value = mock_container
        mock_docker.from_env.return_value = mock_client
        
        manager = GrafanaManager()
        manager.container = mock_container
        result = manager.stop_grafana()
        
        assert result is True
        mock_container.stop.assert_called_once()

    @patch('grafana_manager.app.services.grafana_manager.docker')
    @patch('grafana_manager.app.services.grafana_manager.GrafanaManager.get_grafana_settings')
    def test_stop_grafana_not_running(self, mock_get_settings, mock_docker):
        """Тест остановки не запущенного контейнера."""
        mock_get_settings.return_value = {
            "grafana-settings": {"name": "test-grafana"}
        }
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.status = "stopped"
        mock_client.containers.get.return_value = mock_container
        mock_docker.from_env.return_value = mock_client
        
        manager = GrafanaManager()
        manager.container = mock_container
        result = manager.stop_grafana()
        
        assert result is False

    @patch('grafana_manager.app.services.grafana_manager.docker')
    @patch('grafana_manager.app.services.grafana_manager.GrafanaManager.get_grafana_settings')
    def test_get_status_success(self, mock_get_settings, mock_docker):
        """Тест получения статуса Grafana."""
        mock_get_settings.return_value = {
            "grafana-settings": {"name": "test-grafana"}
        }
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.status = "running"
        mock_client.containers.get.return_value = mock_container
        mock_docker.from_env.return_value = mock_client
        
        manager = GrafanaManager()
        manager.container = mock_container
        result = manager.get_status()
        
        assert result == "running"
        mock_container.reload.assert_called_once()

    @patch('grafana_manager.app.services.grafana_manager.docker')
    @patch('grafana_manager.app.services.grafana_manager.GrafanaManager.get_grafana_settings')
    def test_get_status_exception(self, mock_get_settings, mock_docker):
        """Тест исключения при получении статуса."""
        mock_get_settings.return_value = {
            "grafana-settings": {"name": "test-grafana"}
        }
        mock_client = MagicMock()
        mock_client.containers.get.side_effect = Exception("Error")
        mock_docker.from_env.return_value = mock_client
        
        manager = GrafanaManager()
        result = manager.get_status()
        
        assert result is None

    @patch('builtins.open', new_callable=mock_open, read_data='grafana-settings:\n  name: test\n')
    @patch('grafana_manager.app.services.grafana_manager.yaml.safe_load')
    @patch('grafana_manager.app.services.grafana_manager.os.path.join')
    def test_get_grafana_settings(self, mock_join, mock_yaml_load, mock_file):
        """Тест получения настроек Grafana."""
        mock_yaml_load.return_value = {"grafana-settings": {"name": "test"}}
        
        result = GrafanaManager.get_grafana_settings()
        
        assert "grafana-settings" in result
        mock_yaml_load.assert_called_once()

    @patch('builtins.open', new_callable=mock_open)
    @patch('grafana_manager.app.services.grafana_manager.yaml.dump')
    @patch('grafana_manager.app.services.grafana_manager.os.path.join')
    def test_update_grafana_settings(self, mock_join, mock_yaml_dump, mock_file):
        """Тест обновления настроек Grafana."""
        settings = {"grafana-settings": {"name": "test"}}
        
        result = GrafanaManager.update_grafana_settings(settings)
        
        assert result is True
        mock_yaml_dump.assert_called_once()

