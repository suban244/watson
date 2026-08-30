#!/bin/sh
cd /app/app && ../.venv/bin/alembic upgrade head
../.venv/bin/python -m db.readonly
cd /app
exec .venv/bin/fastapi run app/main.py --port 8000 --host 0.0.0.0
