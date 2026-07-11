#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

export PYTHONPATH=/app/app
cd /app/app
exec /app/.venv/bin/taskiq worker taskiq_app:broker tasks
