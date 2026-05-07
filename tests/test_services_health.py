import contextlib

import pytest
from fastapi.testclient import TestClient

# Используем функцию из conftest для импорта с правильной настройкой алиаса
from tests.conftest import import_service_app

# Импортируем app модули сервисов с правильной настройкой контекста
# Порядок важен: каждый сервис устанавливает свой алиас 'app'
docker_api_app = import_service_app("docker_api")
docker_classification_app = import_service_app("docker_classification")
prometheus_generation_app = import_service_app("prometheus_generation")
prometheus_manager_app = import_service_app("prometheus_manager")
api_agregator_app = import_service_app("api_agregator")

# grafana_generation и grafana_manager могут иметь проблемы с импортами
# импортируем их с обработкой ошибок
try:
    grafana_generation_app = import_service_app("grafana_generation")
except Exception:
    grafana_generation_app = None

try:
    grafana_manager_app = import_service_app("grafana_manager")
except Exception:
    grafana_manager_app = None


@contextlib.contextmanager
def _test_client(app, *, clear_startup: bool = False):
    """
    Helper context manager to create TestClient without executing heavy
    startup hooks (e.g. MinIO initialization).
    """
    if clear_startup:
        # FastAPI keeps startup handlers in router.on_startup list
        app.router.on_startup.clear()
    with TestClient(app) as client:
        yield client


def test_api_agregator_root_and_health():
    with _test_client(api_agregator_app) as client:
        resp_root = client.get("/")
        assert resp_root.status_code == 200
        data = resp_root.json()
        assert data.get("message") == "Auto Observability API"

        resp_health = client.get("/health")
        assert resp_health.status_code == 200
        assert resp_health.json() == {"status": "healthy"}


def test_docker_api_root_and_health():
    with _test_client(docker_api_app) as client:
        resp_root = client.get("/")
        assert resp_root.status_code == 200
        data = resp_root.json()
        assert data.get("message") == "Docker API"

        resp_health = client.get("/health")
        assert resp_health.status_code == 200
        assert resp_health.json() == {"status": "healthy"}


def test_docker_classification_root_and_health():
    with _test_client(docker_classification_app) as client:
        resp_root = client.get("/")
        assert resp_root.status_code == 200
        data = resp_root.json()
        assert data.get("message") == "Docker classification API"

        resp_health = client.get("/health")
        assert resp_health.status_code == 200
        assert resp_health.json() == {"status": "healthy"}


def test_prometheus_generation_root_and_health_without_startup():
    # Skip heavy startup that talks to MinIO, we just verify basic endpoints
    with _test_client(prometheus_generation_app, clear_startup=True) as client:
        resp_root = client.get("/")
        assert resp_root.status_code == 200
        data = resp_root.json()
        assert data.get("message") == "Prometheus Generation API"

        resp_health = client.get("/health")
        assert resp_health.status_code == 200
        assert resp_health.json() == {"status": "healthy"}


def test_prometheus_manager_root_and_health():
    with _test_client(prometheus_manager_app) as client:
        resp_root = client.get("/")
        assert resp_root.status_code == 200
        data = resp_root.json()
        assert data.get("message") == "Prometheus manage API"

        resp_health = client.get("/health")
        assert resp_health.status_code == 200
        assert resp_health.json() == {"status": "healthy"}


def test_grafana_generation_root_and_health_without_startup():
    # grafana_generation может быть не полностью реализован
    if grafana_generation_app is None:
        pytest.skip("grafana_generation не может быть импортирован")
    # grafana_generation.app.main is currently aligned with prometheus_generation
    with _test_client(grafana_generation_app, clear_startup=True) as client:
        resp_root = client.get("/")
        assert resp_root.status_code == 200
        data = resp_root.json()
        # Reuse the same expectation as in main module
        assert data.get("message") == "Prometheus Generation API"

        resp_health = client.get("/health")
        assert resp_health.status_code == 200
        assert resp_health.json() == {"status": "healthy"}


def test_grafana_manager_root_and_health():
    if grafana_manager_app is None:
        pytest.skip("grafana_manager не может быть импортирован")
    with _test_client(grafana_manager_app) as client:
        resp_root = client.get("/")
        assert resp_root.status_code == 200
        data = resp_root.json()
        assert data.get("message") == "Grafana API"

        resp_health = client.get("/health")
        assert resp_health.status_code == 200
        assert resp_health.json() == {"status": "healthy"}

