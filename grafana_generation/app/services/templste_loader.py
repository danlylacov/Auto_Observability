import hashlib
import json
import os
import re
import uuid
from copy import deepcopy
from typing import Any

import requests
import yaml


def resolve_observability_signatures_path(explicit: str | None = None) -> str:
    """
    Единый YAML сервисов (Prometheus exporter + Grafana dashboard id) в корне репозитория
    или /app/signatures.yml в Docker.
    """
    if explicit:
        return explicit
    env = (os.getenv("SIGNATURES_PATH") or os.getenv("OBSERVABILITY_SIGNATURES_PATH") or "").strip()
    if env:
        return env
    if os.path.exists("/app/signatures.yml"):
        return "/app/signatures.yml"
    service_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    workspace_root = os.path.dirname(service_root)
    for candidate in (
        os.path.join(workspace_root, "signatures.yml"),
        os.path.join(service_root, "signatures.yml"),
    ):
        if os.path.exists(candidate):
            return candidate
    return os.path.join(workspace_root, "signatures.yml")


class GrafanaTemplateLoader:
    """Загрузка дашбордов с grafana.com и подготовка под локальный источник Prometheus."""

    GRAFANA_COM_API = "https://grafana.com/api/dashboards"

    def __init__(self, cache_dir: str = "./.dashboard_cache", templates_path: str | None = None):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.templates_path = resolve_observability_signatures_path(templates_path)

    def load_templates_index(self) -> dict[str, Any]:
        """
        Индекс шаблонов: ключ стека → { dashboard_id } из корневого signatures.yml
        (поля grafana_dashboard_id или устаревший dashboard_id на сервисе).
        """
        try:
            with open(self.templates_path, encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
        except FileNotFoundError:
            return {}

        idx: dict[str, Any] = {}
        for key, val in raw.items():
            if not isinstance(val, dict):
                continue
            gid = val.get("grafana_dashboard_id")
            if gid is None:
                gid = val.get("dashboard_id")
            if gid is None:
                continue
            try:
                idx[str(key)] = {"dashboard_id": int(gid)}
            except (TypeError, ValueError):
                continue
        return idx

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
                var.pop("regex", None)
                var["refresh"] = 1
            elif name == "host":
                var["query"] = 'label_values(up{job=~".*_mongodb"}, instance)'
                var["includeAll"] = False
                var.pop("regex", None)
                var["refresh"] = 1

    @staticmethod
    def patch_mongodb_7353_compatible_metrics(dash: dict[str, Any]) -> None:
        """
        MongoDB exporters in --compatible-mode expose legacy metric names without mongod_ infix.
        Map dashboard references so panels resolve on both naming schemes by preferring the
        compatible names (same label layout on modern percona exporters).
        """
        subs = (
            ("mongodb_mongod_extra_info_page_faults_total", "mongodb_extra_info_page_faults_total"),
            ("mongodb_mongod_op_counters_total", "mongodb_op_counters_total"),
            ("mongodb_mongod_asserts_total", "mongodb_asserts_total"),
            ("mongodb_mongod_connections", "mongodb_connections"),
        )

        def patch_expr(expr: str) -> str:
            out = expr
            for old, new in subs:
                out = out.replace(old, new)
            return out

        def walk(o: Any) -> None:
            if isinstance(o, dict):
                if isinstance(o.get("expr"), str):
                    o["expr"] = patch_expr(o["expr"])
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for it in o:
                    walk(it)

        walk(dash)

    @staticmethod
    def patch_postgresql_9628(dash: dict[str, Any]) -> None:
        """
        Make dashboard 9628 work outside Kubernetes:
        - replace release label selectors with job selectors
        - normalize variables to Prometheus job/instance labels
        """
        templating = (dash.get("templating") or {}).get("list")
        if isinstance(templating, list):
            for var in templating:
                if not isinstance(var, dict):
                    continue
                name = var.get("name")
                if name == "namespace":
                    var["query"] = 'label_values(pg_up{job=~".*_postgres"}, job)'
                    var["includeAll"] = False
                    # Original 9628 used query_result(); regex expected "release=..." in the string.
                    # label_values() returns plain values — strip regex or variables stay empty.
                    var.pop("regex", None)
                    var["refresh"] = 1
                elif name == "release":
                    var["query"] = 'label_values(pg_up{job=~".*_postgres"}, job)'
                    var["includeAll"] = False
                    var.pop("regex", None)
                    var["refresh"] = 1
                elif name == "instance":
                    var["query"] = 'label_values(pg_up{job="$release"}, instance)'
                    var["includeAll"] = False
                    var.pop("regex", None)
                    var["refresh"] = 1
                elif name == "datname":
                    # Scope databases to the selected exporter (avoids empty multi-job mixes).
                    var["query"] = (
                        'label_values(pg_stat_database_numbackends{job="$release", '
                        'instance="$instance"}, datname)'
                    )
                    var["refresh"] = 1
                    var.pop("regex", None)
                elif name == "mode":
                    var.pop("regex", None)
                elif name == "DS_PROMETHEUS":
                    var.pop("regex", None)

        def patch_expr(expr: str) -> str:
            out = re.sub(r"(\{|,\s*)release=", r"\1job=", expr)
            out = out.replace('kubernetes_namespace="$namespace", ', "")
            out = out.replace(', kubernetes_namespace="$namespace"', "")
            return out

        def walk(o: Any) -> None:
            if isinstance(o, dict):
                if isinstance(o.get("expr"), str):
                    o["expr"] = patch_expr(o["expr"])
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for it in o:
                    walk(it)

        walk(dash)

    def prepare_for_import(
        self,
        dashboard: dict[str, Any],
        ds_uid: str,
        instance_suffix: str | None = None,
        title_prefix: str | None = None,
    ) -> dict[str, Any]:
        dash = self.unwrap_dashboard_payload(dashboard)
        source_dashboard_id = int(dash.get("gnetId") or dash.get("id") or 0)

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
        if source_dashboard_id == 7353:
            self.patch_mongodb_7353_templating(dash)
            self.patch_mongodb_7353_compatible_metrics(dash)
        if source_dashboard_id == 9628:
            self.patch_postgresql_9628(dash)

        # Удалить возможные временные ключи Grafana.com
        if "meta" in dash:
            dash.pop("meta", None)

        return dash
