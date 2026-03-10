import logging

from fastapi import APIRouter, status, HTTPException

from app.models.manage_models import Container, FullContainer
from app.services.docker_manager import DockerManager

router = APIRouter()

logger = logging.getLogger(__name__)


def get_docker_manager() -> DockerManager:
    """
    Получение экземпляра DockerManager.

    Returns:
        DockerManager: Экземпляр менеджера Docker
    """
    return DockerManager()


@router.post("/container/stop", status_code=status.HTTP_200_OK)
async def stop_container(container: Container):
    """
    Остановка контейнера.

    Args:
        container: Модель контейнера с идентификатором

    Returns:
        dict: Результат операции остановки

    Raises:
        HTTPException: При ошибке остановки контейнера
    """
    try:
        docker_manager = get_docker_manager()
        result = docker_manager.stop_container(container.id)
        return {"message": f"Container {container.id} stopped successfully", "result": result}
    except Exception as e:
        logger.error(f"Error stopping container {container.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop container: {str(e)}"
        )


@router.delete("/container/remove", status_code=status.HTTP_200_OK)
async def remove_container(container: Container, force: bool = False):
    """
    Удаление контейнера.

    Args:
        container: Модель контейнера с идентификатором
        force: Принудительное удаление

    Returns:
        dict: Результат операции удаления

    Raises:
        HTTPException: При ошибке удаления контейнера
    """
    try:
        docker_manager = get_docker_manager()
        result = docker_manager.remove_container(container.id, force=force)
        return {"message": f"Container {container.id} removed successfully", "result": result}
    except Exception as e:
        logger.error(f"Error removing container {container.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove container: {str(e)}"
        )


@router.post("/container/start", status_code=status.HTTP_200_OK)
async def start_container(container: Container):
    """
    Запуск контейнера.

    Args:
        container: Модель контейнера с идентификатором

    Returns:
        dict: Результат операции запуска

    Raises:
        HTTPException: При ошибке запуска контейнера
    """
    try:
        docker_manager = get_docker_manager()
        result = docker_manager.start_container(container.id)
        return {"message": f"Container {container.id} started successfully", "result": result}
    except Exception as e:
        logger.error(f"Error starting container {container.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start container: {str(e)}"
        )


@router.post("/container/pull_and_run", status_code=status.HTTP_200_OK)
async def pull_and_run_container(container: FullContainer):
    """
    Загрузка образа и запуск контейнера.

    Args:
        container: Модель контейнера с полными параметрами

    Returns:
        dict: Результат операции запуска

    Raises:
        HTTPException: При ошибке загрузки или запуска контейнера
    """
    try:
        docker_manager = get_docker_manager()
        result = docker_manager.pull_and_run_container(
            container.image_name,
            container.command,
            container.name,
            container.detach,
            container.ports,
            container.volumes,
            container.environment,
            container.network
        )
        return {"result": result}
    except Exception as e:
        logger.error(f"Error pulling and starting container: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start container: {str(e)}"
        )


@router.delete("/volume/remove", status_code=status.HTTP_200_OK)
async def remove_volume(volume_name: str, force: bool = False):
    """
    Удаление тома.

    Args:
        volume_name: Имя тома
        force: Принудительное удаление

    Returns:
        dict: Результат операции удаления

    Raises:
        HTTPException: При ошибке удаления тома
    """
    try:
        docker_manager = get_docker_manager()
        result = docker_manager.remove_volume(volume_name, force=force)
        return {"message": f"Volume {volume_name} removed successfully", "result": result}
    except Exception as e:
        logger.error(f"Error removing volume {volume_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove volume: {str(e)}"
        )


@router.post("/volumes/prune", status_code=status.HTTP_200_OK)
async def prune_volumes():
    """
    Очистка неиспользуемых томов.

    Returns:
        dict: Результат операции очистки

    Raises:
        HTTPException: При ошибке очистки томов
    """
    try:
        docker_manager = get_docker_manager()
        result = docker_manager.prune_volumes()
        return {"message": "Unused volumes pruned successfully", "result": result}
    except Exception as e:
        logger.error(f"Error pruning volumes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to prune volumes: {str(e)}"
        )


@router.delete("/image/remove", status_code=status.HTTP_200_OK)
async def remove_image(image_id_or_name: str, force: bool = False):
    """
    Удаление образа.

    Args:
        image_id_or_name: Идентификатор или имя образа
        force: Принудительное удаление

    Returns:
        dict: Результат операции удаления

    Raises:
        HTTPException: При ошибке удаления образа
    """
    try:
        docker_manager = get_docker_manager()
        result = docker_manager.remove_image(image_id_or_name, force=force)
        return {"message": f"Image {image_id_or_name} removed successfully", "result": result}
    except Exception as e:
        logger.error(f"Error removing image {image_id_or_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove image: {str(e)}"
        )


@router.post("/system/cleanup", status_code=status.HTTP_200_OK)
async def cleanup_system():
    """
    Очистка системы: удаление остановленных контейнеров, неиспользуемых сетей и образов.

    Returns:
        dict: Результат операции очистки

    Raises:
        HTTPException: При ошибке очистки системы
    """
    try:
        docker_manager = get_docker_manager()
        result = docker_manager.cleanup_system()
        return {"message": "System cleanup completed successfully", "result": result}
    except Exception as e:
        logger.error(f"Error during system cleanup: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup system: {str(e)}"
        )