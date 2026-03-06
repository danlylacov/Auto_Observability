import logging
from typing import Dict, Any
from fastapi import APIRouter, status, HTTPException
from app.services.prometheus_manager import PrometheusManager
from app.services.update_config import UpdateConfig

router = APIRouter()
logger = logging.getLogger(__name__)


def get_prometheus_manager() -> PrometheusManager:
    return PrometheusManager()


def get_update_config() -> UpdateConfig:
    return UpdateConfig()


@router.post("/prometheus/start", status_code=status.HTTP_200_OK)
async def start_prometheus() -> Dict[str, Any]:
    """Запускает контейнер Prometheus"""
    try:
        manager = get_prometheus_manager()
        result = manager.start()
        if result:
            return {"message": "Prometheus started successfully", "status": "started"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to start Prometheus"
            )
    except Exception as e:
        logger.error(f"Error starting Prometheus: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start Prometheus: {str(e)}"
        )


@router.post("/prometheus/stop", status_code=status.HTTP_200_OK)
async def stop_prometheus() -> Dict[str, Any]:
    """Останавливает контейнер Prometheus"""
    try:
        manager = get_prometheus_manager()
        result = manager.stop()
        if result:
            return {"message": "Prometheus stopped successfully", "status": "stopped"}
        else:
            return {"message": "Prometheus was not running", "status": "not_found"}
    except Exception as e:
        logger.error(f"Error stopping Prometheus: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop Prometheus: {str(e)}"
        )


@router.get("/prometheus/status", status_code=status.HTTP_200_OK)
async def get_prometheus_status() -> Dict[str, Any]:
    """Получает статус контейнера Prometheus"""
    try:
        manager = get_prometheus_manager()
        status_info = manager.status()
        return status_info
    except Exception as e:
        logger.error(f"Error getting Prometheus status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}"
        )


@router.get("/prometheus/settings", status_code=status.HTTP_200_OK)
async def get_settings() -> Dict[str, Any]:
    """Получает настройки Prometheus"""
    try:
        settings = PrometheusManager.get_prometheus_settings()
        return settings
    except Exception as e:
        logger.error(f"Error getting settings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get settings: {str(e)}"
        )


@router.post("/prometheus/settings", status_code=status.HTTP_200_OK)
async def update_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Обновляет настройки Prometheus"""
    try:
        result = PrometheusManager.update_prometheus_settings(settings)
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


@router.post("/config/update", status_code=status.HTTP_200_OK)
async def update_config() -> Dict[str, Any]:
    """Обновляет конфигурацию Prometheus из MinIO"""
    try:
        updater = get_update_config()
        updater.update()
        return {"message": "Configuration updated successfully"}
    except Exception as e:
        logger.error(f"Error updating config: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update config: {str(e)}"
        )

