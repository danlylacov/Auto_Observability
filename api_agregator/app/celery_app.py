from celery import Celery
from celery.schedules import crontab
from app.config import settings

# Создаем экземпляр Celery
celery_app = Celery(
    "worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=['app.tasks']
)

# Настройка Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 минут
    task_soft_time_limit=60,   # 60 секунд
)


celery_app.conf.beat_schedule = {
    'run-every-minute': {
        'task': 'app.tasks.minute_task',
        'schedule': crontab(minute='*'),
    }
}

# Для отладки
if __name__ == '__main__':
    celery_app.start()