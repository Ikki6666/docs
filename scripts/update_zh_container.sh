#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="langchain-docs-zh"
HEALTH_URL="${HEALTH_URL:-http://localhost:33030}"
OPENAI_URL="$HEALTH_URL/oss/python/integrations/chat/openai"
AUTH_COOKIE="${AUTH_COOKIE:-dulu=ikki}"

cd "$ROOT_DIR"

echo "==> Building Docker image with the latest Chinese overlay"
docker compose build "$SERVICE_NAME"

echo "==> Restarting documentation and Nginx containers"
docker compose up -d --force-recreate "$SERVICE_NAME" nginx

echo "==> Waiting for site: $HEALTH_URL"
for attempt in $(seq 1 60); do
  if curl -fsS --max-time 5 -H "Cookie: $AUTH_COOKIE" "$HEALTH_URL" >/dev/null 2>&1; then
    unauthorized_status=$(curl -sS --max-time 5 -o /dev/null -w "%{http_code}" "$HEALTH_URL")
    if [ "$unauthorized_status" != "403" ]; then
      echo "ERROR: Unauthenticated request returned HTTP $unauthorized_status, expected 403." >&2
      exit 1
    fi

    echo "==> Verifying hidden page: $OPENAI_URL"
    curl -fsS --max-time 10 -H "Cookie: $AUTH_COOKIE" "$OPENAI_URL" >/dev/null
    echo "==> Ready: $HEALTH_URL"
    docker compose ps "$SERVICE_NAME" nginx
    exit 0
  fi

  if [ "$attempt" -eq 60 ]; then
    echo "ERROR: Site did not become healthy after 60 attempts." >&2
    echo "Recent logs:" >&2
    docker compose logs --tail=80 "$SERVICE_NAME" nginx >&2
    exit 1
  fi

  sleep 2
done
