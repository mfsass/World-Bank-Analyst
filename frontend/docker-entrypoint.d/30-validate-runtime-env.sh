#!/bin/sh
set -eu

runtime_env="${WORLD_ANALYST_RUNTIME_ENV:-local}"

if [ "$runtime_env" = "local" ]; then
  exit 0
fi

if [ -z "${WORLD_ANALYST_API_UPSTREAM:-}" ] || [ "${WORLD_ANALYST_API_UPSTREAM}" = "http://world-analyst-api:8080/api/v1/" ]; then
  echo >&2 "WORLD_ANALYST_API_UPSTREAM must be set explicitly when WORLD_ANALYST_RUNTIME_ENV is not local."
  exit 1
fi

if [ -z "${WORLD_ANALYST_PROXY_API_KEY:-}" ] || [ "${WORLD_ANALYST_PROXY_API_KEY}" = "local-dev" ]; then
  echo >&2 "WORLD_ANALYST_PROXY_API_KEY must be set explicitly when WORLD_ANALYST_RUNTIME_ENV is not local."
  exit 1
fi
