#!/bin/sh
set -e
set -o errexit
set -o pipefail
set -o nounset

echo "Starting Celery Beat..."
export PYTHONPATH=/app/app
cd /app/app
exec /app/.venv/bin/celery -A celery_app.celery_app beat -l INFO
