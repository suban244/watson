FROM ghcr.io/astral-sh/uv:python3.12-alpine

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1

ENV UV_LINK_MODE=copy

COPY pyproject.toml uv.lock /app/

COPY ./app /app/app

RUN \
    apk add --no-cache postgresql-libs && \
    apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev && \
    uv sync --frozen --no-install-project --no-dev && \
    apk --purge del .build-deps

ENTRYPOINT ["/app/.venv/bin/fastapi", "run", "app/main.py", "--port", "8000", "--host", "0.0.0.0", "--reload"]
