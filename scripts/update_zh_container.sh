#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="langchain-docs-zh"
HEALTH_URL="${HEALTH_URL:-http://localhost:33030}"
OPENAI_URL="$HEALTH_URL/oss/python/integrations/chat/openai"

cd "$ROOT_DIR"

echo "==> Building Docker image with the latest Chinese overlay"
docker compose build "$SERVICE_NAME"

echo "==> Restarting container"
docker compose up -d --force-recreate "$SERVICE_NAME"

echo "==> Waiting for site: $HEALTH_URL"
for attempt in $(seq 1 60); do
  if curl -fsS --max-time 5 "$HEALTH_URL" >/dev/null 2>&1; then
    echo "==> Verifying hidden page: $OPENAI_URL"
    curl -fsS --max-time 10 "$OPENAI_URL" >/dev/null
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
