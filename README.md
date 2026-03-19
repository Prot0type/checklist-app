# checklist-app

This project tracks soccer betting checklists from CSV files, stores match state in DynamoDB, watches those matches live through FotMob, and posts checklist updates into Discord.

## What Changed

The repo now has a real application package in `checklist_app/` with:

- typed domain models for wagers, match state, and checklist records
- isolated integrations for Discord and FotMob
- repository boundaries for DynamoDB and in-memory testing
- service objects for CSV import, checklist execution, and monitoring
- a CLI entrypoint instead of only ad hoc scripts
- compatibility wrappers so the old script locations still work
- unit tests around the core behavior

The old codebase was mostly procedural scripts with import-time side effects and hardcoded infrastructure assumptions. The new structure is meant to be a foundation we can extend cleanly.

## Architecture

- `checklist_app/domain/`: the core data model and settlement logic
- `checklist_app/integrations/`: Discord publishing and FotMob scraping
- `checklist_app/repositories/`: persistence contracts plus DynamoDB implementations
- `checklist_app/services/`: checklist import, execution, monitor, and cleanup workflows
- `checklist_app/cli.py`: operational entrypoint

## Environment

The app reads configuration from environment variables.

- `DISCORD_BOT_TOKEN`
- `DISCORD_CHANNEL_ID`
- `CHECKLIST_AWS_REGION`
- `CHECKLIST_TABLE_NAME`
- `MATCH_DATA_TABLE_NAME`
- `CHECKLIST_CSV_DIRECTORY`
- `CHECKLIST_LOG_DIRECTORY`
- `CHECKLIST_DISPLAY_TIMEZONE`
- `CHECKLIST_MONITOR_POLL_SECONDS`
- `CHECKLIST_PER_MATCH_SLEEP_MIN_SECONDS`
- `CHECKLIST_PER_MATCH_SLEEP_MAX_SECONDS`
- `CHECKLIST_ROUND_SLEEP_MIN_SECONDS`
- `CHECKLIST_ROUND_SLEEP_MAX_SECONDS`
- `CHECKLIST_FOTMOB_WAIT_TIMEOUT_SECONDS`
- `CHECKLIST_FOTMOB_CHROME_BINARY`
- `CHECKLIST_FOTMOB_CHROMEDRIVER_PATH`

See `.env.example` for a starter template. On the tested Ubuntu 24.04 ARM server, the Chromium binary and Chromedriver paths are auto-detected if those two FotMob variables are left blank.

## CLI

Import a CSV:

```bash
python -m checklist_app import-csv scythe-test-1.csv
```

Run a checklist once:

```bash
python -m checklist_app run-checklist scythe-test-1 --once
```

Run the monitor loop:

```bash
python -m checklist_app monitor
```

Run a single monitor scan in the foreground:

```bash
python -m checklist_app monitor --once --foreground
```

## Legacy Scripts

The historical scripts under `checklist/` are now compatibility shims that call the new application package. They are still there so older muscle memory and ad hoc workflows do not break while we keep modernizing the repo.

## Server Build

The tested Ubuntu 24.04 ARM (`t4g`) rebuild guide lives in [docs/t4g-server-setup.md](docs/t4g-server-setup.md).

## Deployment Contract

The server deployment is intentionally simple:

- repo contents copied or cloned to `/opt/checklist-app`
- Python virtualenv created at `/opt/checklist-app/.venv`
- runtime config stored in `/etc/checklist-app/checklist-app.env`
- logs written under `/var/log/checklist-app`
- optional long-running worker managed by `systemd`

The source of truth for dependencies is split by layer:

- Python dependencies: `pyproject.toml`
- Ubuntu system packages: `ops/ubuntu-24.04-t4g-apt-packages.txt`
- server bootstrap and install steps: `ops/bootstrap_t4g.sh`, `ops/install_app.sh`, and `ops/rebuild_t4g.sh`
- environment variables: `.env.example` and `ops/checklist-app.env.example`

The operational assets for that server live in `ops/`:

- `ops/bootstrap_t4g.sh`
- `ops/install_app.sh`
- `ops/rebuild_t4g.sh`
- `ops/smoke_test_t4g.sh`
- `ops/checklist-app-monitor.service`
- `ops/checklist-app.env.example`
