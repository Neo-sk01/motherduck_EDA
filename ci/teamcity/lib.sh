#!/usr/bin/env bash
set -Eeuo pipefail

tc_note() {
  printf '##teamcity[message text=%q]\n' "$*"
}

require_env() {
  local missing=0
  for name in "$@"; do
    if [[ -z "${!name:-}" ]]; then
      printf 'Missing required environment variable: %s\n' "$name" >&2
      missing=1
    fi
  done
  if [[ "$missing" -ne 0 ]]; then
    exit 2
  fi
}

require_command() {
  local missing=0
  for name in "$@"; do
    if ! command -v "$name" >/dev/null 2>&1; then
      printf 'Missing required command on TeamCity agent: %s\n' "$name" >&2
      missing=1
    fi
  done
  if [[ "$missing" -ne 0 ]]; then
    exit 2
  fi
}

short_revision() {
  if [[ -n "${BUILD_VCS_NUMBER:-}" ]]; then
    printf '%s' "${BUILD_VCS_NUMBER:0:12}"
    return
  fi
  git rev-parse --short=12 HEAD
}

azure_cli() {
  require_env AZURE_CLIENT_ID AZURE_CLIENT_SECRET AZURE_TENANT_ID AZURE_SUBSCRIPTION_ID
  require_command docker

  docker run --rm \
    -e AZURE_CLIENT_ID \
    -e AZURE_CLIENT_SECRET \
    -e AZURE_TENANT_ID \
    -e AZURE_SUBSCRIPTION_ID \
    -e AZURE_RESOURCE_GROUP \
    -e ACR_NAME \
    -e CONTAINER_APP_JOB_NAME \
    -e FUNCTION_APP_NAME \
    -e FUNCTION_STORAGE_ACCOUNT \
    -e FUNCTION_RELEASE_CONTAINER \
    -v "$PWD:/work" \
    -w /work \
    mcr.microsoft.com/azure-cli:2.66.0 \
    /bin/sh -lc "
      set -eu
      az login --service-principal \
        --username \"\$AZURE_CLIENT_ID\" \
        --password \"\$AZURE_CLIENT_SECRET\" \
        --tenant \"\$AZURE_TENANT_ID\" >/dev/null
      az account set --subscription \"\$AZURE_SUBSCRIPTION_ID\"
      $*
    "
}
