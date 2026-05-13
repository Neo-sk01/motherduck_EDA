#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"
. ci/teamcity/lib.sh

require_command docker
require_env \
  AZURE_CLIENT_ID \
  AZURE_CLIENT_SECRET \
  AZURE_TENANT_ID \
  AZURE_SUBSCRIPTION_ID \
  AZURE_RESOURCE_GROUP \
  ACR_NAME \
  CONTAINER_APP_JOB_NAME

ACR_LOGIN_SERVER="${ACR_NAME}.azurecr.io"
REVISION="$(short_revision)"
IMAGE="${ACR_LOGIN_SERVER}/neolore-pipeline:${REVISION}"
LATEST_IMAGE="${ACR_LOGIN_SERVER}/neolore-pipeline:latest"

printf '%s\n' "$AZURE_CLIENT_SECRET" | docker login "$ACR_LOGIN_SERVER" \
  --username "$AZURE_CLIENT_ID" \
  --password-stdin

docker build -t "$IMAGE" -t "$LATEST_IMAGE" .
docker push "$IMAGE"
docker push "$LATEST_IMAGE"

azure_cli "
  az containerapp job update \
    --name \"\$CONTAINER_APP_JOB_NAME\" \
    --resource-group \"\$AZURE_RESOURCE_GROUP\" \
    --image \"$IMAGE\" \
    --output none
"
