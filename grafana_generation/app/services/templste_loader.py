import hashlib
import json
import os
import uuid
from copy import deepcopy
from typing import Any

import requests
import yaml


class GrafanaTemplateLoader:
    """Загрузка дашбордов с grafana.com и подготовка под локальный источник Prometheus."""

    GRAFANA_COM_API = "https://grafana.com/api/dashboards"

    def __init__(self, cache_dir: str = "./.dashboard_cache", templates_path: str | None = None):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        if templates_path is None:
            if os.path.exists("/app/grafana_templates.yml"):
                templates_path = "/app/grafana_templates.yml"
            else:
                root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                templates_path = os.path.join(root, "grafana_templates.yml")
        self.templates_path = templates_path

    def load_templates_index(self) -> dict[str, Any]:
        """Каталог ключ → { dashboard_id, … } из grafana_templates.yml."""
        try:
            with open(self.templates_path, encoding="utf-8") as f:
                idx = yaml.safe_load(f)
            return idx or {}
        except FileNotFoundError:
            return {}

    def fetch_dashboard_json(self, dashboard_id: int, revision: int | None = None) -> dict[str, Any]:
        """
        Возвращает JSON дашборда (как в ответе grafana.com: часто ключ \"dashboard\").
        """
        if revision is None:
            meta_url = f"{self.GRAFANA_COM_API}/{dashboard_id}"
            resp = requests.get(meta_url, timeout=30)
            if resp.status_code != 200:
                raise RuntimeError(f"Не удалось получить метаданные: {resp.text}")
            revision = int(resp.json()["revision"])

        cache_key = f"{dashboard_id}_r{revision}"
        cache_path = os.path.join(self.cache_dir, f"{cache_key}.json")

        if os.path.exists(cache_path):
            with open(cache_path, encoding="utf-8") as f:
                return json.load(f)

        download_url = f"{self.GRAFANA_COM_API}/{dashboard_id}/revisions/{revision}/download"
        resp = requests.get(download_url, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"Не удалось скачать дашборд: {resp.text}")

        dashboard_raw = resp.json()
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(dashboard_raw, f, indent=2)
        return dashboard_raw

    @staticmethod
    def unwrap_dashboard_payload(payload: dict[str, Any]) -> dict[str, Any]:
        """
        Скаченный объект может быть {\"dashboard\": {...}, \"meta\": ...} или сразу дашборд.
        """
        if "dashboard" in payload and isinstance(payload["dashboard"], dict):
            return deepcopy(payload["dashboard"])
        return deepcopy(payload)

    @staticmethod
    def rewrite_prometheus_datasources(element: Any, ds_uid: str) -> None:
        """
        Рекурсивно подменить ссылки Prometheus на нужный UID.
        Поля \"datasource\" встречаются в panels, templating, annotations, transformations.
        """
        mixed_aliases = frozenset(
            {"mixed", "-- mixed --", "__mixed__", "datasourcemixed"}
        )

        def norm_ds_ref(ref: Any) -> dict[str, str] | Any:
            if ref is None:
                return {"type": "prometheus", "uid": ds_uid}
            if isinstance(ref, str):
                s = ref.strip()
                if s in ("${DS_PROMETHEUS}", "$DS_PROMETHEUS"):
                    # Grafana.com input placeholder becomes unresolved after removing __inputs.
                    return {"type": "prometheus", "uid": ds_uid}
                if s.startswith("$") or s.startswith("${"):
                    return ref  # Grafana template variable (${datasource})
                if ref.strip().lower() in mixed_aliases:
                    return ref
                return {"type": "prometheus", "uid": ds_uid}
            if isinstance(ref, dict):
                if ((ref.get("type") or "").lower() == "mixed") or ref.get("uid") == "__mixed__":
                    return ref
                new_ref = dict(ref)
                new_ref["type"] = "prometheus"
                new_ref["uid"] = ds_uid
                return new_ref
            return ref

        def walk(o: Any) -> None:
            if isinstance(o, dict):
                if "datasource" in o:
                    o["datasource"] = norm_ds_ref(o["datasource"])
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for it in o:
                    walk(it)

        walk(element)

    @staticmethod
    def patch_mongodb_7353_templating(dash: dict[str, Any]) -> None:
        """
        Normalize known broken variables from grafana.com dashboard 7353.
        - cluster variable should have values from mongodb jobs
        - host variable should resolve instances from those jobs
        """
        templating = (dash.get("templating") or {}).get("list")
        if not isinstance(templating, list):
            return
        for var in templating:
            if not isinstance(var, dict):
                continue
            name = var.get("name")
            if name == "cluster":
                var["query"] = 'label_values(up{job=~".*_mongodb"}, job)'
                var["includeAll"] = True
                var["allValue"] = ".*"
            elif name == "host":
                var["query"] = 'label_values(up{job=~".*_mongodb"}, instance)'
                var["includeAll"] = False


    def prepare_for_import(
        self,
        dashboard: dict[str, Any],
        ds_uid: str,
        instance_suffix: str | None = None,
        title_prefix: str | None = None,
    ) -> dict[str, Any]:
        dash = self.unwrap_dashboard_payload(dashboard)

        dash.pop("__inputs", None)
        dash.pop("__requires", None)
        dash.pop("id", None)
        dash["version"] = 1

        if instance_suffix is None:
            instance_suffix = hashlib.sha256(uuid.uuid4().bytes).hexdigest()[:8]

        original_uid = dash.get("uid") or "dash"
        dash["uid"] = f"{original_uid}-{instance_suffix}"[:40]

        if title_prefix:
            dash["title"] = f"{title_prefix}: {dash.get('title', 'Dashboard')}"
        else:
            dash["title"] = f"{dash.get('title', 'Dashboard')} [{instance_suffix}]"

        self.rewrite_prometheus_datasources(dash, ds_uid)
        if int(dash.get("gnetId") or 0) == 7353:
            self.patch_mongodb_7353_templating(dash)

        # Удалить возможные временные ключи Grafana.com
        if "meta" in dash:
            dash.pop("meta", None)

        return dash
