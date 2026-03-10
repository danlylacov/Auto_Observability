"""Host PostgreSQL model module."""

import uuid

from sqlalchemy import Column, String, Integer

from app.db.postgres.database import Base


class Host(Base):
    """
    Модель хоста в базе данных.

    Хранит информацию о целевых хостах для мониторинга.
    """

    __tablename__ = "hosts"

    id = Column(
        String(255), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name = Column(String(255))
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
