FROM postgres:18.1

RUN apt-get update && apt-get install -y \
    postgresql-18-pgvector \
    git \
    build-essential \
    curl \
    postgresql-server-dev-18 \
    && rm -rf /var/lib/apt/lists/*

RUN cd /tmp \
    && git clone https://github.com/timescale/pg_textsearch \
    && cd pg_textsearch \
    && make \
    && make install \
    && rm -rf /tmp/pg_textsearch


RUN apt-get update \
    && curl -L "https://github.com/paradedb/paradedb/releases/download/v0.23.2/postgresql-18-pg-search_0.23.2-1PARADEDB-noble_arm64.deb" -o /tmp/pg_search.deb \
    && dpkg --force-depends -i /tmp/pg_search.deb \
    && rm -f /tmp/pg_search.deb \
    && rm -rf /var/lib/apt/lists/*
