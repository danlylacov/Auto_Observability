"""Тесты для сервисов Prometheus Manager."""

import pytest
from unittest.mock import MagicMock, patch, mock_open
import docker.errors

from prometheus_manager.app.services.prometheus_manager import PrometheusManager


class TestPrometheusManager:
    """Тесты для PrometheusManager."""

    @patch('prometheus_manager.app.services.prometheus_manager.docker')
    @patch('prometheus_manager.app.services.prometheus_manager.os.path.exists')
    @patch('prometheus_manager.app.services.prometheus_manager.os.path.dirname')
    @patch('prometheus_manager.app.services.prometheus_manager.os.path.abspath')
    @patch('prometheus_manager.app.services.prometheus_manager.os.path.join')
    @patch('prometheus_manager.app.services.prometheus_manager.os.environ.get')
    @patch('prometheus_manager.app.services.prometheus_manager.PrometheusManager.get_prometheus_settings')
    def test_init(self, mock_get_settings, mock_getenv, mock_join, mock_abspath, mock_dirname, mock_exists, mock_docker):
        """Тест инициализации PrometheusManager."""
        mock_getenv.return_value = None
        mock_get_settings.return_value = {"prometheus-settings": {"name": "test-prometheus"}}
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        
        manager = PrometheusManager()
        
        assert manager.client == mock_client
        assert manager.container_name == "test-prometheus"

    @patch('prometheus_manager.app.services.prometheus_manager.docker')
    @patch('prometheus_manager.app.services.prometheus_manager.PrometheusManager.get_prometheus_settings')
    def test_start_success(self, mock_get_settings, mock_docker):
        """Тест успешного запуска Prometheus."""
        mock_get_settings.return_value = {
            "prometheus-settings": {"name": "test-prometheus", "image": "prom/prometheus"}
        }
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_client.containers.run.return_value = mock_container
        mock_client.containers.get.side_effect = docker.errors.NotFound("Not found")
        mock_docker.from_env.return_value = mock_client
        
        manager = PrometheusManager()
        result = manager.start()
        
        assert result is True
        mock_client.containers.run.assert_called_once()

    @patch('prometheus_manager.app.services.prometheus_manager.docker')
    @patch('prometheus_manager.app.services.prometheus_manager.PrometheusManager.get_prometheus_settings')
    def test_start_exception(self, mock_get_settings, mock_docker):
        """Тест исключения при запуске Prometheus."""
        mock_get_settings.return_value = {
            "prometheus-settings": {"name": "test-prometheus", "image": "prom/prometheus"}
        }
        mock_client = MagicMock()
        mock_client.containers.get.side_effect = docker.errors.NotFound("Not found")
        mock_client.containers.run.side_effect = Exception("Start error")
        mock_docker.from_env.return_value = mock_client
        
        manager = PrometheusManager()
        result = manager.start()
        
        assert result is False

    @patch('prometheus_manager.app.services.prometheus_manager.docker')
    @patch('prometheus_manager.app.services.prometheus_manager.PrometheusManager.get_prometheus_settings')
    def test_stop_success(self, mock_get_settings, mock_docker):
        """Тест успешной остановки Prometheus."""
        mock_get_settings.return_value = {
            "prometheus-settings": {"name": "test-prometheus"}
        }
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_client.containers.get.return_value = mock_container
        mock_docker.from_env.return_value = mock_client
        
        manager = PrometheusManager()
        result = manager.stop()
        
        assert result is True
        mock_container.stop.assert_called_once()
        mock_container.remove.assert_called_once()

    @patch('prometheus_manager.app.services.prometheus_manager.docker')
    @patch('prometheus_manager.app.services.prometheus_manager.PrometheusManager.get_prometheus_settings')
    def test_stop_not_found(self, mock_get_settings, mock_docker):
        """Тест остановки несуществующего контейнера."""
        mock_get_settings.return_value = {
            "prometheus-settings": {"name": "test-prometheus"}
        }
        mock_client = MagicMock()
        mock_client.containers.get.side_effect = docker.errors.NotFound("Not found")
        mock_docker.from_env.return_value = mock_client
        
        manager = PrometheusManager()
        result = manager.stop()
        
        assert result is False

    @patch('prometheus_manager.app.services.prometheus_manager.docker')
    @patch('prometheus_manager.app.services.prometheus_manager.PrometheusManager.get_prometheus_settings')
    def test_status_running(self, mock_get_settings, mock_docker):
        """Тест получения статуса запущенного контейнера."""
        mock_get_settings.return_value = {
            "prometheus-settings": {"name": "test-prometheus"}
        }
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.status = "running"
        mock_container.attrs = {"Created": "2023-01-01T00:00:00Z"}
        mock_client.containers.get.return_value = mock_container
        mock_docker.from_env.return_value = mock_client
        
        manager = PrometheusManager()
        result = manager.status()
        
        assert result["status"] == "running"
        assert "created" in result

    @patch('prometheus_manager.app.services.prometheus_manager.docker')
    @patch('prometheus_manager.app.services.prometheus_manager.PrometheusManager.get_prometheus_settings')
    def test_status_not_found(self, mock_get_settings, mock_docker):
        """Тест получения статуса несуществующего контейнера."""
        mock_get_settings.return_value = {
            "prometheus-settings": {"name": "test-prometheus"}
        }
        mock_client = MagicMock()
        # Создаем правильный класс исключения
        NotFound = type('NotFound', (Exception,), {})
        mock_docker.errors = MagicMock()
        mock_docker.errors.NotFound = NotFound
        mock_client.containers.get.side_effect = NotFound("Not found")
        mock_docker.from_env.return_value = mock_client
        
        manager = PrometheusManager()
        result = manager.status()
        
        assert result["status"] == "not found"

    @patch('builtins.open', new_callable=mock_open, read_data='prometheus-settings:\n  name: test\n')
    @patch('prometheus_manager.app.services.prometheus_manager.yaml.safe_load')
    @patch('prometheus_manager.app.services.prometheus_manager.os.path.join')
    def test_get_prometheus_settings(self, mock_join, mock_yaml_load, mock_file):
        """Тест получения настроек Prometheus."""
        mock_yaml_load.return_value = {"prometheus-settings": {"name": "test"}}
        
        result = PrometheusManager.get_prometheus_settings()
        
        assert "prometheus-settings" in result
        mock_yaml_load.assert_called_once()

    @patch('builtins.open', new_callable=mock_open)
    @patch('prometheus_manager.app.services.prometheus_manager.yaml.dump')
    @patch('prometheus_manager.app.services.prometheus_manager.os.path.join')
    def test_update_prometheus_settings(self, mock_join, mock_yaml_dump, mock_file):
        """Тест обновления настроек Prometheus."""
        settings = {"prometheus-settings": {"name": "test"}}
        
        result = PrometheusManager.update_prometheus_settings(settings)
        
        assert result is True
        mock_yaml_dump.assert_called_once_with(settings, mock_file.return_value.__enter__.return_value)

