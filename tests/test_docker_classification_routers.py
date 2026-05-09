"""Тесты для роутеров Docker Classification."""

import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from tests.conftest import import_service_app

docker_classification_app = import_service_app("docker_classification")


@pytest.fixture
def client():
    """Фикстура для тестового клиента FastAPI."""
    return TestClient(docker_classification_app)


class TestClassificateRouter:
    """Тесты для роутера classificate."""

    @patch('docker_classification.app.routers.classificate.WeightedDiscovery')
    def test_classificate_success(self, mock_discovery_class, client):
        """Тест успешной классификации контейнера."""
        mock_discovery = MagicMock()
        mock_discovery.classify_container.return_value = [["postgresql", 100]]
        mock_discovery_class.return_value = mock_discovery

        response = client.post(
            "/api/v1/classificate/",
            json={
                "labels": {},
                "envs": [],
                "image": "postgres:latest",
                "ports": ["5432"]
            }
        )
        
        assert response.status_code == 200
        assert "result" in response.json()
        assert response.json()["result"][0][0] == "postgresql"

    @patch('docker_classification.app.routers.classificate.WeightedDiscovery')
    def test_classificate_error(self, mock_discovery_class, client):
        """Тест классификации при ошибке."""
        mock_discovery = MagicMock()
        mock_discovery.classify_container.side_effect = Exception("Test error")
        mock_discovery_class.return_value = mock_discovery

        response = client.post(
            "/api/v1/classificate/",
            json={
                "labels": {},
                "envs": [],
                "image": "test:latest",
                "ports": []
            }
        )
        
        assert response.status_code == 200
        assert "error" in response.json()

