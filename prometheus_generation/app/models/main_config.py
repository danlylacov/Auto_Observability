from typing import Dict, Any

from pydantic import BaseModel


class AddServiceRequest(BaseModel):
    """
    Модель запроса для добавления сервиса в основной конфиг Prometheus.

    Attributes:
        scrape_config: Конфигурация scrape для Prometheus
        target: Целевой адрес или список адресов
        target_name: Имя целевого файла
    """

    scrape_config: Dict[str, Any]
    target: list | dict
    target_name: str


class RemoveServiceRequest(BaseModel):
    """
    Модель запроса для удаления сервиса из основного конфига Prometheus.

    Attributes:
        job_name: Имя job в Prometheus
        target_name: Имя целевого файла
    """

    job_name: str
    target_name: str
