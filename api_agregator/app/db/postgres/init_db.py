"""Database initialization module."""

import logging

from app.db.postgres.database import Base, engine

logger = logging.getLogger(__name__)


def init_db() -> None:
    """
    Создание всех таблиц в базе данных.

    Создает все таблицы, определенные в моделях SQLAlchemy.
    """
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully!")


if __name__ == "__main__":
    init_db()
