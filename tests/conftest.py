import sys
import importlib
from pathlib import Path
from unittest.mock import MagicMock, Mock
from typing import Generator

import pytest
from sqlalchemy.orm import Session


# Добавляем корень репозитория в sys.path, чтобы импортировать пакеты сервисов
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Также добавляем директории сервисов как пакеты верхнего уровня,
# чтобы импорты вида `from app...` корректно резолвились внутри них.
SERVICE_DIRS = [
    ROOT_DIR / "api_agregator",
    ROOT_DIR / "docker_api",
    ROOT_DIR / "docker_classification",
    ROOT_DIR / "prometheus_generation",
    ROOT_DIR / "prometheus_manager",
    ROOT_DIR / "grafana_generation",
    ROOT_DIR / "grafana_manager",
]

for service_path in SERVICE_DIRS:
    if service_path.is_dir():
        if str(service_path) not in sys.path:
            sys.path.insert(0, str(service_path))


def import_service_app(service_name: str):
    """
    Импортирует app модуль сервиса с правильной настройкой алиаса 'app'.
    
    ВАЖНО: Эта функция устанавливает глобальный алиас 'app', который будет
    использоваться последующими импортами. Каждый вызов перезаписывает предыдущий алиас.
    
    Args:
        service_name: Имя сервиса (например, 'docker_api', 'api_agregator')
    
    Returns:
        app объект FastAPI из main модуля сервиса
    """
    # Очищаем кеш модулей, связанных с предыдущим сервисом
    # Удаляем все модули, начинающиеся с 'app.'
    modules_to_remove = [key for key in list(sys.modules.keys()) if key.startswith("app.")]
    for key in modules_to_remove:
        del sys.modules[key]
    
    # Также удаляем сам модуль 'app', если он существует
    if "app" in sys.modules:
        del sys.modules["app"]
    
    # Импортируем app модуль сервиса
    app_module = importlib.import_module(f"{service_name}.app")
    # Устанавливаем алиас 'app' на этот модуль
    sys.modules["app"] = app_module
    # Теперь импортируем main модуль, который использует 'from app...'
    main_module = importlib.import_module(f"{service_name}.app.main")
    return main_module.app


# Фикстуры для моков

@pytest.fixture
def mock_db_session():
    """Фикстура для мока сессии базы данных."""
    session = MagicMock(spec=Session)
    session.query = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.refresh = MagicMock()
    session.delete = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    return session


@pytest.fixture
def mock_redis_client():
    """Фикстура для мока Redis клиента."""
    client = MagicMock()
    client.pipeline = MagicMock(return_value=MagicMock())
    client.keys = MagicMock(return_value=[])
    client.get = MagicMock(return_value=None)
    client.set = MagicMock(return_value=True)
    client.delete = MagicMock(return_value=0)
    client.hgetall = MagicMock(return_value={})
    client.hset = MagicMock(return_value=True)
    client.hdel = MagicMock(return_value=0)
    return client


@pytest.fixture
def mock_docker_containers():
    """Фикстура для мока DockerContainers."""
    containers = MagicMock()
    containers.get_containers = MagicMock(return_value={})
    containers.get_container = MagicMock(return_value=None)
    containers.client = MagicMock()
    return containers


@pytest.fixture
def mock_api_gateway():
    """Фикстура для мока APIGateway."""
    gateway = MagicMock()
    gateway.make_request = MagicMock(return_value={})
    return gateway


@pytest.fixture
def mock_minio_service():
    """Фикстура для мока MinioService."""
    service = MagicMock()
    service.upload_file = MagicMock(return_value=True)
    service.get_file = MagicMock(return_value=None)
    service.delete_file = MagicMock(return_value=True)
    service.s3_client = MagicMock()
    return service


@pytest.fixture
def mock_docker_client():
    """Фикстура для мока Docker клиента."""
    client = MagicMock()
    client.containers = MagicMock()
    client.containers.list = MagicMock(return_value=[])
    client.containers.get = MagicMock()
    client.containers.run = MagicMock()
    client.images = MagicMock()
    client.volumes = MagicMock()
    client.networks = MagicMock()
    return client



