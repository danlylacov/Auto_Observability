import logging
from fastapi import APIRouter, status, HTTPException
from app.services.update_containers import UpdateContainers


router = APIRouter()
logger = logging.getLogger(__name__)


@router.patch("/update_containers", status_code=status.HTTP_200_OK)
async def update_containers():
    """
    Обновление информации о контейнерах
    """
    update_containers_service = UpdateContainers()
    update_containers_service.upload_containers()

