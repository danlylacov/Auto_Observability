import logging
from typing import Optional

from fastapi import APIRouter, status, HTTPException
from app.services.docker_manager import DockerManager
from app.models.remote_docker_host import RemoteHost
from app.models.manage_models import Container

router = APIRouter()

logger = logging.getLogger(__name__)


def get_docker_manager(remote_host: Optional[RemoteHost]= None) -> DockerManager:
    return DockerManager(f'{remote_host.username}@{remote_host.address}') if remote_host \
        else DockerManager()

@router.post("/container/stop", status_code=status.HTTP_200_OK)
async def stop_container(container: Container, remote_host: Optional[RemoteHost] = None):
    try:
        docker_manager = get_docker_manager(remote_host)
        result = docker_manager.stop_container(container.id)
        return {"message": f"Container {container.id} stopped successfully", "result": result}
    except Exception as e:
        logger.error(f"Error stopping container {container.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop container: {str(e)}"
        )


@router.delete("/container/remove", status_code=status.HTTP_200_OK)
async def remove_container(container: Container, force: bool = False, remote_host: Optional[RemoteHost] = None):
    try:
        docker_manager = get_docker_manager(remote_host)
        result = docker_manager.remove_container(container.id, force=force)
        return {"message": f"Container {container.id} removed successfully", "result": result}
    except Exception as e:
        logger.error(f"Error removing container {container.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove container: {str(e)}"
        )

@router.post("/container/start", status_code=status.HTTP_200_OK)
async def start_container(container: Container, remote_host: Optional[RemoteHost] = None):
    try:
        docker_manager = get_docker_manager(remote_host)
        result = docker_manager.start_container(container.id)
        return {"message": f"Container {container.id} started successfully", "result": result}
    except Exception as e:
        logger.error(f"Error starting container {container.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start container: {str(e)}"
        )


@router.delete("/volume/remove", status_code=status.HTTP_200_OK)
async def remove_volume(volume_name: str, force: bool = False, remote_host: Optional[RemoteHost] = None):
    try:
        docker_manager = get_docker_manager(remote_host)
        result = docker_manager.remove_volume(volume_name, force=force)
        return {"message": f"Volume {volume_name} removed successfully", "result": result}
    except Exception as e:
        logger.error(f"Error removing volume {volume_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove volume: {str(e)}"
        )


@router.post("/volumes/prune", status_code=status.HTTP_200_OK)
async def prune_volumes(remote_host: Optional[RemoteHost] = None):
    try:
        docker_manager = get_docker_manager(remote_host)
        result = docker_manager.prune_volumes()
        return {"message": "Unused volumes pruned successfully", "result": result}
    except Exception as e:
        logger.error(f"Error pruning volumes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to prune volumes: {str(e)}"
        )


@router.delete("/image/remove", status_code=status.HTTP_200_OK)
async def remove_image(image_id_or_name: str, force: bool = False, remote_host: Optional[RemoteHost] = None):
    try:
        docker_manager = get_docker_manager(remote_host)
        result = docker_manager.remove_image(image_id_or_name, force=force)
        return {"message": f"Image {image_id_or_name} removed successfully", "result": result}
    except Exception as e:
        logger.error(f"Error removing image {image_id_or_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove image: {str(e)}"
        )


@router.post("/system/cleanup", status_code=status.HTTP_200_OK)
async def cleanup_system(remote_host: Optional[RemoteHost] = None):
    try:
        docker_manager = get_docker_manager(remote_host)
        result = docker_manager.cleanup_system()
        return {"message": "System cleanup completed successfully", "result": result}
    except Exception as e:
        logger.error(f"Error during system cleanup: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup system: {str(e)}"
        )