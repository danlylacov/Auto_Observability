"""Celery application configuration module."""

import os
import sys
from datetime import timedelta

from celery import Celery
from celery.schedules import crontab

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.config import settings

celery_app = Celery(
    "worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=['app.tasks']
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=60,
)


celery_app.conf.beat_schedule = {
    'run-every-minute': {
        'task': 'app.tasks.update_containers',
        'schedule': crontab(minute='*'),
    },
    'run-hosts-every-15-seconds': {
        'task': 'app.tasks.update_hosts',
        'schedule': timedelta(seconds=15),
    },
}

if __name__ == '__main__':
    celery_app.start()
