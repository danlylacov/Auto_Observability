import sys
from pathlib import Path

from fastapi.testclient import TestClient


SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from app import main as main_module  # type: ignore[import]
from app.services.templste_loader import GrafanaTemplateLoader  # type: ignore[import]


def test_root_and_health():
    client = TestClient(main_module.app)
    resp_root = client.get("/")
    assert resp_root.status_code == 200
    data = resp_root.json()
    assert "Grafana Generation API" in data.get("message", "")

    resp_health = client.get("/health")
    assert resp_health.status_code == 200
    assert resp_health.json() == {"status": "healthy"}


def test_templates_yml_get():
    client = TestClient(main_module.app)
    r = client.get("/api/v1/grafana/templates_yml")
    assert r.status_code == 200
    body = r.json()
    assert "content" in body
    assert isinstance(body["content"], str)
    assert len(body["content"]) > 0
    assert "grafana_dashboard_id" in body["content"]


def test_load_templates_index_from_unified_signatures():
    loader = GrafanaTemplateLoader()
    idx = loader.load_templates_index()
    assert idx.get("postgresql") == {"dashboard_id": 9628}
    assert idx.get("mongodb") == {"dashboard_id": 7353}


def test_templates_yml_put_invalid_yaml():
    client = TestClient(main_module.app)
    r = client.put(
        "/api/v1/grafana/templates_yml",
        content="this is not: valid: yaml: [[",
        headers={"Content-Type": "text/plain; charset=utf-8"},
    )
    assert r.status_code == 400

