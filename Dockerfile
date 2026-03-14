FROM python:3.13-slim

# Keeps Python from buffering stdout/stderr and prevents .pyc files
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps: libpq for psycopg, netcat for the DB readiness check
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies in two stages:
# Stage A: everything except django-celery-beat
# Stage B: django-celery-beat alone with --no-deps
# Reason: django-celery-beat==2.8.1 has a stale "Django<6.0" metadata constraint,
# but it works correctly with Django 6.0 (proven by the local virtualenv).
COPY requirements.txt .
RUN pip install --upgrade pip --no-cache-dir && \
    grep -v "django-celery-beat" requirements.txt | pip install --no-cache-dir -r /dev/stdin && \
    pip install --no-cache-dir --no-deps django-celery-beat==2.8.1



# Copy project source code
COPY . .

# Create a non-root user and assign ownership
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser && \
    chown -R appuser:appgroup /app

# Make the entrypoint executable
RUN chmod +x /app/entrypoint.sh

USER appuser

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
