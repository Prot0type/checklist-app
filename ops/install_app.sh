#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
APP_DIR="${APP_DIR:-${REPO_ROOT}}"
VENV_DIR="${VENV_DIR:-${APP_DIR}/.venv}"
RUN_TESTS="${RUN_TESTS:-1}"

cd "${APP_DIR}"

python3 -m venv "${VENV_DIR}"
source "${VENV_DIR}/bin/activate"

python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .

if [[ "${RUN_TESTS}" == "1" ]]; then
  python -m unittest discover -s tests -v
  python -m compileall checklist_app tests checklist discord fotmob >/dev/null
fi

python -m checklist_app --help >/dev/null

echo "Application install complete."
echo "Virtualenv: ${VENV_DIR}"
