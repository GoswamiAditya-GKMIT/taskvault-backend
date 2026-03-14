#!/bin/bash
# =============================================================================
# entrypoint.sh — Routes to the correct service based on $SERVICE env variable
# =============================================================================
set -e

# Wait for PostgreSQL to be ready before any service starts
echo "[entrypoint] Waiting for PostgreSQL at ${POSTGRES_HOST}:5432..."
until nc -z "${POSTGRES_HOST}" 5432; do
  sleep 1
done
echo "[entrypoint] PostgreSQL is ready."

SERVICE="${SERVICE:-web}"

case "$SERVICE" in
  web)
    echo "[entrypoint] Running database migrations..."
    python manage.py migrate --noinput

    echo "[entrypoint] Collecting static files..."
    python manage.py collectstatic --noinput --clear

    echo "[entrypoint] Seeding super admin..."
    python manage.py seed_superadmin

    echo "[entrypoint] Starting Gunicorn..."
    exec gunicorn config.wsgi:application \
      --bind 0.0.0.0:8000 \
      --workers 3 \
      --timeout 120 \
      --log-level info \
      --access-logfile - \
      --error-logfile -
    ;;


  celery_worker)
    echo "[entrypoint] Starting Celery Worker..."
    exec celery -A config worker -l info --concurrency=4
    ;;

  celery_beat)
    echo "[entrypoint] Starting Celery Beat..."
    exec celery -A config beat -l info \
      --scheduler django_celery_beat.schedulers:DatabaseScheduler
    ;;

  *)
    echo "[entrypoint] Unknown SERVICE: '$SERVICE'. Expected: web, celery_worker, celery_beat"
    exit 1
    ;;
esac
