from typing import Dict, List, Any
from pydantic import BaseModel, Field, field_validator


class ClassificationResult(BaseModel):
    """Модель результата классификации"""
    result: List[List[Any]] = Field(..., description="Список кортежей [stack_name, score]")
    
    @field_validator('result')
    @classmethod
    def validate_result(cls, v):
        if not v or len(v) == 0:
            raise ValueError("Результат классификации не может быть пустым")
        if not isinstance(v[0], list) or len(v[0]) < 2:
            raise ValueError("Результат классификации должен содержать кортежи [stack_name, score]")
        return v


class ContainerData(BaseModel):
    """Модель данных контейнера для генерации конфигурации Prometheus
    
    Принимает данные контейнера с информацией и результатами классификации.
    Использует Dict для гибкости, так как структура данных Docker может варьироваться.
    """
    info: Dict[str, Any] = Field(..., description="Информация о контейнере из Docker API")
    classification: ClassificationResult = Field(..., description="Результаты классификации контейнера")
    
    @field_validator('info')
    @classmethod
    def validate_info(cls, v):
        if not isinstance(v, dict):
            raise ValueError("info должен быть словарем")
        if 'Id' not in v and 'Name' not in v:
            raise ValueError("info должен содержать хотя бы Id или Name")
        return v
