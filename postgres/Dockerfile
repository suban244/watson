FROM postgres:18.1

RUN apt-get update && apt-get install -y \
    postgresql-18-pgvector \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update \
    && curl -L "https://github.com/paradedb/paradedb/releases/download/v0.23.2/postgresql-18-pg-search_0.23.2-1PARADEDB-trixie_arm64.deb" -o /tmp/pg_search.deb \
    && apt-get install -y /tmp/pg_search.deb \
    && rm -f /tmp/pg_search.deb \
    && rm -rf /var/lib/apt/lists/*
