#!/bin/sh

set -o errexit
set -o pipefail
set -o nounset

export PYTHONPATH=/app/app
cd /app/app

/app/.venv/bin/python seed_schedules.py

exec /app/.venv/bin/taskiq scheduler scheduler:scheduler
