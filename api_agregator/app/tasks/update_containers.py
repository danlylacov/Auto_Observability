from app.celery_app import celery_app
from app.services.update_containers import UpdateContainers


@celery_app.task(name='app.tasks.update_containers')
def update_containers():
    """Задача Celery для обновления контейнеров"""
    update_containers_service = UpdateContainers()
    update_containers_service.upload_containers()
