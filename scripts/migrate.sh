#!/usr/bin/env bash
# Run Alembic migrations against apps/api/.env's DATABASE_URL, either directly
# (if a local venv exists) or via Docker Compose against the running api service.
set -euo pipefail
cd "$(dirname "$0")/../apps/api"

if [ -d .venv ]; then
  . .venv/bin/activate
  alembic upgrade head
else
  cd ../..
  docker compose run --rm api alembic upgrade head
fi
