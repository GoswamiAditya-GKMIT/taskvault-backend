#!/bin/bash
# =============================================================================
# entrypoint.sh — Routes to the correct service based on $SERVICE env variable
# =============================================================================
set -e

# Wait for PostgreSQL to be ready before any service starts
echo "[entrypoint] Waiting for PostgreSQL at ${POSTGRES_HOST}:${POSTGRES_PORT:-5432}..."
until nc -z "${POSTGRES_HOST}" "${POSTGRES_PORT:-5432}"; do
  sleep 1
done
echo "[entrypoint] PostgreSQL is ready."

SERVICE="${SERVICE:-web}"

# Check for New Relic license key to dynamically run APM
if [ -n "$NEW_RELIC_LICENSE_KEY" ]; then
    echo "[entrypoint] New Relic enabled for $SERVICE."
    EXEC_PREFIX="newrelic-admin run-program"
else
    echo "[entrypoint] New Relic disabled (No license key found)."
    EXEC_PREFIX=""
fi

case "$SERVICE" in
  web)
    echo "[entrypoint] Running database migrations..."
    python manage.py migrate --noinput

    echo "[entrypoint] Collecting static files..."
    python manage.py collectstatic --noinput --clear

    echo "[entrypoint] Seeding super admin..."
    python manage.py seed_superadmin

    echo "[entrypoint] Starting Gunicorn..."
    exec $EXEC_PREFIX gunicorn config.wsgi:application \
      --bind 0.0.0.0:8000 \
      --workers 3 \
      --timeout 120 \
      --log-level info \
      --access-logfile - \
      --error-logfile -
    ;;


  celery_worker)
    echo "[entrypoint] Starting Celery Worker..."
    exec $EXEC_PREFIX celery -A config worker -l info --concurrency=4
    ;;

  celery_beat)
    echo "[entrypoint] Starting Celery Beat..."
    exec $EXEC_PREFIX celery -A config beat -l info \
      --scheduler django_celery_beat.schedulers:DatabaseScheduler
    ;;

  *)
    echo "[entrypoint] Unknown SERVICE: '$SERVICE'. Expected: web, celery_worker, celery_beat"
    exit 1
    ;;
esac
