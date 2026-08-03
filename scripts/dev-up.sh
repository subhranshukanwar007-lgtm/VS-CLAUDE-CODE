#!/usr/bin/env bash
# Bring up the full stack (Postgres, Redis, API, worker, beat, web) with Docker
# Compose. Run once from the repo root: ./scripts/dev-up.sh
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f apps/api/.env ]; then
  echo "apps/api/.env not found — copying from .env.example (edit it to add AI provider keys, etc.)"
  cp apps/api/.env.example apps/api/.env
fi

docker compose up --build
