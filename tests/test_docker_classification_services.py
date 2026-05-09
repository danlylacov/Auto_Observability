"""Тесты для сервисов docker_classification."""

import sys
from unittest.mock import MagicMock, patch, mock_open
import pytest

# Настраиваем алиас 'app' для docker_classification перед импортами
import docker_classification.app as docker_classification_app_module
sys.modules["app"] = docker_classification_app_module

from docker_classification.app.services.docker_clasification import WeightedDiscovery


class TestWeightedDiscovery:
    """Тесты для WeightedDiscovery."""

    @patch('builtins.open', new_callable=mock_open, read_data='''ports:
  "5432":
    tech: "postgresql"
    weight: 100
  "80":
    tech: "nginx"
    weight: 100
env:
  "POSTGRES_*":
    tech: "postgresql"
    weight: 50
images:
  postgres:
    tech: "postgresql"
    weight: 100
  nginx:
    tech: "nginx"
    weight: 100
labels:
  postgres:
    tech: "postgresql"
    weight: 50
''')
    @patch('docker_classification.app.services.docker_clasification.os.path.abspath')
    @patch('docker_classification.app.services.docker_clasification.os.path.dirname')
    @patch('docker_classification.app.services.docker_clasification.os.path.join')
    def test_init_default_path(self, mock_join, mock_dirname, mock_abspath, mock_file):
        """Тест инициализации с путем по умолчанию."""
        mock_dirname.return_value = "/test"
        mock_abspath.return_value = "/test/docker_clasification.py"
        mock_join.return_value = "/test/signatures.yml"
        
        discovery = WeightedDiscovery()
        
        assert discovery.rules is not None
        assert discovery.threshold == 50
        mock_file.assert_called_once()

    @patch('builtins.open', new_callable=mock_open, read_data='''ports: {}
env: {}
images:
  postgres:
    tech: "postgresql"
    weight: 100
labels: {}
''')
    def test_init_custom_path(self, mock_file):
        """Тест инициализации с кастомным путем."""
        discovery = WeightedDiscovery(rules_path="/custom/path/signatures.yml")
        
        assert discovery.rules is not None
        assert discovery.threshold == 50
        mock_file.assert_called_once_with("/custom/path/signatures.yml", 'r', encoding='utf-8')

    @patch('builtins.open', new_callable=mock_open, read_data='''ports:
  "5432":
    tech: "postgresql"
    weight: 100
  "80":
    tech: "nginx"
    weight: 100
env:
  "POSTGRES_*":
    tech: "postgresql"
    weight: 50
images:
  postgres:
    tech: "postgresql"
    weight: 100
  nginx:
    tech: "nginx"
    weight: 100
labels:
  postgres:
    tech: "postgresql"
    weight: 50
''')
    @patch('docker_classification.app.services.docker_clasification.os.path.abspath')
    @patch('docker_classification.app.services.docker_clasification.os.path.dirname')
    @patch('docker_classification.app.services.docker_clasification.os.path.join')
    def test_classify_container_by_image(self, mock_join, mock_dirname, mock_abspath, mock_file):
        """Тест классификации контейнера по образу."""
        mock_dirname.return_value = "/test"
        mock_abspath.return_value = "/test/docker_clasification.py"
        mock_join.return_value = "/test/signatures.yml"
        
        discovery = WeightedDiscovery()
        
        result = discovery.classify_container(
            labels={},
            envs=[],
            image="postgres:14",
            ports=[]
        )
        
        assert len(result) > 0
        assert result[0][0] == "postgresql"
        assert result[0][1] >= discovery.threshold

    @patch('builtins.open', new_callable=mock_open, read_data='''ports:
  "5432":
    tech: "postgresql"
    weight: 100
  "80":
    tech: "nginx"
    weight: 100
env: {}
images: {}
labels: {}
''')
    @patch('docker_classification.app.services.docker_clasification.os.path.abspath')
    @patch('docker_classification.app.services.docker_clasification.os.path.dirname')
    @patch('docker_classification.app.services.docker_clasification.os.path.join')
    def test_classify_container_by_ports(self, mock_join, mock_dirname, mock_abspath, mock_file):
        """Тест классификации контейнера по портам."""
        mock_dirname.return_value = "/test"
        mock_abspath.return_value = "/test/docker_clasification.py"
        mock_join.return_value = "/test/signatures.yml"
        
        discovery = WeightedDiscovery()
        
        # Проверяем что правила загружены правильно
        assert discovery.rules is not None
        assert 'ports' in discovery.rules
        
        result = discovery.classify_container(
            labels={},
            envs=[],
            image="unknown:latest",
            ports=["5432", "5432/tcp"]
        )
        
        assert len(result) > 0
        assert result[0][0] == "postgresql"

    @patch('builtins.open', new_callable=mock_open, read_data='''ports: {}
env:
  "POSTGRES_DB":
    tech: "postgresql"
    weight: 50
images: {}
labels: {}
''')
    @patch('docker_classification.app.services.docker_clasification.os.path.abspath')
    @patch('docker_classification.app.services.docker_clasification.os.path.dirname')
    @patch('docker_classification.app.services.docker_clasification.os.path.join')
    def test_classify_container_by_env(self, mock_join, mock_dirname, mock_abspath, mock_file):
        """Тест классификации контейнера по переменным окружения."""
        mock_dirname.return_value = "/test"
        mock_abspath.return_value = "/test/docker_clasification.py"
        mock_join.return_value = "/test/signatures.yml"
        
        discovery = WeightedDiscovery()
        
        # Проверяем что правила загружены правильно
        assert discovery.rules is not None
        assert 'env' in discovery.rules
        
        result = discovery.classify_container(
            labels={},
            envs=["POSTGRES_DB=mydb", "POSTGRES_USER=user"],
            image="unknown:latest",
            ports=[]
        )
        
        # POSTGRES_DB должен совпадать с "POSTGRES_DB=mydb"
        assert len(result) > 0
        assert result[0][0] == "postgresql"

    @patch('builtins.open', new_callable=mock_open, read_data='''ports: {}
env: {}
images: {}
labels:
  "com.example.service":
    tech: "postgresql"
    weight: 50
''')
    @patch('docker_classification.app.services.docker_clasification.os.path.abspath')
    @patch('docker_classification.app.services.docker_clasification.os.path.dirname')
    @patch('docker_classification.app.services.docker_clasification.os.path.join')
    def test_classify_container_by_labels(self, mock_join, mock_dirname, mock_abspath, mock_file):
        """Тест классификации контейнера по меткам."""
        mock_dirname.return_value = "/test"
        mock_abspath.return_value = "/test/docker_clasification.py"
        mock_join.return_value = "/test/signatures.yml"
        
        discovery = WeightedDiscovery()
        
        result = discovery.classify_container(
            labels={"com.example.service": "postgres"},
            envs=[],
            image="unknown:latest",
            ports=[]
        )
        
        assert len(result) > 0
        assert result[0][0] == "postgresql"

    @patch('builtins.open', new_callable=mock_open, read_data='''ports: {}
env: {}
images: {}
labels: {}
''')
    @patch('docker_classification.app.services.docker_clasification.os.path.abspath')
    @patch('docker_classification.app.services.docker_clasification.os.path.dirname')
    @patch('docker_classification.app.services.docker_clasification.os.path.join')
    def test_classify_container_no_match(self, mock_join, mock_dirname, mock_abspath, mock_file):
        """Тест классификации контейнера без совпадений."""
        mock_dirname.return_value = "/test"
        mock_abspath.return_value = "/test/docker_clasification.py"
        mock_join.return_value = "/test/signatures.yml"
        
        discovery = WeightedDiscovery()
        
        result = discovery.classify_container(
            labels={},
            envs=[],
            image="unknown:latest",
            ports=["9999"]
        )
        
        # Результат должен быть отсортирован по баллам
        assert isinstance(result, list)
        # Если нет совпадений, результат должен быть пустым
        assert len(result) == 0

