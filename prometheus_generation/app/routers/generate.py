import logging
from typing import Dict, Any

from fastapi import APIRouter, status, HTTPException

from app.models.container_data import ContainerData
from app.services.minio import MinioService
from app.services.prometheus_config_generator import PrometheusConfigGenerator

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", status_code=status.HTTP_200_OK)
async def generate(container_data: ContainerData, host: str) -> Dict[str, Dict]:
    """
    Генерирует конфигурацию Prometheus для контейнера.

    Args:
        container_data: Данные о контейнере
        host: Адрес хоста

    Returns:
        Dict[str, Dict]: Конфигурация и информация об экспортере

    Raises:
        HTTPException: При ошибке генерации конфигурации
    """
    try:
        generator = PrometheusConfigGenerator()
        container_dict = container_data.model_dump()

        config = generator.generate_config(container_dict, host)

        if config is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не удалось сгенерировать конфигурацию. Проверьте данные контейнера и классификацию."
            )

        minio_service = MinioService()
        upload_data = minio_service.upload_config(
            config['config']["scrape_config"],
            config['config']["target"],
            container_data.info['Id']
        )

        return {
            'config': upload_data,
            'info': config['exporter_config']
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при генерации конфигурации: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Внутренняя ошибка сервера: {str(e)}"
        )
