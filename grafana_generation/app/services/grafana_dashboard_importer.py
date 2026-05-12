"""Импорт / удаление дашбордов через HTTP API Grafana."""

import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)


class GrafanaHttpError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def _normalize_base(url: str) -> str:
    return (url or "").strip().rstrip("/")


class GrafanaDashboardImporter:
    def __init__(self) -> None:
        base = os.getenv("GRAFANA_URL")
        self.base_url = _normalize_base(base or "")
        self.user = os.getenv("GRAFANA_USER", "admin")
        self.password = os.getenv("GRAFANA_PASSWORD", "admin")

    def is_configured(self) -> bool:
        return bool(self.base_url)

    def _prometheus_url(self) -> str:
        return os.getenv("PROMETHEUS_URL", "http://host.docker.internal:9090")

    def ensure_prometheus_datasource(self, ds_uid: str) -> None:
        """Ensure Grafana has Prometheus datasource with expected UID."""
        if not self.base_url:
            raise GrafanaHttpError(503, "GRAFANA_URL is not configured")
        get_url = f"{self.base_url}/api/datasources/uid/{ds_uid}"
        r = requests.get(get_url, auth=(self.user, self.password), timeout=30)
        if r.status_code == 200:
            return
        if r.status_code not in (404,):
            raise GrafanaHttpError(r.status_code, f"Failed to check datasource UID {ds_uid}: {r.text}")

        create_url = f"{self.base_url}/api/datasources"
        payload = {
            "name": "Prometheus",
            "type": "prometheus",
            "access": "proxy",
            "url": self._prometheus_url(),
            "uid": ds_uid,
            "isDefault": True,
            "jsonData": {
                "httpMethod": "POST",
            },
        }
        cr = requests.post(
            create_url,
            json=payload,
            auth=(self.user, self.password),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=60,
        )
        if cr.status_code >= 400:
            raise GrafanaHttpError(cr.status_code, f"Failed to create datasource UID {ds_uid}: {cr.text}")

    def import_dashboard(
        self,
        dashboard_body: dict[str, Any],
        prometheus_ds_uid: str | None = None,
        *,
        overwrite: bool = True,
        folder_id: int | None = None,
        message: str | None = None,
    ) -> dict[str, Any]:
        """
        POST /api/dashboards/db
        dashboard_body должен содержать uid, panels, templating как в сохранении JSON.
        """
        if not self.base_url:
            raise GrafanaHttpError(503, "GRAFANA_URL is not configured")
        if prometheus_ds_uid:
            self.ensure_prometheus_datasource(prometheus_ds_uid)

        payload: dict[str, Any] = {
            "dashboard": dashboard_body,
            "overwrite": overwrite,
            "message": message or "imported via Auto Observability",
        }
        if folder_id is not None:
            payload["folderId"] = folder_id

        url = f"{self.base_url}/api/dashboards/db"
        logger.info("Importing Grafana dashboard %s via %s", dashboard_body.get("title"), url)
        r = requests.post(
            url,
            json=payload,
            auth=(self.user, self.password),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=120,
        )
        try:
            data = r.json() if r.text else {}
        except Exception:
            data = {"detail": r.text}

        if r.status_code >= 400:
            raise GrafanaHttpError(
                r.status_code,
                data.get("message") or data.get("detail") or r.text or r.reason,
            )
        return data

    def delete_dashboard_by_uid(self, uid: str) -> bool:
        """
        DELETE /api/dashboards/uid/{uid}
        Возвращает True если удалено или уже отсутствует.
        """
        if not self.base_url:
            raise GrafanaHttpError(503, "GRAFANA_URL is not configured")

        url = f"{self.base_url}/api/dashboards/uid/{uid}"
        r = requests.delete(url, auth=(self.user, self.password), timeout=60)
        if r.status_code in (404,):
            logger.info("Grafana dashboard uid=%s already absent", uid)
            return True
        if r.status_code >= 400:
            try:
                data = r.json()
                msg = data.get("message") or data.get("detail") or str(data)
            except Exception:
                msg = r.text or r.reason
            raise GrafanaHttpError(r.status_code, msg or r.reason)

        logger.info("Deleted Grafana dashboard uid=%s", uid)
        return True
