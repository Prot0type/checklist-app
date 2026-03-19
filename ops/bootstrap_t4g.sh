#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PACKAGE_FILE="${SCRIPT_DIR}/ubuntu-24.04-t4g-apt-packages.txt"
APP_USER="${APP_USER:-ubuntu}"
APP_DIR="${APP_DIR:-/opt/checklist-app}"
CONFIG_DIR="${CONFIG_DIR:-/etc/checklist-app}"
LOG_DIR="${LOG_DIR:-/var/log/checklist-app}"

if [[ ! -f "${PACKAGE_FILE}" ]]; then
  echo "Package file not found: ${PACKAGE_FILE}" >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

apt-get update
xargs -a "${PACKAGE_FILE}" apt-get install -y

if ! snap list chromium >/dev/null 2>&1; then
  snap install chromium
fi

mkdir -p "${APP_DIR}" "${CONFIG_DIR}" "${LOG_DIR}"
if id "${APP_USER}" >/dev/null 2>&1; then
  chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}" "${LOG_DIR}"
fi

echo "Bootstrap complete."
echo "Chromium binary: /snap/chromium/current/usr/lib/chromium-browser/chrome"
echo "Chromedriver:   /snap/chromium/current/usr/lib/chromium-browser/chromedriver"
echo "App directory:  ${APP_DIR}"
echo "Config dir:     ${CONFIG_DIR}"
echo "Log directory:  ${LOG_DIR}"
