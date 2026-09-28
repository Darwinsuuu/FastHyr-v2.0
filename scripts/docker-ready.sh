#!/usr/bin/env bash
# Shared helper, sourced by the other scripts.

# `docker info` can hang while Docker Desktop is starting or quitting, so give it 5 seconds.
docker_ready() {
  docker info >/dev/null 2>&1 &
  local pid=$!
  for _ in $(seq 1 10); do
    if ! kill -0 "$pid" 2>/dev/null; then
      wait "$pid"
      return $?
    fi
    sleep 0.5
  done
  kill "$pid" 2>/dev/null
  wait "$pid" 2>/dev/null
  return 1
}
