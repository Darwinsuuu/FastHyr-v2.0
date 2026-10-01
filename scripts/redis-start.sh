#!/usr/bin/env bash
# Starts local Redis for the job queue (FND-008) in a Docker container named fasthyr-redis.
# Its data is throwaway: Postgres holds the state that matters (ADR-009).
set -euo pipefail

"$(dirname "$0")/ensure-docker.sh"

NAME=fasthyr-redis
IMAGE=redis:7-alpine

if [[ "$(docker inspect -f '{{.State.Running}}' "$NAME" 2>/dev/null || true)" == "true" ]]; then
  exit 0
fi

if docker inspect "$NAME" >/dev/null 2>&1; then
  docker start "$NAME" >/dev/null
else
  docker run -d --name "$NAME" -p 6379:6379 "$IMAGE" >/dev/null
fi
echo "Redis is running on 127.0.0.1:6379."
