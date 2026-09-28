#!/usr/bin/env bash
# Stops everything `make dev` started: the web app and API, local Supabase, then Docker Desktop (macOS).
set -uo pipefail
source "$(dirname "$0")/docker-ready.sh"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Stopping the web app and API..."
# The dev servers of this checkout, found by their command line.
pkill -f "$ROOT/apps/web/node_modules/.bin/../next/dist/bin/next dev" 2>/dev/null || true
pkill -f "uvicorn app.main:app --reload --port 8000" 2>/dev/null || true
# Anything else still listening on the dev ports.
for port in 3000 8000; do
  pids=$(lsof -ti "tcp:$port" -sTCP:LISTEN 2>/dev/null || true)
  if [[ -n "$pids" ]]; then
    kill $pids 2>/dev/null || true
  fi
done

if docker_ready; then
  echo "Stopping Supabase..."
  pnpm supabase stop >/dev/null 2>&1 || true
fi

if [[ "$(uname)" == "Darwin" ]]; then
  echo "Quitting Docker Desktop..."
  osascript -e 'quit app "Docker"' 2>/dev/null || true
fi

echo "FastHyr is stopped. Your local data is kept."
