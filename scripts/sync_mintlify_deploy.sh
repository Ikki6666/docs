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
TMP_DIR=""
WORKTREE=""

cleanup() {
  cd "$ROOT"
  if [[ -n "$WORKTREE" ]]; then
    git worktree remove --force "$WORKTREE" >/dev/null 2>&1 || true
  fi
  if [[ -n "$TMP_DIR" ]]; then
    rm -rf "$TMP_DIR"
  fi
  # Remove metadata for worktrees whose directories are already gone.
  git worktree prune
}
trap cleanup EXIT

cd "$ROOT"

if [[ "${1:-}" != "--no-build" ]]; then
  make "$BUILD_TARGET"
fi

if [[ ! -f build/docs.json ]]; then
  echo "Error: build/docs.json missing. Run make $BUILD_TARGET first." >&2
  exit 1
fi

git worktree prune

if ! remote_ref=$(git ls-remote --heads origin "refs/heads/$BRANCH"); then
  echo "Error: cannot query origin for branch $BRANCH." >&2
  exit 1
fi

if [[ -n "$remote_ref" ]]; then
  git fetch origin "$BRANCH"
fi

TMP_DIR="$(cd "$(mktemp -d)" && pwd -P)"
WORKTREE="$TMP_DIR/$BRANCH"

if git show-ref --verify --quiet "refs/remotes/origin/$BRANCH"; then
  # The deploy branch is generated content, so rebuild it from origin instead
  # of trusting a local branch that may be stale.
  git worktree add -q -B "$BRANCH" "$WORKTREE" "origin/$BRANCH"
else
  git worktree add -q --orphan -b "$BRANCH" "$WORKTREE"
fi

rsync -a --delete --exclude .git build/ "$WORKTREE"/

SRC_SHA="$(git rev-parse --short HEAD)"
STAMP="$(date '+%Y-%m-%d %H:%M:%S')"

cd "$WORKTREE"
git add -A
if git diff --cached --quiet; then
  echo "No changes; deploy branch $BRANCH is up to date with build/ from $SRC_SHA."
  exit 0
fi

git commit -m "Mintlify deploy: $BUILD_TARGET output from $SRC_SHA ($STAMP)"
git push -u origin "$BRANCH"
