#!/usr/bin/env bash
# Build and (re)start the production stack.
# Builds first; containers are only recreated if the build succeeds, so a
# failed build leaves the previous stack running. alembic migrations run on
# backend startup (see backend/start.sh).
set -euo pipefail

# Resolve repo root regardless of where this is called from.
cd "$(dirname "$0")/.."

docker compose -f prod.yml up -d --build --remove-orphans

# Reclaim disk from old image layers (important on the Pi's small storage).
docker image prune -f
