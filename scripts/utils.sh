#!/bin/bash
# Shared utility functions for scripts.

info()    { echo "===> $*"; }
success() { echo ""; echo "✅  $*"; }

require_commands() {
  for cmd in "$@"; do
    if ! command -v "$cmd" &>/dev/null; then
      echo "ERROR: '$cmd' is required but not found in PATH." >&2
      exit 1
    fi
  done
}

confirm() {
  echo ""
  read -rp "$* [y/N] " answer
  if [[ "${answer}" != "y" && "${answer}" != "Y" ]]; then
    echo "Aborted."
    exit 0
  fi
}

# Usage: prompt_gh secret|variable NAME "Description"
prompt_gh() {
  local type="$1"
  local name="$2"
  local description="$3"
  local value

  read -rp "  ${description} (${name}): " value
  if [[ -z "${value}" ]]; then
    return
  fi
  gh "${type}" set "${name}" --body "${value}"
}
