#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"
. ci/teamcity/lib.sh

require_command zip
require_env \
  AZURE_CLIENT_ID \
  AZURE_CLIENT_SECRET \
  AZURE_TENANT_ID \
  AZURE_SUBSCRIPTION_ID \
  AZURE_RESOURCE_GROUP \
  FUNCTION_APP_NAME \
  FUNCTION_STORAGE_ACCOUNT

FUNCTION_RELEASE_CONTAINER="${FUNCTION_RELEASE_CONTAINER:-scm-releases}"
export FUNCTION_RELEASE_CONTAINER
REVISION="$(short_revision)"
BLOB_NAME="functionapp-${REVISION}.zip"

python3 -m venv functions/.venv
. functions/.venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r functions/requirements.txt pytest
python -m pytest functions/tests -v
rm -rf functions/.python_packages
python -m pip install \
  -r functions/requirements.txt \
  --target=functions/.python_packages/lib/site-packages \
  --no-compile
deactivate

rm -f functionapp.zip
(
  cd functions
  zip -r ../functionapp.zip . \
    -x "tests/*" "**/__pycache__/*" "*.pyc" ".pytest_cache/*" ".venv/*"
)

azure_cli "
  az storage blob upload \
    --account-name \"\$FUNCTION_STORAGE_ACCOUNT\" \
    --container-name \"\$FUNCTION_RELEASE_CONTAINER\" \
    --name \"$BLOB_NAME\" \
    --file functionapp.zip \
    --auth-mode login \
    --overwrite \
    --output none

  BLOB_URL=\"https://\${FUNCTION_STORAGE_ACCOUNT}.blob.core.windows.net/\${FUNCTION_RELEASE_CONTAINER}/$BLOB_NAME\"

  az functionapp config appsettings set \
    --name \"\$FUNCTION_APP_NAME\" \
    --resource-group \"\$AZURE_RESOURCE_GROUP\" \
    --settings \"WEBSITE_RUN_FROM_PACKAGE=\$BLOB_URL\" \
    --output none

  az resource invoke-action \
    --resource-group \"\$AZURE_RESOURCE_GROUP\" \
    --name \"\$FUNCTION_APP_NAME\" \
    --resource-type Microsoft.Web/sites \
    --action syncfunctiontriggers \
    --output none
"
