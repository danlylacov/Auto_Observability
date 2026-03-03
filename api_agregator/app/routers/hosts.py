import logging
from fastapi import APIRouter, status, Depends
from app.models.postgres.host import Host
from sqlalchemy.orm import Session

from app.db.postgres.database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/add", status_code=status.HTTP_200_OK)
async def add_host(name: str, host: str, port: int, db: Session = Depends(get_db)):
    """
    Добавление нового целевого хоста
    """
    try:
        prometheus_config = Host(name=name, host=host, port=port)
        db.add(prometheus_config)
        db.commit()
        db.refresh(prometheus_config)
        return {"message": "Host added successfully"}
    except Exception as e:
        return {"message": str(e)}


@router.get("/get", status_code=status.HTTP_200_OK)
async def get_hosts(db: Session = Depends(get_db)):
    """
    Получение всех хостов
    """
    try:
        hosts = db.query(Host).all()
        return {"hosts": hosts}
    except Exception as e:
        return {"message": str(e)}


@router.put("/update", status_code=status.HTTP_200_OK)
async def update_host(
        id: str,
        name: str | None = None,
        host: str | None = None,
        port: int | None = None,
        db: Session = Depends(get_db),
):
    """
    Обновление существующего целевого хоста по id
    """
    try:
        db_host = db.query(Host).filter(Host.id == id).first()
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
        return {"message": "Host updated successfully"}
    except Exception as e:
        return {"message": str(e)}


@router.delete("/delete", status_code=status.HTTP_200_OK)
async def delete_host(id: str, db: Session = Depends(get_db)):
    """
    Удаление целевого хоста по id
    """
    try:
        db_host = db.query(Host).filter(Host.id == id).first()
        if not db_host:
            return {"message": "Host not found"}

        db.delete(db_host)
        db.commit()
        return {"message": "Host deleted successfully"}
    except Exception as e:
        return {"message": str(e)}
