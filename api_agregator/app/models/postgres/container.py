from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, DateTime, JSON, Index
from sqlalchemy.orm import relationship

from app.db.postgres.database import Base


class Container(Base):
    __tablename__ = "containers"

    id = Column(String(255), primary_key=True)

    name = Column(String(255), nullable=False, index=True)
    image = Column(String(500))
    status = Column(String(50), default="unknown", index=True)

    stack = Column(String(100), index=True)
    classification_score = Column(JSON)

    docker_info = Column(JSON, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    prometheus_configs = relationship(
        "PrometheusConfig",
        back_populates="container",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_container_name", "name"),
        Index("idx_container_stack", "stack"),
        Index("idx_container_status", "status"),
        Index("idx_container_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Container(id={self.id}, name={self.name}, stack={self.stack})>"
