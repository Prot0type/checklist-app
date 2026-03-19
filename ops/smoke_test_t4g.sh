#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${VENV_DIR:-${REPO_ROOT}/.venv}"

source "${VENV_DIR}/bin/activate"

python -m unittest discover -s tests -v
python -m checklist_app --help >/dev/null

python - <<'PY'
import boto3
from checklist_app.config import Settings
from checklist_app.integrations.fotmob_client import FotMobClient

settings = Settings.from_env()
print({
    "chrome_binary": settings.fotmob_chrome_binary,
    "chromedriver_path": settings.fotmob_chromedriver_path,
})

identity = boto3.client("sts", region_name=settings.aws_region).get_caller_identity()
print({"account": identity["Account"], "arn": identity["Arn"]})

client = FotMobClient(
    wait_timeout_seconds=settings.fotmob_wait_timeout_seconds,
    chrome_binary=settings.fotmob_chrome_binary,
    chromedriver_path=settings.fotmob_chromedriver_path,
)
try:
    state = client.fetch_match_state("athletic-club-vs-mallorca/2dsrjx#4506857")
    print({
        "home_team": state.home_team,
        "away_team": state.away_team,
        "start_time": state.start_time.isoformat(),
        "status": state.status.value,
        "score": state.score,
    })
finally:
    client.close()
PY

echo "Smoke test complete."
