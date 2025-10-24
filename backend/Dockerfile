FROM ghcr.io/astral-sh/uv:python3.12-alpine

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1

ENV UV_LINK_MODE=copy

COPY pyproject.toml uv.lock /app/

RUN \
    apk add --no-cache postgresql-libs && \
    apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev && \
    uv sync --frozen --no-dev && \
    apk --purge del .build-deps

COPY ./app /app/app

COPY start.sh .
RUN chmod +x ./start.sh

COPY celery/worker/start.sh ./start-worker.sh
RUN chmod +x ./start-worker.sh

COPY celery/beat/start.sh ./start-beat.sh
RUN chmod +x ./start-beat.sh

ENV PYTHONPATH=/app
