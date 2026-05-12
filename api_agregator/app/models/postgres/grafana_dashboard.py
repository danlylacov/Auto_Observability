"""Модель импортированного дашборда Grafana."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, text

from app.db.postgres.database import Base


class GrafanaDashboard(Base):
    """
    Запись об импортированном в Grafana дашборде (локальный учёт + удаление).
    """

    # Отдельное имя: в БД уже могла быть legacy-таблица grafana_dashboards с другой схемой.
    __tablename__ = "grafana_imported_dashboards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uid = Column(String(128), nullable=False, unique=True, index=True)
    title = Column(String(512))
    template_key = Column(String(128), index=True)
    source_dashboard_id = Column(Integer)

    slug = Column(String(512))

    url = Column(String(1024))

    prometheus_config_id = Column(Integer, ForeignKey("prometheus_configs.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_grafana_imported_template_key", "template_key"),
        Index(
            "uq_grafana_imported_prometheus_config_id",
            "prometheus_config_id",
            unique=True,
            postgresql_where=text("prometheus_config_id IS NOT NULL"),
        ),
    )

    def __repr__(self) -> str:
        return f"<GrafanaDashboard(id={self.id}, uid={self.uid}, title={self.title!r})>"
