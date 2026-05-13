#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

IMAGE_TAG="${IMAGE_TAG:-neolore-queue-analytics:teamcity-${BUILD_NUMBER:-local}}"
docker build -t "$IMAGE_TAG" .
