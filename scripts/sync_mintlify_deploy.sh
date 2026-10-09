#!/usr/bin/env bash
# Sync the Chinese docs build output to the Mintlify deploy branch.
#
# Mintlify cloud hosting builds the deploy branch directly (docs.json must sit
# at the branch root), but this repo keeps docs.json in src/ and needs the
# custom pipeline before mint, so the deploy branch holds only generated
# content from build/. Do not edit the deploy branch by hand; rerun this
# script to update it.
#
# Usage:
#   ./scripts/sync_mintlify_deploy.sh              # run make build-zh, then sync
#   ./scripts/sync_mintlify_deploy.sh --no-build   # reuse the existing build/
#
# Environment overrides:
#   BRANCH        deploy branch name (default: mintlify-deploy-zh)
#   BUILD_TARGET  make target that produces build/ (default: build-zh)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BRANCH="${BRANCH:-mintlify-deploy-zh}"
BUILD_TARGET="${BUILD_TARGET:-build-zh}"

cd "$ROOT"

if [[ "${1:-}" != "--no-build" ]]; then
  make "$BUILD_TARGET"
fi

if [[ ! -f build/docs.json ]]; then
  echo "Error: build/docs.json missing. Run make $BUILD_TARGET first." >&2
  exit 1
fi

git fetch origin "$BRANCH" 2>/dev/null || true

WORKTREE="$(mktemp -d)/$BRANCH"
if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git worktree add "$WORKTREE" "$BRANCH"
elif git show-ref --verify --quiet "refs/remotes/origin/$BRANCH"; then
  git worktree add -b "$BRANCH" "$WORKTREE" "origin/$BRANCH"
else
  git worktree add --orphan -b "$BRANCH" "$WORKTREE"
fi

rsync -a --delete --exclude .git build/ "$WORKTREE"/

SRC_SHA="$(git rev-parse --short HEAD)"
STAMP="$(date '+%Y-%m-%d %H:%M:%S')"

cd "$WORKTREE"
git add -A
if git diff --cached --quiet; then
  echo "No changes; deploy branch $BRANCH is up to date with build/ from $SRC_SHA."
else
  git commit -m "Mintlify deploy: $BUILD_TARGET output from $SRC_SHA ($STAMP)"
  git push -u origin "$BRANCH"
fi

cd "$ROOT"
git worktree remove "$WORKTREE"
