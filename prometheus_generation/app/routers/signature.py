import logging
from typing import Dict

from fastapi import APIRouter, status

from app.services.signature import Signature

router = APIRouter()
logger = logging.getLogger(__name__)


@router.patch("/update", status_code=status.HTTP_200_OK)
async def generate(new_signature: str) -> Dict[str, str]:
    """
    Обновляет файл signatures.yml.

    Args:
        new_signature: Новая подпись для обновления

    Returns:
        Dict[str, str]: Результат обновления
    """
    signature = Signature()
    try:
        signature.update(new_signature)
        return {"result": "success"}
    except Exception as e:
        logger.error(f"Ошибка при обновлении signature: {str(e)}", exc_info=True)
        return {"result": str(e)}


@router.get("/get", status_code=status.HTTP_200_OK)
async def get() -> Dict[str, str]:
    """
    Получает содержимое файла signatures.yml.

    Returns:
        Dict[str, str]: Содержимое файла signatures.yml или ошибка
    """
    signature = Signature()
    try:
        return {"signature.yml": signature.get()}
    except Exception as e:
        logger.error(f"Ошибка при получении signature: {str(e)}", exc_info=True)
        return {"signature.yml": str(e)}



