#!/usr/bin/env bash
# Makes sure Docker is running before local Supabase starts.
# On macOS it opens Docker Desktop and waits for its engine, so `make dev` works from a cold start.
set -euo pipefail

if docker info >/dev/null 2>&1; then
  exit 0
fi

if [[ "$(uname)" == "Darwin" ]] && open -Ra Docker 2>/dev/null; then
  echo "Starting Docker Desktop..."
  open -a Docker
  for _ in $(seq 1 90); do
    if docker info >/dev/null 2>&1; then
      echo "Docker is running."
      exit 0
    fi
    sleep 2
  done
  echo "Docker Desktop did not start within 3 minutes. Open it, wait until it says Engine running, then try again." >&2
  exit 1
fi

echo "Docker is not running. Install Docker Desktop, open it, wait until it says Engine running, then try again." >&2
exit 1
