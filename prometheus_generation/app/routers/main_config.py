from typing import Dict

from fastapi import APIRouter, status, HTTPException

from app.models.main_config import AddServiceRequest, RemoveServiceRequest
from app.services.main_config import MainPrometheusConfig

router = APIRouter()


@router.post("/add", status_code=status.HTTP_200_OK)
async def add_service(request: AddServiceRequest) -> Dict[str, str]:
    """
    Добавляет сервис в основной конфиг Prometheus.

    Args:
        request: Запрос с данными о сервисе для добавления

    Returns:
        Dict[str, str]: Результат добавления сервиса

    Raises:
        HTTPException: При ошибке добавления сервиса
    """
    try:
        config = MainPrometheusConfig()
        result = config.add_service(
            scrape_config=request.scrape_config,
            target=request.target,
            target_name=request.target_name
        )

        if result:
            return {"status": "success", "message": "Сервис успешно добавлен"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не удалось добавить сервис"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при добавлении сервиса: {str(e)}"
        )


@router.delete("/remove", status_code=status.HTTP_200_OK)
async def remove_service(request: RemoveServiceRequest) -> Dict[str, str]:
    """
    Удаляет сервис из основного конфига Prometheus.

    Args:
        request: Запрос с данными о сервисе для удаления

    Returns:
        Dict[str, str]: Результат удаления сервиса

    Raises:
        HTTPException: При ошибке удаления сервиса
    """
    try:
        config = MainPrometheusConfig()
        result = config.remove_service(
            job_name=request.job_name,
            target_name=request.target_name
        )

        if result:
            return {"status": "success", "message": "Сервис успешно удален"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не удалось удалить сервис"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при удалении сервиса: {str(e)}"
        )


@router.get("/", status_code=status.HTTP_200_OK)
async def get_full_config() -> Dict:
    """
    Получает полный конфиг Prometheus и все файлы targets.

    Returns:
        Dict: Полный конфиг Prometheus с targets

    Raises:
        HTTPException: При ошибке получения конфига
    """
    try:
        config = MainPrometheusConfig()
        result = config.get_full_config()
        return result
    except Exception as e:
        error_str = str(e)
        # Если конфиг не найден, возвращаем пустую структуру вместо ошибки
        if "NoSuchKey" in error_str or "does not exist" in error_str:
            return {
                'main_config': None,
                'targets': {}
            }
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении конфига: {error_str}"
        )
