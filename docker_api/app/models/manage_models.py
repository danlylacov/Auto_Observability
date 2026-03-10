from typing import Optional, Dict

from pydantic import BaseModel, Field


class Container(BaseModel):
    """
    Модель контейнера с идентификатором.

    Attributes:
        id: Идентификатор контейнера
    """

    id: str = Field(..., max_length=500)


class Volume(BaseModel):
    """
    Модель тома.

    Attributes:
        name: Имя тома
    """

    name: str = Field(None, max_length=500)


class FullContainer(BaseModel):
    """
    Модель контейнера с полными параметрами для запуска.

    Attributes:
        image_name: Имя образа Docker
        command: Команда для запуска
        name: Имя контейнера
        detach: Запуск в фоновом режиме
        ports: Маппинг портов
        volumes: Маппинг томов
        environment: Переменные окружения
        network: Имя сети
    """

    image_name: str = Field(None, max_length=500)
    command: Optional[str] = Field(None, max_length=500)
    name: Optional[str] = Field(None, max_length=500)
    detach: bool = Field(True)
    ports: Optional[Dict[str, int]] = Field(None)
    volumes: Optional[Dict[str, Dict[str, str]]] = Field(None)
    environment: Optional[Dict[str, str]] = Field(None)
    network: Optional[str] = Field(None, max_length=500)
