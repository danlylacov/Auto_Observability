import logging
from typing import Optional
from fastapi import APIRouter, status, HTTPException
from app.services.docker_manager import DockerManager

router = APIRouter()
logger = logging.getLogger(__name__)


def get_docker_manager() -> DockerManager:
    return DockerManager()


@router.post("/", status_code=status.HTTP_201_CREATED)
async def get_containers():
    try:
        docker_manager = get_docker_manager()

        try:
            docker_manager.client.ping()
        except Exception as e:
            logger.error(f"Docker daemon not responding: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Docker daemon is not responding"
            )

        containers = docker_manager.discover_containers()

        if not containers:
            logger.info("No containers found")
            return {"containers": [], "message": "No containers found"}

        logger.info(f"Successfully discovered {len(containers)} containers")
        return {
            "containers": containers,
            "count": len(containers),
            "message": f"Successfully discovered {len(containers)} containers"
        }

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Invalid input parameters: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input: {str(e)}"
        )
    except ConnectionError as e:
        logger.error(f"Connection error to Docker host: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cannot connect to Docker host: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error discovering containers: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to discover containers: {str(e)}"
        )
