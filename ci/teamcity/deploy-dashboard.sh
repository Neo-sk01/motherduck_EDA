#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR/dashboard"

if [[ -z "${SWA_DEPLOYMENT_TOKEN:-}" ]]; then
  printf 'Missing required environment variable: SWA_DEPLOYMENT_TOKEN\n' >&2
  exit 2
fi
if [[ -z "${VITE_REPORTS_BASE_URL:-}" ]]; then
  printf 'Missing required environment variable: VITE_REPORTS_BASE_URL\n' >&2
  exit 2
fi

npm ci
npm test -- --run
VITE_REPORTS_BASE_URL="$VITE_REPORTS_BASE_URL" npm run build
npx -y @azure/static-web-apps-cli@2 deploy ./dist \
  --deployment-token "$SWA_DEPLOYMENT_TOKEN" \
  --env production
