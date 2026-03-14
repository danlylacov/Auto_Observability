import logging
from typing import Dict, Any

from fastapi import APIRouter, status, HTTPException

from app.services.grafana_manager import GrafanaManager


router = APIRouter()
logger = logging.getLogger(__name__)


def get_grafana_manager() -> GrafanaManager:
    """
    Получение экземпляра grafana.

    Returns:
        PrometheusManager: Экземпляр менеджера grafana
    """
    return GrafanaManager()




@router.post("/grafana/start", status_code=status.HTTP_200_OK)
async def start_grafana() -> Dict[str, Any]:
    """
    Запускает контейнер Grafana.

    Returns:
        Dict[str, Any]: Результат запуска grafana

    Raises:
        HTTPException: При ошибке запуска grafana
    """
    try:
        manager = get_grafana_manager()
        result = manager.start_grafana()
        if result:
            return {"message": "Grafana started successfully", "status": "started"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to start Grafana"
            )
    except Exception as e:
        logger.error(f"Error starting Grafana: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start Grafana: {str(e)}"
        )


@router.post("/grafana/stop", status_code=status.HTTP_200_OK)
async def stop_grafana() -> Dict[str, Any]:
    """
    Останавливает контейнер grafana.

    Returns:
        Dict[str, Any]: Результат остановки grafana

    Raises:
        HTTPException: При ошибке остановки grafana
    """
    try:
        manager = get_grafana_manager()
        result = manager.stop_grafana()
        if result:
            return {"message": "grafana stopped successfully", "status": "stopped"}
        else:
            return {"message": "grafana was not running", "status": "not_found"}
    except Exception as e:
        logger.error(f"Error stopping grafana: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop grafana: {str(e)}"
        )


@router.get("/grafana/status", status_code=status.HTTP_200_OK)
async def get_grafana_status() -> Dict[str, Any]:
    """
    Получает статус контейнера grafana.

    Returns:
        Dict[str, Any]: Статус контейнера grafana

    Raises:
        HTTPException: При ошибке получения статуса
    """
    try:
        manager = get_grafana_manager()
        status_info = manager.get_status()
        if status_info is None:
            return {"status": "unknown", "message": "Container status could not be determined"}
        return {"status": status_info}
    except Exception as e:
        logger.error(f"Error getting grafana status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}"
        )


@router.get("/grafana/settings", status_code=status.HTTP_200_OK)
async def get_settings() -> Dict[str, Any]:
    """
    Получает настройки grafana.

    Returns:
        Dict[str, Any]: Настройки grafana

    Raises:
        HTTPException: При ошибке получения настроек
    """
    try:
        manager = get_grafana_manager()
        manager_settings = manager.get_grafana_settings()
        return manager_settings
    except Exception as e:
        logger.error(f"Error getting settings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get settings: {str(e)}"
        )


@router.post("/grafana/settings", status_code=status.HTTP_200_OK)
async def update_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Обновляет настройки grafana.

    Args:
        settings: Новые настройки grafana

    Returns:
        Dict[str, Any]: Результат обновления настроек

    Raises:
        HTTPException: При ошибке обновления настроек
    """
    try:
        manager = get_grafana_manager()
        result = manager.update_grafana_settings(settings)
        if result:
            return {"message": "Settings updated successfully", "settings": settings}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update settings"
            )
    except Exception as e:
        logger.error(f"Error updating settings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update settings: {str(e)}"
        )




