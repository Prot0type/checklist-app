# T4G Server Setup

This is the rebuild guide for the Ubuntu 24.04 ARM (`t4g`) worker we tested through SSM.

## What This Deploys

- Ubuntu 24.04 ARM EC2 instance
- SSM-managed access
- Chromium and Chromedriver from the `chromium` snap
- Python app installed from this repo into a virtualenv
- Optional `systemd` service for the monitor worker

The app is designed around a single active worker on the instance at a time. That is intentional for cost and stability on a small box.

## Proven Runtime

The following combination was smoke-tested successfully on the `t4g`:

- Ubuntu 24.04.4 LTS
- Python 3.12
- Chromium `146.0.7680.80`
- Chromedriver `146.0.7680.80`
- Selenium using the direct snap-mounted binaries:
  - `/snap/chromium/current/usr/lib/chromium-browser/chrome`
  - `/snap/chromium/current/usr/lib/chromium-browser/chromedriver`

## Preconditions

1. Launch an Ubuntu 24.04 ARM EC2 instance.
2. Attach an instance role with `AmazonSSMManagedInstanceCore`.
3. Confirm the instance is reachable in Systems Manager.
4. Clone this repo to `/opt/checklist-app` or copy the repo contents there.

## Bootstrap System Packages

Run on the server:

```bash
cd /opt/checklist-app
sudo bash ops/bootstrap_t4g.sh
```

This installs:

- `python3-pip`
- `python3-venv`
- the Chromium runtime libraries we proved were required on Ubuntu 24.04 ARM
- the `chromium` snap

## Install The App

Run on the server:

```bash
cd /opt/checklist-app
bash ops/install_app.sh
```

That creates `.venv/`, installs the project in editable mode, runs the unit tests, and verifies the CLI starts.

If you want the shortest rebuild path after copying the repo onto the server, use:

```bash
cd /opt/checklist-app
sudo bash ops/rebuild_t4g.sh
```

That wraps bootstrap, app installation, and creation of the initial env file in one command.

## Configure Environment

Create the runtime environment file:

```bash
sudo mkdir -p /etc/checklist-app
sudo cp ops/checklist-app.env.example /etc/checklist-app/checklist-app.env
sudo nano /etc/checklist-app/checklist-app.env
```

At minimum, fill in:

- `DISCORD_BOT_TOKEN`
- `DISCORD_CHANNEL_ID`
- `CHECKLIST_TABLE_NAME`
- `MATCH_DATA_TABLE_NAME`

The Chromium binary and driver paths are auto-detected in code on the tested `t4g` image, but they are included in the env example as explicit overrides if you want them pinned.

## Run A Smoke Test

Run on the server:

```bash
cd /opt/checklist-app
bash ops/smoke_test_t4g.sh
```

This checks:

- unit tests
- CLI startup
- AWS STS from the instance role
- live FotMob scraping via Selenium

## Install As A Service

Install the monitor worker:

```bash
sudo cp ops/checklist-app-monitor.service /etc/systemd/system/checklist-app-monitor.service
sudo systemctl daemon-reload
sudo systemctl enable checklist-app-monitor.service
sudo systemctl start checklist-app-monitor.service
sudo systemctl status checklist-app-monitor.service
```

View logs:

```bash
sudo journalctl -u checklist-app-monitor.service -f
```

## Rebuild Checklist

If the server is destroyed, the rebuild path is:

1. Launch fresh Ubuntu 24.04 ARM EC2
2. Attach SSM role
3. Copy or clone repo to `/opt/checklist-app`
4. `sudo bash ops/rebuild_t4g.sh`
5. Fill in `/etc/checklist-app/checklist-app.env`
6. `bash ops/smoke_test_t4g.sh`
7. Install/start `checklist-app-monitor.service`

## Notes

- This repo currently assumes a single active worker process on the instance.
- That is a good fit for a `t4g.small` and for keeping costs down.
- If we later introduce queued jobs or multiple execution workers, we should revisit memory sizing before increasing concurrency.
- The deployment source of truth is:
  - `pyproject.toml` for Python dependencies
  - `ops/ubuntu-24.04-t4g-apt-packages.txt` for Ubuntu packages
  - `ops/checklist-app.env.example` for server environment variables
