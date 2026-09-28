#!/usr/bin/env bash
# Makes sure Docker is running before local Supabase starts.
# On macOS it opens Docker Desktop and waits for its engine, so `make dev` works from a cold start.
set -uo pipefail

source "$(dirname "$0")/docker-ready.sh"

if docker_ready; then
  exit 0
fi

if [[ "$(uname)" == "Darwin" ]] && open -Ra Docker 2>/dev/null; then
  echo "Starting Docker Desktop (this can take a minute)..."
  for _ in $(seq 1 36); do
    # Asking again is harmless and recovers when Docker Desktop was still quitting.
    open -a Docker
    if docker_ready; then
      echo "Docker is running."
      exit 0
    fi
    sleep 2
  done
  echo "Docker Desktop did not start within about 4 minutes. Open it, wait until it says Engine running, then try again." >&2
  exit 1
fi

echo "Docker is not running. Install Docker Desktop, open it, wait until it says Engine running, then try again." >&2
exit 1
