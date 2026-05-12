"""Tests: Redis container host keys must match API host_id (UUID), not display host_name."""

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_MOD_PATH = _ROOT / "api_agregator" / "app" / "services" / "prometheus_scrape_resolution.py"
_spec = importlib.util.spec_from_file_location("prometheus_scrape_resolution", _MOD_PATH)
assert _spec and _spec.loader
_pr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pr)

find_exporter_container_data = _pr.find_exporter_container_data
host_port_from_redis_inspect = _pr.host_port_from_redis_inspect
redis_host_key_for_api_host_id = _pr.redis_host_key_for_api_host_id


def test_redis_host_key_prefers_host_id_over_display_name():
    cdata = {"host_id": "uuid-host-1", "host_name": "My Docker Server"}
    assert redis_host_key_for_api_host_id(cdata) == "uuid-host-1"


def test_find_exporter_finds_by_host_id_when_host_name_differs():
    """Regression: host_name was compared first, so UUID from API never matched display name."""
    all_c = {
        "c1": {
            "info": {
                "Name": "/my-mongo-exporter",
                "NetworkSettings": {
                    "Ports": {"9216/tcp": [{"HostIp": "0.0.0.0", "HostPort": "9100"}]},
                },
            },
            "host_id": "db-uuid-99",
            "host_name": "server-display-name",
        }
    }
    found = find_exporter_container_data(
        workload_container_name="my-mongo",
        host_id="db-uuid-99",
        all_containers=all_c,
    )
    assert found is not None
    assert host_port_from_redis_inspect(found, 9216) == 9100


def test_find_exporter_skips_wrong_host_uuid():
    all_c = {
        "c1": {
            "info": {"Name": "/my-mongo-exporter", "NetworkSettings": {"Ports": {}}},
            "host_id": "other-uuid",
            "host_name": "x",
        }
    }
    assert (
        find_exporter_container_data(
            workload_container_name="my-mongo",
            host_id="db-uuid-99",
            all_containers=all_c,
        )
        is None
    )
