from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, DateTime, JSON, ForeignKey, Index
)
from sqlalchemy.orm import relationship

from app.db.postgres.database import Base


class PrometheusConfig(Base):
    __tablename__ = "prometheus_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    container_id = Column(
        String(255),
        ForeignKey("containers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    container_name = Column(String(255), index=True)
    stack = Column(String(100), nullable=False, index=True)

    exporter_image = Column(String(500))
    exporter_port = Column(Integer)
    target_address = Column(String(255))
    job_name = Column(String(255))

    minio_bucket = Column(String(100))
    minio_file_path = Column(String(500))

    status = Column(String(50), default="active", index=True)
    version = Column(Integer, default=1)

    config_metadata = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    container = relationship("Container", back_populates="prometheus_configs")

    __table_args__ = (
        Index("idx_config_container_id", "container_id"),
        Index("idx_config_stack", "stack"),
        Index("idx_config_status", "status"),
        Index("idx_config_created_at", "created_at"),
        Index("idx_config_container_status", "container_id", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<PrometheusConfig(id={self.id}, container_id={self.container_id}, "
            f"stack={self.stack}, status={self.status})>"
        )
