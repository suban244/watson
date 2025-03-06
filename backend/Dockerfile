FROM ghcr.io/astral-sh/uv:python3.12-alpine

WORKDIR /app

COPY . /app

RUN uv sync --frozen --no-cache

# CMD ["fastapi", "run", "app/main.py", "--port", "8000"]
ENTRYPOINT ["/app/.venv/bin/fastapi", "run", "app/main.py", "--port", "8000", "--host", "0.0.0.0", "--reload"]