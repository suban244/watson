FROM ghcr.io/astral-sh/uv:python3.12-alpine

WORKDIR /app

COPY . /app

RUN \
    apk add --no-cache postgresql-libs && \
    apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev && \
    uv sync --frozen --no-cache && \
    apk --purge del .build-deps


# CMD ["fastapi", "run", "app/main.py", "--port", "8000"]
ENTRYPOINT ["/app/.venv/bin/fastapi", "run", "app/main.py", "--port", "8000", "--host", "0.0.0.0", "--reload"]
