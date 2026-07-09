#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="langchain-docs-zh-static"
HEALTH_URL="${HEALTH_URL:-http://localhost:33031}"
EXPORT_ZIP="$ROOT_DIR/build/export.zip"
STATIC_DIR="$ROOT_DIR/build/static-site"

cd "$ROOT_DIR"

if [ "${REBUILD_EXPORT:-0}" = "1" ] || [ ! -f "$EXPORT_ZIP" ]; then
  echo "==> Building Chinese overlay"
  uv run python -m scripts.zh.overlay build

  echo "==> Building Mintlify input"
  PYTHONPATH="$ROOT_DIR" uv run pipeline build --src-dir .generated/zh/src --build-dir build

  echo "==> Exporting static site"
  (cd build && mint export --output export.zip)
fi

echo "==> Preparing static site directory"
rm -rf "$STATIC_DIR"
mkdir -p "$STATIC_DIR"
unzip -q "$EXPORT_ZIP" -d "$STATIC_DIR"

if [ ! -f "$STATIC_DIR/index.html" ]; then
  echo "ERROR: Static export is missing index.html after unzip." >&2
  exit 1
fi

echo "==> Building static site image"
docker compose build "$SERVICE_NAME"

echo "==> Starting static container"
docker compose up -d --force-recreate "$SERVICE_NAME"

echo "==> Waiting for site: $HEALTH_URL"
for attempt in $(seq 1 30); do
  if curl -fsS --max-time 5 "$HEALTH_URL" >/dev/null 2>&1; then
    echo "==> Ready: $HEALTH_URL"
    docker compose ps "$SERVICE_NAME"
    exit 0
  fi

  if [ "$attempt" -eq 30 ]; then
    echo "ERROR: Static site did not become healthy after 30 attempts." >&2
    echo "Recent logs:" >&2
    docker compose logs --tail=80 "$SERVICE_NAME" >&2
    exit 1
  fi

  sleep 1
done
