"""Связь записей GrafanaDashboard с конфигом Prometheus (FK + legacy по заголовку)."""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.models.postgres.grafana_dashboard import GrafanaDashboard

_TITLE_INSTANCE_RE = re.compile(r"\[([^\]]+)\]\s*$")


def grafana_instance_suffix(container_name: str | None) -> str:
    """Тот же суффикс, что и при импорте дашборда (instance_suffix из имени контейнера)."""
    base = (container_name or "").lstrip("/")
    return re.sub(r"[^a-zA-Z0-9_-]", "-", base)


def load_grafana_dashboard_link_index(db: Session) -> tuple[set[int], set[str]]:
    """
    Возвращает:
    - множество prometheus_config.id, для которых в БД есть дашборд с FK;
    - множество суффиксов из заголовка `... [suffix]` для строк без FK (импорт до появления колонки).
    """
    dash_cfg_ids: set[int] = set()
    legacy_suffixes: set[str] = set()
    for d in db.query(GrafanaDashboard).all():
        if d.prometheus_config_id is not None:
            dash_cfg_ids.add(int(d.prometheus_config_id))
            continue
        m = _TITLE_INSTANCE_RE.search((d.title or "").rstrip())
        if m:
            legacy_suffixes.add(m.group(1))
    return dash_cfg_ids, legacy_suffixes


def has_grafana_dashboard_for_config(
    *,
    prometheus_config_id: int,
    container_name: str | None,
    dash_cfg_ids: set[int],
    legacy_suffixes: set[str],
) -> bool:
    if prometheus_config_id in dash_cfg_ids:
        return True
    return grafana_instance_suffix(container_name) in legacy_suffixes
