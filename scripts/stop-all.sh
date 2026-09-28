#!/usr/bin/env bash
# Stops everything `make dev` started: the web app and API, local Supabase, then Docker Desktop (macOS).
set -uo pipefail

echo "Stopping the web app and API..."
for port in 3000 8000; do
  pids=$(lsof -ti "tcp:$port" -sTCP:LISTEN 2>/dev/null || true)
  if [[ -n "$pids" ]]; then
    kill $pids 2>/dev/null || true
  fi
done

if docker info >/dev/null 2>&1; then
  echo "Stopping Supabase..."
  pnpm supabase stop
fi

if [[ "$(uname)" == "Darwin" ]]; then
  echo "Quitting Docker Desktop..."
  osascript -e 'quit app "Docker"' 2>/dev/null || true
fi

echo "FastHyr is stopped. Your local data is kept."
