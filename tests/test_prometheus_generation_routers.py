"""Тесты для роутеров Prometheus Generation."""

import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from tests.conftest import import_service_app

prometheus_generation_app = import_service_app("prometheus_generation")


@pytest.fixture
def client():
    """Фикстура для тестового клиента FastAPI."""
    return TestClient(prometheus_generation_app)


class TestGenerateRouter:
    """Тесты для роутера generate."""

    @patch('prometheus_generation.app.routers.generate.MinioService')
    @patch('prometheus_generation.app.routers.generate.PrometheusConfigGenerator')
    def test_generate_success(self, mock_generator_class, mock_minio_service_class, client):
        """Тест успешной генерации конфигурации."""
        mock_generator = MagicMock()
        mock_generator.generate_config.return_value = {
            "config": {
                "scrape_config": {"job_name": "test"},
                "target": {"targets": ["localhost:9187"]}
            },
            "exporter_config": {
                "exporter_image": "prom/postgres-exporter",
                "exporter_port": 9187
            }
        }
        mock_generator.exporter_configs = {"postgresql": {}}
        mock_generator_class.return_value = mock_generator
        
        mock_minio_service = MagicMock()
        mock_minio_service.upload_config.return_value = {
            "scrape_config": {"job_name": "test"},
            "target": {"targets": ["localhost:9187"]}
        }
        mock_minio_service_class.return_value = mock_minio_service

        response = client.post(
            "/api/v1/generate/",
            params={"host": "localhost"},
            json={
                "info": {"Id": "container1"},
                "classification": {"result": [["postgresql", 100]]}
            }
        )
        
        assert response.status_code == 200
        assert "config" in response.json()
        assert "info" in response.json()

    @patch('prometheus_generation.app.routers.generate.PrometheusConfigGenerator')
    def test_generate_no_exporter(self, mock_generator_class, client):
        """Тест генерации конфигурации при отсутствии экспортера."""
        mock_generator = MagicMock()
        mock_generator.generate_config.return_value = None
        mock_generator.exporter_configs = {"postgresql": {}}
        mock_generator_class.return_value = mock_generator

        response = client.post(
            "/api/v1/generate/",
            params={"host": "localhost"},
            json={
                "info": {"Id": "container1"},
                "classification": {"result": [["unknown_stack", 100]]}
            }
        )
        
        assert response.status_code == 400

