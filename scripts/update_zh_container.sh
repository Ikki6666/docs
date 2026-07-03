#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="langchain-docs-zh"
HEALTH_URL="${HEALTH_URL:-http://localhost:33030}"

cd "$ROOT_DIR"

echo "==> Building Chinese overlay locally"
uv run python -m scripts.zh.overlay build

echo "==> Building Docker image"
docker compose build "$SERVICE_NAME"

echo "==> Restarting container"
docker compose up -d "$SERVICE_NAME"

echo "==> Waiting for site: $HEALTH_URL"
for attempt in $(seq 1 60); do
  if curl -fsS --max-time 5 "$HEALTH_URL" >/dev/null 2>&1; then
    echo "==> Ready: $HEALTH_URL"
    docker compose ps "$SERVICE_NAME"
    exit 0
  fi

  if [ "$attempt" -eq 60 ]; then
    echo "ERROR: Site did not become healthy after 60 attempts." >&2
    echo "Recent logs:" >&2
    docker compose logs --tail=80 "$SERVICE_NAME" >&2
    exit 1
  fi

  sleep 2
done
