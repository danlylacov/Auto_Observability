"""Тесты для роутеров Prometheus Manager."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from tests.conftest import import_service_app

prometheus_manager_app = import_service_app("prometheus_manager")


@pytest.fixture
def client():
    return TestClient(prometheus_manager_app)


class TestPrometheusManagerRouter:
    """Тесты для роутеров Prometheus Manager."""

    @patch('prometheus_manager.app.routes.manage.get_prometheus_manager')
    def test_start_prometheus_success(self, mock_get_manager, client):
        """Тест успешного запуска Prometheus."""
        mock_manager = MagicMock()
        mock_manager.start.return_value = True
        mock_get_manager.return_value = mock_manager

        response = client.post("/api/v1/manage/prometheus/start")
        
        assert response.status_code == 200
        assert response.json()["status"] == "started"
        mock_manager.start.assert_called_once()

    @patch('prometheus_manager.app.routes.manage.get_prometheus_manager')
    def test_start_prometheus_failure(self, mock_get_manager, client):
        """Тест неудачного запуска Prometheus."""
        mock_manager = MagicMock()
        mock_manager.start.return_value = False
        mock_get_manager.return_value = mock_manager

        response = client.post("/api/v1/manage/prometheus/start")
        
        assert response.status_code == 500
        assert "Failed to start" in response.json()["detail"]

    @patch('prometheus_manager.app.routes.manage.get_prometheus_manager')
    def test_start_prometheus_exception(self, mock_get_manager, client):
        """Тест исключения при запуске Prometheus."""
        mock_manager = MagicMock()
        mock_manager.start.side_effect = Exception("Start error")
        mock_get_manager.return_value = mock_manager

        response = client.post("/api/v1/manage/prometheus/start")
        
        assert response.status_code == 500
        assert "Failed to start" in response.json()["detail"]

    @patch('prometheus_manager.app.routes.manage.get_prometheus_manager')
    def test_stop_prometheus_success(self, mock_get_manager, client):
        """Тест успешной остановки Prometheus."""
        mock_manager = MagicMock()
        mock_manager.stop.return_value = True
        mock_get_manager.return_value = mock_manager

        response = client.post("/api/v1/manage/prometheus/stop")
        
        assert response.status_code == 200
        assert response.json()["status"] == "stopped"
        mock_manager.stop.assert_called_once()

    @patch('prometheus_manager.app.routes.manage.get_prometheus_manager')
    def test_stop_prometheus_not_running(self, mock_get_manager, client):
        """Тест остановки не запущенного Prometheus."""
        mock_manager = MagicMock()
        mock_manager.stop.return_value = False
        mock_get_manager.return_value = mock_manager

        response = client.post("/api/v1/manage/prometheus/stop")
        
        assert response.status_code == 200
        assert response.json()["status"] == "not_found"

    @patch('prometheus_manager.app.routes.manage.get_prometheus_manager')
    def test_stop_prometheus_exception(self, mock_get_manager, client):
        """Тест исключения при остановке Prometheus."""
        mock_manager = MagicMock()
        mock_manager.stop.side_effect = Exception("Stop error")
        mock_get_manager.return_value = mock_manager

        response = client.post("/api/v1/manage/prometheus/stop")
        
        assert response.status_code == 500
        assert "Failed to stop" in response.json()["detail"]

    @patch('prometheus_manager.app.routes.manage.get_prometheus_manager')
    def test_get_prometheus_status_success(self, mock_get_manager, client):
        """Тест получения статуса Prometheus."""
        mock_manager = MagicMock()
        mock_manager.status.return_value = {"status": "running", "container_id": "test123"}
        mock_get_manager.return_value = mock_manager

        response = client.get("/api/v1/manage/prometheus/status")
        
        assert response.status_code == 200
        assert response.json()["status"] == "running"
        mock_manager.status.assert_called_once()

    @patch('prometheus_manager.app.routes.manage.get_prometheus_manager')
    def test_get_prometheus_status_exception(self, mock_get_manager, client):
        """Тест исключения при получении статуса."""
        mock_manager = MagicMock()
        mock_manager.status.side_effect = Exception("Status error")
        mock_get_manager.return_value = mock_manager

        response = client.get("/api/v1/manage/prometheus/status")
        
        assert response.status_code == 500
        assert "Failed to get status" in response.json()["detail"]

    @patch('prometheus_manager.app.routes.manage.PrometheusManager')
    def test_get_settings_success(self, mock_prometheus_manager_class, client):
        """Тест получения настроек Prometheus."""
        mock_prometheus_manager_class.get_prometheus_settings.return_value = {
            "global": {"scrape_interval": "15s"}
        }

        response = client.get("/api/v1/manage/prometheus/settings")
        
        assert response.status_code == 200
        assert "global" in response.json()
        mock_prometheus_manager_class.get_prometheus_settings.assert_called_once()

    @patch('prometheus_manager.app.routes.manage.PrometheusManager')
    def test_get_settings_exception(self, mock_prometheus_manager_class, client):
        """Тест исключения при получении настроек."""
        mock_prometheus_manager_class.get_prometheus_settings.side_effect = Exception("Settings error")

        response = client.get("/api/v1/manage/prometheus/settings")
        
        assert response.status_code == 500
        assert "Failed to get settings" in response.json()["detail"]

    @patch('prometheus_manager.app.routes.manage.PrometheusManager')
    def test_update_settings_success(self, mock_prometheus_manager_class, client):
        """Тест обновления настроек Prometheus."""
        mock_prometheus_manager_class.update_prometheus_settings.return_value = True

        response = client.post(
            "/api/v1/manage/prometheus/settings",
            json={"global": {"scrape_interval": "30s"}}
        )
        
        assert response.status_code == 200
        assert "updated successfully" in response.json()["message"]
        mock_prometheus_manager_class.update_prometheus_settings.assert_called_once()

    @patch('prometheus_manager.app.routes.manage.PrometheusManager')
    def test_update_settings_failure(self, mock_prometheus_manager_class, client):
        """Тест неудачного обновления настроек."""
        mock_prometheus_manager_class.update_prometheus_settings.return_value = False

        response = client.post(
            "/api/v1/manage/prometheus/settings",
            json={"global": {"scrape_interval": "30s"}}
        )
        
        assert response.status_code == 500
        assert "Failed to update settings" in response.json()["detail"]

    @patch('prometheus_manager.app.routes.manage.PrometheusManager')
    def test_update_settings_exception(self, mock_prometheus_manager_class, client):
        """Тест исключения при обновлении настроек."""
        mock_prometheus_manager_class.update_prometheus_settings.side_effect = Exception("Update error")

        response = client.post(
            "/api/v1/manage/prometheus/settings",
            json={"global": {"scrape_interval": "30s"}}
        )
        
        assert response.status_code == 500
        assert "Failed to update settings" in response.json()["detail"]

    @patch('prometheus_manager.app.routes.manage.get_update_config')
    def test_update_config_success(self, mock_get_update_config, client):
        """Тест обновления конфигурации Prometheus."""
        mock_updater = MagicMock()
        mock_updater.update.return_value = None
        mock_get_update_config.return_value = mock_updater

        response = client.post("/api/v1/manage/config/update")
        
        assert response.status_code == 200
        assert "updated successfully" in response.json()["message"]
        mock_updater.update.assert_called_once()

    @patch('prometheus_manager.app.routes.manage.get_update_config')
    def test_update_config_exception(self, mock_get_update_config, client):
        """Тест исключения при обновлении конфигурации."""
        mock_updater = MagicMock()
        mock_updater.update.side_effect = Exception("Update error")
        mock_get_update_config.return_value = mock_updater

        response = client.post("/api/v1/manage/config/update")
        
        assert response.status_code == 500
        assert "Failed to update config" in response.json()["detail"]

