"""Тесты для сервисов Prometheus Generation."""

import sys
import importlib
import pytest
from unittest.mock import MagicMock, patch, mock_open
import yaml

# Настраиваем алиас 'app' для prometheus_generation перед импортами
import prometheus_generation.app as prometheus_generation_app_module
sys.modules["app"] = prometheus_generation_app_module
# Без этого getattr(prometheus_generation.app, 'services') и ключ
# sys.modules['prometheus_generation.app.services'] — разные модули, и unittest.mock.patch
# на prometheus_generation.app.services.... не находит prometheus_config_generator.
_services_pkg = importlib.import_module("prometheus_generation.app.services")
prometheus_generation_app_module.services = _services_pkg
sys.modules["app.services"] = _services_pkg
importlib.import_module("prometheus_generation.app.services.prometheus_config_generator")

from prometheus_generation.app.services.prometheus_config_generator import PrometheusConfigGenerator
from prometheus_generation.app.services.main_config import MainPrometheusConfig
from prometheus_generation.app.services.exporter_env_generator import ExporterEnvGenerator
from prometheus_generation.app.services.minio import MinioService
from prometheus_generation.app.services.signature import Signature


class TestPrometheusConfigGenerator:
    """Тесты для PrometheusConfigGenerator."""

    @patch('prometheus_generation.app.services.prometheus_config_generator.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='nginx:\n  exporter_image: nginx-exporter')
    @patch('prometheus_generation.app.services.prometheus_config_generator.yaml.safe_load')
    def test_init(self, mock_yaml_load, mock_file, mock_exists):
        """Тест инициализации PrometheusConfigGenerator."""
        mock_exists.return_value = True
        mock_yaml_load.return_value = {"nginx": {"exporter_image": "nginx-exporter"}}
        
        generator = PrometheusConfigGenerator()
        
        assert "nginx" in generator.exporter_configs

    @patch('prometheus_generation.app.services.prometheus_config_generator.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='nginx:\n  exporter_image: nginx-exporter')
    @patch('prometheus_generation.app.services.prometheus_config_generator.yaml.safe_load')
    def test_get_container_name(self, mock_yaml_load, mock_file, mock_exists):
        """Тест получения имени контейнера."""
        mock_exists.return_value = True
        mock_yaml_load.return_value = {"nginx": {}}
        
        generator = PrometheusConfigGenerator()
        container_info = {"Name": "/test-container"}
        result = generator._get_container_name(container_info)
        
        assert result == "test-container"

    @patch('prometheus_generation.app.services.prometheus_config_generator.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='nginx:\n  exporter_image: nginx-exporter')
    @patch('prometheus_generation.app.services.prometheus_config_generator.yaml.safe_load')
    def test_get_stack_from_classification(self, mock_yaml_load, mock_file, mock_exists):
        """Тест получения стека из классификации."""
        mock_exists.return_value = True
        mock_yaml_load.return_value = {"nginx": {}}
        
        generator = PrometheusConfigGenerator()
        classification = {"result": [["nginx", 0.9]]}
        result = generator._get_stack_from_classification(classification)
        
        assert result == "nginx"

    @patch('prometheus_generation.app.services.prometheus_config_generator.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='nginx:\n  exporter_image: nginx-exporter')
    @patch('prometheus_generation.app.services.prometheus_config_generator.yaml.safe_load')
    def test_normalize_stack_name(self, mock_yaml_load, mock_file, mock_exists):
        """Тест нормализации имени стека."""
        mock_exists.return_value = True
        mock_yaml_load.return_value = {"nginx": {}}
        
        generator = PrometheusConfigGenerator()
        result = generator._normalize_stack_name("PostgreSQL")
        
        assert result == "postgresql"

    @patch('prometheus_generation.app.services.prometheus_config_generator.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='mongodb:\n  exporter_port: 9216\n  job_name_suffix: _mongodb')
    @patch('prometheus_generation.app.services.prometheus_config_generator.yaml.safe_load')
    def test_build_prometheus_config_uses_scrape_port_override(self, mock_yaml_load, mock_file, mock_exists):
        """Host publish port must appear in targets when prometheus_scrape_port is set."""
        mock_exists.return_value = True
        mock_yaml_load.return_value = {
            "mongodb": {
                "exporter_port": 9216,
                "job_name_suffix": "_mongodb",
                "scrape_interval": "15s",
                "scrape_timeout": "10s",
                "prometheus_scrape_port": 9100,
            }
        }
        generator = PrometheusConfigGenerator()
        cfg = {
            "exporter_port": 9216,
            "job_name_suffix": "_mongodb",
            "scrape_interval": "15s",
            "scrape_timeout": "10s",
            "prometheus_scrape_port": 9100,
        }
        out = generator._build_prometheus_config(
            "my-mongo",
            {"Config": {"Labels": {}}},
            cfg,
            "localhost",
        )
        assert out["target"]["targets"] == ["localhost:9100"]

    @patch('prometheus_generation.app.services.prometheus_config_generator.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='nginx:\n  exporter_image: nginx-exporter')
    @patch('prometheus_generation.app.services.prometheus_config_generator.yaml.safe_load')
    def test_generate_config_success(self, mock_yaml_load, mock_file, mock_exists):
        """Тест успешной генерации конфигурации."""
        mock_exists.return_value = True
        mock_yaml_load.return_value = {
            "nginx": {
                "exporter_image": "nginx-exporter",
                "exporter_port": 9100
            }
        }
        
        generator = PrometheusConfigGenerator()
        
        container_data = {
            "info": {"Name": "/test-container", "NetworkSettings": {}},
            "classification": {"result": [["nginx", 0.9]]}
        }
        
        with patch.object(generator.env_generator, 'generate_env_vars', return_value={}):
            with patch.object(generator.env_generator, 'get_container_network', return_value=None):
                result = generator.generate_config(container_data, "localhost:8080")
                
                assert result is not None
                assert "config" in result
                assert "exporter_config" in result

    @patch('prometheus_generation.app.services.prometheus_config_generator.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='nginx:\n  exporter_image: nginx-exporter')
    @patch('prometheus_generation.app.services.prometheus_config_generator.yaml.safe_load')
    def test_generate_config_no_stack(self, mock_yaml_load, mock_file, mock_exists):
        """Тест генерации конфигурации без стека."""
        mock_exists.return_value = True
        mock_yaml_load.return_value = {"nginx": {}}
        
        generator = PrometheusConfigGenerator()
        
        container_data = {
            "info": {"Name": "/test-container"},
            "classification": {"result": []}
        }
        
        result = generator.generate_config(container_data, "localhost:8080")
        
        assert result is None

    @patch('prometheus_generation.app.services.prometheus_config_generator.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='nginx:\n  exporter_image: nginx-exporter')
    @patch('prometheus_generation.app.services.prometheus_config_generator.yaml.safe_load')
    def test_generate_config_scrape_timing_from_signature(self, mock_yaml_load, mock_file, mock_exists):
        """scrape_interval / scrape_timeout берутся из signatures при наличии."""
        mock_exists.return_value = True
        mock_yaml_load.return_value = {
            "nginx": {
                "exporter_image": "nginx-exporter",
                "exporter_port": 9100,
                "scrape_interval": "20s",
                "scrape_timeout": "45s",
            }
        }

        generator = PrometheusConfigGenerator()

        container_data = {
            "info": {"Name": "/test-container", "NetworkSettings": {}},
            "classification": {"result": [["nginx", 0.9]]}
        }

        with patch.object(generator.env_generator, 'generate_env_vars', return_value={}):
            with patch.object(generator.env_generator, 'get_container_network', return_value=None):
                result = generator.generate_config(container_data, "localhost:8080")

        assert result is not None
        scrape = result["config"]["scrape_config"]
        assert scrape["scrape_interval"] == "20s"
        assert scrape["scrape_timeout"] == "45s"

    @patch('prometheus_generation.app.services.prometheus_config_generator.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='nginx:\n  exporter_image: nginx-exporter')
    @patch('prometheus_generation.app.services.prometheus_config_generator.yaml.safe_load')
    def test_generate_config_default_scrape_timeout(self, mock_yaml_load, mock_file, mock_exists):
        """Без scrape_timeout в сигнатуре используется увеличенный дефолт для медленных /metrics."""
        mock_exists.return_value = True
        mock_yaml_load.return_value = {
            "nginx": {
                "exporter_image": "nginx-exporter",
                "exporter_port": 9100,
            }
        }

        generator = PrometheusConfigGenerator()

        container_data = {
            "info": {"Name": "/tc", "NetworkSettings": {}},
            "classification": {"result": [["nginx", 0.9]]}
        }

        with patch.object(generator.env_generator, 'generate_env_vars', return_value={}):
            with patch.object(generator.env_generator, 'get_container_network', return_value=None):
                result = generator.generate_config(container_data, "host")

        assert result["config"]["scrape_config"]["scrape_timeout"] == "30s"


class TestMainPrometheusConfig:
    """Тесты для MainPrometheusConfig."""

    @patch('prometheus_generation.app.services.main_config.MinioService')
    def test_init(self, mock_minio_service_class):
        """Тест инициализации MainPrometheusConfig."""
        mock_minio_service = MagicMock()
        mock_minio_service_class.return_value = mock_minio_service
        
        config = MainPrometheusConfig()
        
        assert config.minio_client == mock_minio_service

    @patch('prometheus_generation.app.services.main_config.MinioService')
    def test_add_service_success(self, mock_minio_service_class):
        """Тест успешного добавления сервиса."""
        mock_minio_service = MagicMock()
        mock_minio_service.get_yaml_file.return_value = {"scrape_configs": []}
        mock_minio_service.upload_file.return_value = True
        mock_minio_service_class.return_value = mock_minio_service
        
        config = MainPrometheusConfig()
        scrape_config = {"job_name": "test"}
        target = [{"targets": ["localhost:9090"]}]
        
        result = config.add_service(scrape_config, target, "test-target")
        
        assert result is True

    @patch('prometheus_generation.app.services.main_config.MinioService')
    def test_remove_service_success(self, mock_minio_service_class):
        """Тест успешного удаления сервиса."""
        mock_minio_service = MagicMock()
        mock_minio_service.get_yaml_file.return_value = {
            "scrape_configs": [{"job_name": "test"}]
        }
        mock_minio_service.upload_file.return_value = True
        mock_minio_service_class.return_value = mock_minio_service
        
        config = MainPrometheusConfig()
        result = config.remove_service("test", "test-target")
        
        assert result is True

    @patch('prometheus_generation.app.services.main_config.MinioService')
    def test_get_full_config(self, mock_minio_service_class):
        """Тест получения полной конфигурации."""
        mock_minio_service = MagicMock()
        mock_minio_service.get_yaml_file.return_value = {
            "global": {"scrape_interval": "15s"},
            "scrape_configs": []
        }
        mock_minio_service.list_files.return_value = []
        mock_minio_service_class.return_value = mock_minio_service
        
        config = MainPrometheusConfig()
        result = config.get_full_config()
        
        assert "main_config" in result and "targets" in result
        mc = result["main_config"]
        assert "global" in mc
        assert "scrape_configs" in mc

