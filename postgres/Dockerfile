FROM postgres:18.1

RUN apt-get update && apt-get install -y \
    postgresql-18-pgvector \
    git \
    build-essential \
    postgresql-server-dev-18 \
    && rm -rf /var/lib/apt/lists/*

RUN cd /tmp \
    && git clone https://github.com/timescale/pg_textsearch \
    && cd pg_textsearch \
    && make \
    && make install \
    && rm -rf /tmp/pg_textsearch
