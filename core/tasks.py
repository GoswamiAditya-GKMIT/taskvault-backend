import os
import time
import logging
from celery import shared_task
from django.conf import settings

logger = logging.getLogger("taskvault.request")

@shared_task
def delete_old_logs():
    """
    Deletes log files in the logs directory that are older than 30 days.
    """
    log_dir = os.path.join(settings.BASE_DIR, 'logs')
    if not os.path.exists(log_dir):
        return "Log directory does not exist."

    now = time.time()
    retention_period = 30 * 24 * 60 * 60  # 30 days in seconds
    count = 0
    
    for filename in os.listdir(log_dir):
        file_path = os.path.join(log_dir, filename)
        if os.path.isfile(file_path):
            file_age = now - os.path.getmtime(file_path)
            if file_age > retention_period:
                os.remove(file_path)
                count += 1
                
    return f"Deleted {count} log files older than 30 days."
