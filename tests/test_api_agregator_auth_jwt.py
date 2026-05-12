"""Тесты JWT middleware и матрицы прав api_agregator."""

import sys
from datetime import datetime, timedelta, timezone

import api_agregator.app as _api_app_module

sys.modules["app"] = _api_app_module

import jwt
import pytest
from fastapi.testclient import TestClient

from api_agregator.app.auth.permissions import is_request_allowed


def test_permissions_user_get_only():
    assert is_request_allowed("GET", "/api/v1/hosts/get", "user")
    assert not is_request_allowed("POST", "/api/v1/hosts/add", "user")


def test_permissions_dev_hosts_mutations():
    assert is_request_allowed("POST", "/api/v1/hosts/add", "dev")
    assert not is_request_allowed("PATCH", "/api/v1/containers/update_containers", "dev")
    assert is_request_allowed("GET", "/api/v1/containers/containers", "dev")


def test_permissions_dev_prometheus_blocked():
    assert not is_request_allowed("POST", "/api/v1/prometheus/generate_config", "dev")
    assert not is_request_allowed("PATCH", "/api/v1/prometheus/update_signature", "dev")


def test_permissions_maintainer_all():
    assert is_request_allowed("POST", "/api/v1/prometheus/generate_config", "maintainer")
    assert is_request_allowed("DELETE", "/api/v1/grafana/imported_dashboards/1", "maintainer")


def _make_token(*, secret: str, role: str, sub: str = "tuser") -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=1)
    return jwt.encode(
        {"sub": sub, "role": role, "iat": int(now.timestamp()), "exp": int(exp.timestamp())},
        secret,
        algorithm="HS256",
    )


@pytest.fixture
def jwt_secret(monkeypatch):
    monkeypatch.delenv("SKIP_JWT_AUTH", raising=False)
    monkeypatch.setenv("JWT_SECRET", "pytest-jwt-secret-key")
    from api_agregator.app.config import get_settings

    get_settings.cache_clear()
    yield "pytest-jwt-secret-key"
    get_settings.cache_clear()


def test_middleware_401_without_token(jwt_secret):
    from unittest.mock import patch

    from api_agregator.app.main import app

    with patch("api_agregator.app.main.apply_schema_patches"):
        with TestClient(app) as client:
            r = client.get("/api/v1/hosts/get")
    assert r.status_code == 401


def test_middleware_403_user_post_hosts(jwt_secret):
    from unittest.mock import patch

    from api_agregator.app.main import app

    token = _make_token(secret=jwt_secret, role="user")
    with patch("api_agregator.app.main.apply_schema_patches"):
        with TestClient(app) as client:
            r = client.post(
                "/api/v1/hosts/add",
                params={"name": "a", "host": "h", "port": 22},
                headers={"Authorization": f"Bearer {token}"},
            )
    assert r.status_code == 403


def test_middleware_403_dev_update_containers(jwt_secret):
    from unittest.mock import patch

    from api_agregator.app.main import app

    token = _make_token(secret=jwt_secret, role="dev")
    with patch("api_agregator.app.main.apply_schema_patches"):
        with TestClient(app) as client:
            r = client.patch(
                "/api/v1/containers/update_containers",
                headers={"Authorization": f"Bearer {token}"},
            )
    assert r.status_code == 403
