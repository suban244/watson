#!/bin/sh
cd /app/app && ../.venv/bin/alembic upgrade head
cd /app
exec .venv/bin/fastapi run app/main.py --port 8000 --host 0.0.0.0 --reload
