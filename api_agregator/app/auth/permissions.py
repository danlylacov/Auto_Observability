"""Role-based access for api_agregator routes."""

from __future__ import annotations

VALID_ROLES = frozenset({"maintainer", "admin", "dev", "user"})

# (method, path) — path must match request.url.path (no query string)
_DEV_EXACT_DENY: list[tuple[str, str]] = [
    ("PATCH", "/api/v1/containers/update_containers"),
    ("POST", "/api/v1/containers/container/start"),
    ("POST", "/api/v1/containers/container/stop"),
    ("DELETE", "/api/v1/containers/container/remove"),
    ("POST", "/api/v1/prometheus/generate_config"),
    ("POST", "/api/v1/prometheus/up_exporter"),
    ("PATCH", "/api/v1/prometheus/update_signature"),
    ("POST", "/api/v1/prometheus/main_config/add"),
    ("DELETE", "/api/v1/prometheus/main_config/remove"),
    ("POST", "/api/v1/prometheus/manager/start"),
    ("POST", "/api/v1/prometheus/manager/stop"),
    ("POST", "/api/v1/prometheus/manager/settings"),
    ("POST", "/api/v1/prometheus/manager/config/update"),
    ("PUT", "/api/v1/grafana/templates_yml"),
    ("POST", "/api/v1/grafana/import_dashboard"),
    ("POST", "/api/v1/grafana/manager/start"),
    ("POST", "/api/v1/grafana/manager/stop"),
    ("POST", "/api/v1/grafana/manager/restart"),
]


def _dev_denied(method: str, path: str) -> bool:
    m = method.upper()
    pair = (m, path)
    if pair in _DEV_EXACT_DENY:
        return True
    if m == "DELETE" and path.startswith("/api/v1/grafana/imported_dashboards/"):
        return True
    return False


def is_request_allowed(method: str, path: str, role: str) -> bool:
    if role not in VALID_ROLES:
        return False
    if role in ("maintainer", "admin"):
        return True
    m = method.upper()
    if role == "user":
        return m == "GET"
    if role == "dev":
        if m == "GET":
            return True
        return not _dev_denied(m, path)
    return False
