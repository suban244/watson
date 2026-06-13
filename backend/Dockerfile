FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock /app/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

COPY ./app /app/app

COPY start.sh .
RUN chmod +x ./start.sh

COPY celery/worker/start.sh ./start-worker.sh
RUN chmod +x ./start-worker.sh

COPY celery/beat/start.sh ./start-beat.sh
RUN chmod +x ./start-beat.sh

ENV PYTHONPATH=/app
