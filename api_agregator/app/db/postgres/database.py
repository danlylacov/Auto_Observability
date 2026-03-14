"""Database connection and session management."""

import os
from pathlib import Path
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

_api_root = Path(__file__).parent.parent.parent.parent
_env_dev = _api_root / '.env.dev'
_env_file = _api_root / '.env'

if _env_dev.exists():
    load_dotenv(_env_dev, override=True)  # override=True перезаписывает существующие переменные
elif _env_file.exists():
    load_dotenv(_env_file, override=True)
else:
    load_dotenv(override=True)

if not os.getenv("DATABASE_URL"):
    postgres_host = os.getenv("POSTGRES_HOST", "postgres")
    postgres_port = os.getenv("POSTGRES_PORT", "5432")
    postgres_user = os.getenv("POSTGRES_USER", "postgres")
    postgres_password = os.getenv("POSTGRES_PASSWORD", "postgres")
    postgres_db = os.getenv("POSTGRES_DB", "auto_observability")
    
    DATABASE_URL = f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"
else:
    DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Генератор для получения сессии базы данных.

    Yields:
        Session: Сессия базы данных, которая будет закрыта после использования
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
