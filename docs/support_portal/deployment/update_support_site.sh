#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${WHISPERWOOD_SUPPORT_REPO_DIR:-/opt/whisperwood-support-site/repo}"
BRANCH="${WHISPERWOOD_SUPPORT_BRANCH:-main}"

if [ ! -d "$REPO_DIR/.git" ]; then
  echo "Repository not found at: $REPO_DIR" >&2
  echo "Clone the repository first, then run this script again." >&2
  exit 1
fi

cd "$REPO_DIR"
git fetch origin "$BRANCH"
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

if [ ! -f "$REPO_DIR/docs/support_portal/index.html" ]; then
  echo "Support site index.html was not found after update." >&2
  exit 1
fi

echo "Whisperwood support site updated from GitHub."
