#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
APP_USER="${APP_USER:-ubuntu}"
APP_DIR="${APP_DIR:-${REPO_ROOT}}"
CONFIG_DIR="${CONFIG_DIR:-/etc/checklist-app}"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run this script with sudo so it can install system packages." >&2
  exit 1
fi

bash "${SCRIPT_DIR}/bootstrap_t4g.sh"

if id "${APP_USER}" >/dev/null 2>&1; then
  chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"
  runuser -u "${APP_USER}" -- env APP_DIR="${APP_DIR}" bash "${SCRIPT_DIR}/install_app.sh"
else
  APP_DIR="${APP_DIR}" bash "${SCRIPT_DIR}/install_app.sh"
fi

mkdir -p "${CONFIG_DIR}"
if [[ ! -f "${CONFIG_DIR}/checklist-app.env" ]]; then
  cp "${SCRIPT_DIR}/checklist-app.env.example" "${CONFIG_DIR}/checklist-app.env"
  echo "Created ${CONFIG_DIR}/checklist-app.env from the example file."
fi

echo "Rebuild complete."
echo "Next steps:"
echo "  1. Fill in ${CONFIG_DIR}/checklist-app.env"
echo "  2. Run: bash ${SCRIPT_DIR}/smoke_test_t4g.sh"
echo "  3. Optionally install ops/checklist-app-monitor.service"
