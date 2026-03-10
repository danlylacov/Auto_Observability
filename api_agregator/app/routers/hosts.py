"""Hosts API router module."""

import logging

from fastapi import APIRouter, status, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.postgres.database import get_db
from app.models.postgres.host import Host
from app.services.hosts_service import HostsService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/add", status_code=status.HTTP_200_OK)
async def add_host(name: str, host: str, port: int, db: Session = Depends(get_db)):
    """
    Добавление нового целевого хоста.

    Args:
        name: Имя хоста
        host: Адрес хоста
        port: Порт хоста
        db: Сессия базы данных

    Returns:
        dict: Сообщение об успешном добавлении или ошибке
    """
    try:
        host_config = Host(name=name, host=host, port=port)
        db.add(host_config)
        db.commit()
        db.refresh(host_config)

        hosts_service = HostsService(db)
        hosts_service.upload_hosts()
        return {"message": "Host added successfully"}
    except Exception as e:
        return {"message": str(e)}


@router.get("/get", status_code=status.HTTP_200_OK)
async def get_hosts(db: Session = Depends(get_db)):
    """
    Получение всех хостов из Redis.

    Args:
        db: Сессия базы данных

    Returns:
        dict: Словарь с хостами или сообщение об ошибке
    """
    try:
        hosts_service = HostsService(db)
        hosts = hosts_service.get_all_hosts()
        return {"hosts": hosts}
    except Exception as e:
        return {"message": str(e)}


@router.put("/update", status_code=status.HTTP_200_OK)
async def update_host(
        host_id: str,
        name: str | None = None,
        host: str | None = None,
        port: int | None = None,
        db: Session = Depends(get_db),
):
    """
    Обновление существующего целевого хоста по id.

    Args:
        host_id: Идентификатор хоста
        name: Новое имя хоста (опционально)
        host: Новый адрес хоста (опционально)
        port: Новый порт хоста (опционально)
        db: Сессия базы данных

    Returns:
        dict: Сообщение об успешном обновлении или ошибке
    """
    try:
        db_host = db.query(Host).filter(Host.id == host_id).first()
        if not db_host:
            return {"message": "Host not found"}

        if name is not None:
            db_host.name = name
        if host is not None:
            db_host.host = host
        if port is not None:
            db_host.port = port

        db.commit()
        db.refresh(db_host)

        hosts_service = HostsService(db)
        hosts_service.upload_hosts()
        return {"message": "Host updated successfully"}
    except Exception as e:
        return {"message": str(e)}


@router.delete("/delete", status_code=status.HTTP_200_OK)
async def delete_host(
    host_id: str = Query(..., alias="id", description="Идентификатор хоста для удаления"),
    db: Session = Depends(get_db)
):
    """
    Удаление целевого хоста по id.

    Args:
        host_id: Идентификатор хоста
        db: Сессия базы данных

    Returns:
        dict: Сообщение об успешном удалении или ошибке

    Raises:
        HTTPException: При ошибке удаления
    """
    try:
        db_host = db.query(Host).filter(Host.id == host_id).first()
        if not db_host:
            raise HTTPException(status_code=404, detail="Host not found")

        db.delete(db_host)
        db.commit()

        hosts_service = HostsService(db)
        hosts_service.upload_hosts()
        return {"message": "Host deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting host %s: %s", host_id, str(e), exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete host: {str(e)}"
        )


@router.get("/update_hosts", status_code=status.HTTP_200_OK)
async def update_hosts_info(db: Session = Depends(get_db)) -> dict[str, dict]:
    """
    Обновление информации о хостах в Redis.

    Args:
        db: Сессия базы данных

    Returns:
        dict[str, dict]: Словарь с обновленными данными о хостах
    """
    hosts_service = HostsService(db)
    hosts = hosts_service.upload_hosts()
    return hosts
