#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/checklist-app}"
APP_USER="${APP_USER:-ubuntu}"
TARGET_BRANCH="${TARGET_BRANCH:-main}"
REPO_URL="${REPO_URL:-https://github.com/Prot0type/checklist-app.git}"
WRITE_ENV_FILE="${WRITE_ENV_FILE:-1}"
RUN_SMOKE_TEST="${RUN_SMOKE_TEST:-1}"
INSTALL_SERVICE="${INSTALL_SERVICE:-1}"
ENABLE_MONITOR_SERVICE="${ENABLE_MONITOR_SERVICE:-0}"
ENV_FILE="${ENV_FILE:-/etc/checklist-app/checklist-app.env}"

if ! id "${APP_USER}" >/dev/null 2>&1; then
  echo "Application user '${APP_USER}' does not exist." >&2
  exit 1
fi

mkdir -p "$(dirname "${APP_DIR}")"

if [[ ! -d "${APP_DIR}/.git" ]]; then
  git clone "${REPO_URL}" "${APP_DIR}"
  chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"
fi

git config --global --add safe.directory "${APP_DIR}"
sudo -u "${APP_USER}" git config --global --add safe.directory "${APP_DIR}"

sudo -u "${APP_USER}" bash -lc "
  set -euo pipefail
  cd '${APP_DIR}'
  git fetch origin '${TARGET_BRANCH}'
  git checkout '${TARGET_BRANCH}'
  git reset --hard 'origin/${TARGET_BRANCH}'
  bash ops/install_app.sh
"

if [[ "${WRITE_ENV_FILE}" == "1" ]]; then
  bash "${APP_DIR}/ops/render_server_env.sh" "${ENV_FILE}"
fi

if [[ "${INSTALL_SERVICE}" == "1" ]]; then
  cp "${APP_DIR}/ops/checklist-app-monitor.service" /etc/systemd/system/checklist-app-monitor.service
  systemctl daemon-reload

  if [[ "${ENABLE_MONITOR_SERVICE}" == "1" ]]; then
    systemctl enable checklist-app-monitor.service
    systemctl restart checklist-app-monitor.service
  elif systemctl is-enabled checklist-app-monitor.service >/dev/null 2>&1; then
    systemctl restart checklist-app-monitor.service
  fi
fi

if [[ "${RUN_SMOKE_TEST}" == "1" ]]; then
  sudo -u "${APP_USER}" bash -lc "
    set -euo pipefail
    cd '${APP_DIR}'
    bash ops/smoke_test_t4g.sh
  "
fi

echo "Instance application deploy complete."
