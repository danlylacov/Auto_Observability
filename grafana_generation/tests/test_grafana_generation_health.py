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
    assert idx.get("redis") == {"dashboard_id": 11835}
    assert idx.get("mysql") == {"dashboard_id": 14057}
    assert idx.get("mariadb") == {"dashboard_id": 14057}
    assert idx.get("rabbitmq") == {"dashboard_id": 10991}
    assert idx.get("elasticsearch") == {"dashboard_id": 6480}
    assert idx.get("opensearch") == {"dashboard_id": 9732}
    assert idx.get("clickhouse") == {"dashboard_id": 14192}
    assert idx.get("influxdb") == {"dashboard_id": 315}
    assert idx.get("kafka") == {"dashboard_id": 7589}
    assert idx.get("nats") == {"dashboard_id": 2279}


def test_templates_yml_put_invalid_yaml():
    client = TestClient(main_module.app)
    r = client.put(
        "/api/v1/grafana/templates_yml",
        content="this is not: valid: yaml: [[",
        headers={"Content-Type": "text/plain; charset=utf-8"},
    )
    assert r.status_code == 400


def test_rewrite_prometheus_datasource_maps_ds_nats_placeholder():
    payload = {"rows": [{"panels": [{"datasource": "${DS_NATS-PROMETHEUS}"}]}]}
    GrafanaTemplateLoader.rewrite_prometheus_datasources(payload, "prom-uid")
    assert payload["rows"][0]["panels"][0]["datasource"] == {"type": "prometheus", "uid": "prom-uid"}


def test_rewrite_prometheus_datasource_preserves_builtin_grafana_ds():
    payload = {"panels": [{"datasource": {"type": "datasource", "uid": "grafana"}}]}
    GrafanaTemplateLoader.rewrite_prometheus_datasources(payload, "prom-uid")
    assert payload["panels"][0]["datasource"] == {"type": "datasource", "uid": "grafana"}


def test_patch_kafka_7589_templating_uses_broker_info_for_job():
    dash = {
        "templating": {
            "list": [
                {"name": "job", "query": "label_values(kafka_consumergroup_current_offset, job)"},
                {"name": "instance", "query": "old"},
                {"name": "topic", "query": "old"},
            ]
        }
    }
    GrafanaTemplateLoader.patch_kafka_7589_templating(dash)
    job_q = next(v["query"] for v in dash["templating"]["list"] if v["name"] == "job")
    assert job_q == "label_values(kafka_broker_info, job)"
    inst_q = next(v["query"] for v in dash["templating"]["list"] if v["name"] == "instance")
    assert "kafka_broker_info" in inst_q

