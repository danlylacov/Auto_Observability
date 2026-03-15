from types import SimpleNamespace

from api_agregator.app.services.api_getaway import APIGateway
from api_agregator.app.services.hosts_service import HostDTO, HostsService
from api_agregator.app.services.update_containers import UpdateContainers


class DummyRedisHosts:
    def __init__(self) -> None:
        self._hosts: dict = {}

    def delete_hosts(self) -> None:
        self._hosts.clear()

    def upload_hosts(self, hosts: dict) -> None:
        self._hosts.update(hosts)

    def get_hosts(self) -> dict:
        return self._hosts


class DummyDBSession:
    def __init__(self, hosts):
        self._hosts = hosts

    def query(self, _model):
        return SimpleNamespace(
            all=lambda: self._hosts,
            filter=lambda *_args, **_kwargs: SimpleNamespace(
                first=lambda: self._hosts[0] if self._hosts else None
            ),
        )


def test_hostdto_base_url():
    dto = HostDTO(host_id="1", name="test", host="localhost", port=8080)
    assert dto.base_url == "http://localhost:8080"


def test_hosts_service_get_all_and_get_by_id(monkeypatch):
    fake_host = SimpleNamespace(id="h1", name="host1", host="127.0.0.1", port=8000)
    db = DummyDBSession([fake_host])

    service = HostsService(db=db)
    service.redis_hosts = DummyRedisHosts()

    all_hosts = service.get_all_hosts_from_db()
    assert len(all_hosts) == 1
    assert all_hosts[0].id == "h1"

    same = service.get_host_by_id("h1")
    assert same is not None
    assert same.name == "host1"


def test_hosts_service_resolve_host_for_docker(monkeypatch):
    fake_host = SimpleNamespace(id="h1", name="host1", host="localhost", port=8000)
    db = DummyDBSession([fake_host])
    service = HostsService(db=db)

    import os

    def fake_exists(path: str) -> bool:
        assert path == "/.dockerenv"
        return False

    monkeypatch.setattr(os.path, "exists", fake_exists)

    assert service._resolve_host_for_docker("localhost") == "localhost"


def test_api_gateway_success(monkeypatch):
    class DummyResponse:
        def __init__(self, status_code, json_data=None, text: str = ""):
            self.status_code = status_code
            self._json = json_data or {}
            self.text = text

        def json(self):
            return self._json

    def fake_request(method, url, data=None, params=None, json=None, timeout=None):
        assert method == "GET"
        assert url.endswith("/ping")
        return DummyResponse(200, {"ok": True})

    import requests

    monkeypatch.setattr(requests, "request", fake_request)

    gw = APIGateway("http://service")
    result = gw.make_request("GET", "/ping")
    assert result == {"ok": True}


def test_update_containers_no_hosts(monkeypatch):
    class DummyDockerContainers:
        def __init__(self):
            self.client = SimpleNamespace(
                pipeline=lambda: SimpleNamespace(execute=lambda: None),
                keys=lambda _pattern=None: [],
                delete=lambda *args, **kwargs: 0,
            )

    monkeypatch.setattr(
        "api_agregator.app.services.update_containers.DockerContainers",
        DummyDockerContainers,
    )

    class DummyHostsService:
        def __init__(self, _db):
            pass

        def get_all_hosts(self):
            return {}

    monkeypatch.setattr(
        "api_agregator.app.services.update_containers.HostsService",
        DummyHostsService,
    )

    updater = UpdateContainers(db=None)
    updater.upload_containers()

