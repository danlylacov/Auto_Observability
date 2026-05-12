"""Тесты для роутеров Grafana Manager."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from tests.conftest import import_service_app

grafana_manager_app = import_service_app("grafana_manager")


@pytest.fixture
def client():
    return TestClient(grafana_manager_app)


class TestGrafanaManagerRouter:
    """Тесты для роутеров Grafana Manager."""

    @patch('grafana_manager.app.routes.manage.get_grafana_manager')
    def test_start_grafana_success(self, mock_get_manager, client):
        """Тест успешного запуска Grafana."""
        mock_manager = MagicMock()
        mock_manager.start_grafana.return_value = True
        mock_get_manager.return_value = mock_manager

        response = client.post("/api/v1/manage/grafana/start")
        
        assert response.status_code == 200
        assert response.json()["status"] == "started"
        mock_manager.start_grafana.assert_called_once()

    @patch('grafana_manager.app.routes.manage.get_grafana_manager')
    def test_start_grafana_failure(self, mock_get_manager, client):
        """Тест неудачного запуска Grafana."""
        mock_manager = MagicMock()
        mock_manager.start_grafana.return_value = False
        mock_get_manager.return_value = mock_manager

        response = client.post("/api/v1/manage/grafana/start")
        
        assert response.status_code == 500
        assert "Failed to start" in response.json()["detail"]

    @patch('grafana_manager.app.routes.manage.get_grafana_manager')
    def test_start_grafana_exception(self, mock_get_manager, client):
        """Тест исключения при запуске Grafana."""
        mock_manager = MagicMock()
        mock_manager.start_grafana.side_effect = Exception("Start error")
        mock_get_manager.return_value = mock_manager

        response = client.post("/api/v1/manage/grafana/start")
        
        assert response.status_code == 500
        assert "Failed to start" in response.json()["detail"]

    @patch('grafana_manager.app.routes.manage.get_grafana_manager')
    def test_stop_grafana_success(self, mock_get_manager, client):
        """Тест успешной остановки Grafana."""
        mock_manager = MagicMock()
        mock_manager.stop_grafana.return_value = True
        mock_get_manager.return_value = mock_manager

        response = client.post("/api/v1/manage/grafana/stop")
        
        assert response.status_code == 200
        assert response.json()["status"] == "stopped"
        mock_manager.stop_grafana.assert_called_once()

    @patch('grafana_manager.app.routes.manage.get_grafana_manager')
    def test_stop_grafana_not_running(self, mock_get_manager, client):
        """Тест остановки не запущенной Grafana."""
        mock_manager = MagicMock()
        mock_manager.stop_grafana.return_value = False
        mock_get_manager.return_value = mock_manager

        response = client.post("/api/v1/manage/grafana/stop")
        
        assert response.status_code == 200
        assert response.json()["status"] == "not_found"

    @patch('grafana_manager.app.routes.manage.get_grafana_manager')
    def test_stop_grafana_exception(self, mock_get_manager, client):
        """Тест исключения при остановке Grafana."""
        mock_manager = MagicMock()
        mock_manager.stop_grafana.side_effect = Exception("Stop error")
        mock_get_manager.return_value = mock_manager

        response = client.post("/api/v1/manage/grafana/stop")
        
        assert response.status_code == 500
        assert "Failed to stop" in response.json()["detail"]

    @patch('grafana_manager.app.routes.manage.get_grafana_manager')
    def test_restart_grafana_success(self, mock_get_manager, client):
        mock_manager = MagicMock()
        mock_manager.restart_grafana.return_value = True
        mock_get_manager.return_value = mock_manager

        response = client.post("/api/v1/manage/grafana/restart")

        assert response.status_code == 200
        assert response.json()["status"] == "restarted"
        mock_manager.restart_grafana.assert_called_once()

    @patch('grafana_manager.app.routes.manage.get_grafana_manager')
    def test_restart_grafana_failure(self, mock_get_manager, client):
        mock_manager = MagicMock()
        mock_manager.restart_grafana.return_value = False
        mock_get_manager.return_value = mock_manager

        response = client.post("/api/v1/manage/grafana/restart")

        assert response.status_code == 500
        assert "Failed to restart" in response.json()["detail"]

    @patch('grafana_manager.app.routes.manage.get_grafana_manager')
    def test_restart_grafana_exception(self, mock_get_manager, client):
        mock_manager = MagicMock()
        mock_manager.restart_grafana.side_effect = Exception("Restart error")
        mock_get_manager.return_value = mock_manager

        response = client.post("/api/v1/manage/grafana/restart")

        assert response.status_code == 500
        assert "Failed to restart" in response.json()["detail"]

    @patch('grafana_manager.app.routes.manage.get_grafana_manager')
    def test_get_grafana_status_success(self, mock_get_manager, client):
        """Тест получения статуса Grafana."""
        mock_manager = MagicMock()
        mock_manager.get_status.return_value = "running"
        mock_get_manager.return_value = mock_manager

        response = client.get("/api/v1/manage/grafana/status")
        
        assert response.status_code == 200
        assert response.json()["status"] == "running"
        mock_manager.get_status.assert_called_once()

    @patch('grafana_manager.app.routes.manage.get_grafana_manager')
    def test_get_grafana_status_none(self, mock_get_manager, client):
        """Тест получения статуса когда статус None."""
        mock_manager = MagicMock()
        mock_manager.get_status.return_value = None
        mock_get_manager.return_value = mock_manager

        response = client.get("/api/v1/manage/grafana/status")
        
        assert response.status_code == 200
        assert response.json()["status"] == "unknown"

    @patch('grafana_manager.app.routes.manage.get_grafana_manager')
    def test_get_grafana_status_exception(self, mock_get_manager, client):
        """Тест исключения при получении статуса."""
        mock_manager = MagicMock()
        mock_manager.get_status.side_effect = Exception("Status error")
        mock_get_manager.return_value = mock_manager

        response = client.get("/api/v1/manage/grafana/status")
        
        assert response.status_code == 500
        assert "Failed to get status" in response.json()["detail"]

    @patch('grafana_manager.app.routes.manage.get_grafana_manager')
    def test_get_settings_success(self, mock_get_manager, client):
        """Тест получения настроек Grafana."""
        mock_manager = MagicMock()
        mock_manager.get_grafana_settings.return_value = {
            "server": {"port": 3000}
        }
        mock_get_manager.return_value = mock_manager

        response = client.get("/api/v1/manage/grafana/settings")
        
        assert response.status_code == 200
        assert "server" in response.json()
        mock_manager.get_grafana_settings.assert_called_once()

    @patch('grafana_manager.app.routes.manage.get_grafana_manager')
    def test_get_settings_exception(self, mock_get_manager, client):
        """Тест исключения при получении настроек."""
        mock_manager = MagicMock()
        mock_manager.get_grafana_settings.side_effect = Exception("Settings error")
        mock_get_manager.return_value = mock_manager

        response = client.get("/api/v1/manage/grafana/settings")
        
        assert response.status_code == 500
        assert "Failed to get settings" in response.json()["detail"]

    @patch('grafana_manager.app.routes.manage.get_grafana_manager')
    def test_update_settings_success(self, mock_get_manager, client):
        """Тест обновления настроек Grafana."""
        mock_manager = MagicMock()
        mock_manager.update_grafana_settings.return_value = True
        mock_get_manager.return_value = mock_manager

        response = client.post(
            "/api/v1/manage/grafana/settings",
            json={"server": {"port": 3001}}
        )
        
        assert response.status_code == 200
        assert "updated successfully" in response.json()["message"]
        mock_manager.update_grafana_settings.assert_called_once()

    @patch('grafana_manager.app.routes.manage.get_grafana_manager')
    def test_update_settings_failure(self, mock_get_manager, client):
        """Тест неудачного обновления настроек."""
        mock_manager = MagicMock()
        mock_manager.update_grafana_settings.return_value = False
        mock_get_manager.return_value = mock_manager

        response = client.post(
            "/api/v1/manage/grafana/settings",
            json={"server": {"port": 3001}}
        )
        
        assert response.status_code == 500
        assert "Failed to update settings" in response.json()["detail"]

    @patch('grafana_manager.app.routes.manage.get_grafana_manager')
    def test_update_settings_exception(self, mock_get_manager, client):
        """Тест исключения при обновлении настроек."""
        mock_manager = MagicMock()
        mock_manager.update_grafana_settings.side_effect = Exception("Update error")
        mock_get_manager.return_value = mock_manager

        response = client.post(
            "/api/v1/manage/grafana/settings",
            json={"server": {"port": 3001}}
        )
        
        assert response.status_code == 500
        assert "Failed to update settings" in response.json()["detail"]

