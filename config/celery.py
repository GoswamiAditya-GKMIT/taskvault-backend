import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("TaskVault")

app.config_from_object("django.conf:settings", namespace="CELERY")

# THIS IS CRITICAL
app.autodiscover_tasks()