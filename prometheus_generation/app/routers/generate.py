from datetime import datetime
import logging
from typing import Dict, Any
from fastapi import APIRouter, status, HTTPException
from app.services.prometheus_config_generator import PrometheusConfigGenerator
from app.services.minio import MinioService
from app.models.container_data import ContainerData

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", status_code=status.HTTP_200_OK)
async def generate(container_data: ContainerData) -> Dict[str, Dict]:
    """
    Генерирует конфигурацию Prometheus для контейнера
    """
    try:
        generator = PrometheusConfigGenerator()
        container_dict = container_data.model_dump()

        config = generator.generate_config(container_dict)

        if config is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не удалось сгенерировать конфигурацию. Проверьте данные контейнера и классификацию."
            )

        info = generator.get_exporter_info(config)

        minio_service = MinioService()
        upload_data = minio_service.upload_yml(
            config,
            f'{container_data.info["Id"]}-{datetime.now().strftime("%Y%m%d-%H%M%S")}.yml',
        )

        return {
            'config': upload_data,
            'info': info
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при генерации конфигурации: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Внутренняя ошибка сервера: {str(e)}"
        )
