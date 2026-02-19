import redis
import os
from dotenv import load_dotenv
from typing import Optional


class RedisConnection:
    """Класс для подключения к Redis"""

    def __init__(self) -> None:
        load_dotenv()
        self.host = os.getenv('REDIS_HOST', '127.0.0.1')
        self.port = int(os.getenv('REDIS_PORT', 6379))  # Приводим к int
        self.db = int(os.getenv('REDIS_DB', 0))  # Приводим к int
        self.password = os.getenv('REDIS_PASSWORD', None)
        self.decode_responses = os.getenv('REDIS_DECODE_RESPONSES', 'True').lower() == 'true'

        self._client: Optional[redis.Redis] = None

    def connect(self) -> redis.Redis:
        """Создание подключения к Redis"""
        try:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=self.decode_responses,
                socket_connect_timeout=5,  # Таймаут подключения
                socket_timeout=5,  # Таймаут операций
            )
            self._client.ping()
            print(f"Успешное подключение к Redis: {self.host}:{self.port}/{self.db}")
            return self._client
        except redis.ConnectionError as e:
            print(f"Ошибка подключения к Redis: {e}")
            raise
        except Exception as e:
            print(f"Непредвиденная ошибка: {e}")
            raise

    def get_client(self) -> redis.Redis:
        """Получение клиента (создает новое подключение если его нет)"""
        if self._client is None:
            self.connect()
        return self._client

    def close(self) -> None:
        """Закрытие подключения"""
        if self._client:
            self._client.close()
            self._client = None
            print("Подключение к Redis закрыто")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Автоматическое закрытие при выходе из контекста"""
        self.close()
