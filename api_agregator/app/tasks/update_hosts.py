from app.celery_app import celery_app
from app.services.hosts_service import HostsService

from app.db.postgres.database import SessionLocal


@celery_app.task(name='app.tasks.update_hosts')
def update_hosts():
    """
    Задача Celery для обновления хостов.

    Проверяет работоспособность всех хостов и сохраняет
    информацию о них в Redis.
    """
    db = SessionLocal()
    try:
        hosts_service = HostsService(db)
        hosts_service.upload_hosts()
    finally:
        db.close()