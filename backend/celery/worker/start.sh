#!/bin/sh

set -o errexit
set -o pipefail
set -o nounset

export PYTHONPATH=/app/app
cd /app/app
exec /app/.venv/bin/celery -A celery_app.celery_app worker -l INFO
