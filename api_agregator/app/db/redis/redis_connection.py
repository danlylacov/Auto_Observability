"""Redis connection management module."""

import os
import logging
from typing import Optional

import redis
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class RedisConnection:
    """
    Класс для подключения к Redis.

    Предоставляет методы для установления и управления подключением к Redis.
    """

    def __init__(self) -> None:
        """
        Инициализация подключения к Redis.

        Загружает параметры подключения из переменных окружения.
        """
        load_dotenv()
        self.host = os.getenv('REDIS_HOST', '127.0.0.1')
        self.port = int(os.getenv('REDIS_PORT', 6379))
        self.db = int(os.getenv('REDIS_DB', 0))
        self.password = os.getenv('REDIS_PASSWORD', None)
        self.decode_responses = os.getenv('REDIS_DECODE_RESPONSES', 'True').lower() == 'true'

        self._client: Optional[redis.Redis] = None

    def connect(self) -> redis.Redis:
        """
        Создание подключения к Redis.

        Returns:
            redis.Redis: Клиент Redis

        Raises:
            redis.ConnectionError: При ошибке подключения
            Exception: При других ошибках
        """
        try:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=self.decode_responses,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            self._client.ping()
            logger.info(
                "Успешное подключение к Redis: %s:%s/%s",
                self.host, self.port, self.db
            )
            return self._client
        except redis.ConnectionError as e:
            logger.error("Ошибка подключения к Redis: %s", e)
            raise
        except Exception as e:
            logger.error("Непредвиденная ошибка: %s", e)
            raise

    def get_client(self) -> redis.Redis:
        """
        Получение клиента Redis.

        Создает новое подключение, если его нет.

        Returns:
            redis.Redis: Клиент Redis
        """
        if self._client is None:
            self.connect()
        return self._client

    def close(self) -> None:
        """
        Закрытие подключения к Redis.
        """
        if self._client:
            self._client.close()
            self._client = None
            logger.info("Подключение к Redis закрыто")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Автоматическое закрытие при выходе из контекста.

        Args:
            exc_type: Тип исключения
            exc_val: Значение исключения
            exc_tb: Трассировка исключения
        """
        self.close()
