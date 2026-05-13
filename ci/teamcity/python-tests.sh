#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest -q

deactivate

python3 -m venv functions/.venv
. functions/.venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r functions/requirements.txt pytest
python -m pytest functions/tests -v
