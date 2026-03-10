from typing import Optional

from pydantic import BaseModel, Field


class ItemBase(BaseModel):
    """
    Базовая модель элемента.

    Attributes:
        name: Название элемента
        description: Описание элемента
        price: Цена элемента
    """

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    price: float = Field(..., gt=0)


class ItemCreate(ItemBase):
    """Модель для создания элемента."""


class ItemUpdate(BaseModel):
    """
    Модель для обновления элемента.

    Attributes:
        name: Новое название элемента
        description: Новое описание элемента
        price: Новая цена элемента
    """

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    price: Optional[float] = Field(None, gt=0)


class ItemResponse(ItemBase):
    """
    Модель ответа с элементом.

    Attributes:
        id: Идентификатор элемента
    """

    id: int

    class Config:
        """Конфигурация Pydantic."""
        from_attributes = True