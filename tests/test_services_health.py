import contextlib

from fastapi.testclient import TestClient

from api_agregator.app.main import app as api_agregator_app
from docker_api.app.main import app as docker_api_app
from docker_classification.app.main import app as docker_classification_app
from prometheus_generation.app import main as prometheus_generation_main
from prometheus_manager.app.main import app as prometheus_manager_app
from grafana_generation.app import main as grafana_generation_main
from grafana_manager.app.main import app as grafana_manager_app


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
    with _test_client(prometheus_generation_main.app, clear_startup=True) as client:
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
    # grafana_generation.app.main is currently aligned with prometheus_generation
    with _test_client(grafana_generation_main.app, clear_startup=True) as client:
        resp_root = client.get("/")
        assert resp_root.status_code == 200
        data = resp_root.json()
        # Reuse the same expectation as in main module
        assert data.get("message") == "Prometheus Generation API"

        resp_health = client.get("/health")
        assert resp_health.status_code == 200
        assert resp_health.json() == {"status": "healthy"}


def test_grafana_manager_root_and_health():
    with _test_client(grafana_manager_app) as client:
        resp_root = client.get("/")
        assert resp_root.status_code == 200
        data = resp_root.json()
        assert data.get("message") == "Grafana API"

        resp_health = client.get("/health")
        assert resp_health.status_code == 200
        assert resp_health.json() == {"status": "healthy"}

