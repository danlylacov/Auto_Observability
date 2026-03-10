"""Application configuration module."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Настройки приложения.

    Загружает параметры из переменных окружения или использует значения по умолчанию.
    """

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    debug: bool = False

    class Config:
        """Конфигурация Pydantic."""
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings():
    """
    Получение настроек приложения.

    Returns:
        Settings: Экземпляр настроек
    """
    return Settings()


settings = get_settings()
