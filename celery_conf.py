from __future__ import absolute_import

from celery import Celery
from datetime import timedelta

from kombu import Exchange, Queue

app = Celery(
    'himawari_bot',
    broker='amqp://',
    backend='amqp://',
    include=['himawari_tasks']
)

app.conf.update(
    CELERYBEAT_SCHEDULE_FILENAME="celerybeat_schedule",
    CELERYBEAT_SCHEDULE={
        'main': {
            'task': 'himawari_tasks.main',
            'schedule': timedelta(hours=2)
        },
    },
    CELERY_DEFAULT_QUEUE='himawari',
    CELERY_QUEUES=(
        Queue('himawari', Exchange('himawari'), routing_key='himawari'),
    ),
    CELERY_ROUTES={
        'himawari_tasks.main': {'queue': 'himawari'}}
)

if __name__ == '__main__':
        app.start()
