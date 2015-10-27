from __future__ import absolute_import

from celery import Celery
from datetime import timedelta

app = Celery(
    'himawari8bot',
    broker='amqp://',
    backend='amqp://',
    include=['himari_tasks']
)

app.conf.update(
    CELERY_TIMEZONE='US/Eastern',
    CELERYBEAT_SCHEDULE_FILENAME="celerybeat_schedule",
    CELERYBEAT_SCHEDULE={
        'main': {
            'task': 'himawari_tasks.main',
            'schedule': timedelta(hours=2)
        },
    }
)

if __name__ == '__main__':
        app.start()

