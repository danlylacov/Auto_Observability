"""Database initialization module."""

import logging
import sys

from sqlalchemy.exc import SQLAlchemyError

from app.db.postgres.database import Base, engine
# Import all models to ensure they are registered with Base.metadata
from app.models.postgres import Container, Host, PrometheusConfig

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def init_db() -> None:
    """
    Создание всех таблиц в базе данных.

    Создает все таблицы, определенные в моделях SQLAlchemy.
    Метод идемпотентен - не создает таблицы, если они уже существуют.
    """
    try:
        logger.info("Starting database initialization...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully!")
    except SQLAlchemyError as e:
        logger.error(f"Error initializing database: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during database initialization: {e}")
        raise


if __name__ == "__main__":
    try:
        init_db()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)
