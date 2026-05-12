"""Идемпотентные правки схемы БД без Alembic (добавление колонок к существующим таблицам)."""

import logging

from sqlalchemy import text

from app.db.postgres.database import engine

logger = logging.getLogger(__name__)


def apply_schema_patches() -> None:
    """
    Применить недостающие объекты схемы. Безопасно вызывать при каждом старте приложения.
    """
    if engine.dialect.name != "postgresql":
        return

    with engine.begin() as conn:
        table = conn.execute(
            text(
                """
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = current_schema()
                  AND table_name = 'grafana_imported_dashboards'
                LIMIT 1
                """
            )
        ).scalar_one_or_none()
        if table is None:
            return

        col = conn.execute(
            text(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = 'grafana_imported_dashboards'
                  AND column_name = 'prometheus_config_id'
                LIMIT 1
                """
            )
        ).scalar_one_or_none()

        if col is None:
            logger.info(
                "Applying schema patch: add grafana_imported_dashboards.prometheus_config_id"
            )
            conn.execute(
                text(
                    """
                    ALTER TABLE grafana_imported_dashboards
                    ADD COLUMN prometheus_config_id INTEGER
                    REFERENCES prometheus_configs (id)
                    """
                )
            )

        logger.info(
            "Ensuring partial unique index uq_grafana_imported_prometheus_config_id exists"
        )
        conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_grafana_imported_prometheus_config_id
                ON grafana_imported_dashboards (prometheus_config_id)
                WHERE prometheus_config_id IS NOT NULL
                """
            )
        )
