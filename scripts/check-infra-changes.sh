#!/usr/bin/env bash
set -euo pipefail

INFRA_PATHS=(
  "^infra/"
  "^\.platform/"
  "^scripts/"
  "^proxy/"
  "^\.github/"
  "Dockerfile$"
  "^docker-compose\.yml$"
  "\.dockerignore$"
)

PATTERN=$(IFS="|"; echo "${INFRA_PATHS[*]}")
CHANGED=$(git diff --name-only HEAD~1 HEAD)

MATCHES=$(echo "$CHANGED" | grep -E "$PATTERN" || true)

if [[ -n "$MATCHES" ]]; then
  echo "Infrastructure changes detected:"
  echo "$MATCHES"
  exit 0
else
  echo "No infrastructure changes detected"
  exit 1
fi
