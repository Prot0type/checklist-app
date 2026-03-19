from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _first_existing_path(candidates: list[str]) -> str | None:
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return None


def _env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return int(raw_value)


def _resolve_path(root: Path, raw_value: str | None, default_relative: str) -> Path:
    candidate = Path(raw_value) if raw_value else root / default_relative
    if not candidate.is_absolute():
        candidate = root / candidate
    return candidate.resolve()


@dataclass(frozen=True, slots=True)
class Settings:
    project_root: Path
    aws_region: str
    checklist_table_name: str
    match_data_table_name: str
    discord_bot_token: str
    discord_channel_id: str
    csv_directory: Path
    log_directory: Path
    display_timezone: str
    monitor_poll_seconds: int
    per_match_sleep_min_seconds: int
    per_match_sleep_max_seconds: int
    round_sleep_min_seconds: int
    round_sleep_max_seconds: int
    fotmob_wait_timeout_seconds: int
    fotmob_chrome_binary: str | None
    fotmob_chromedriver_path: str | None

    @classmethod
    def from_env(cls, project_root: Path | None = None) -> "Settings":
        root = (project_root or Path.cwd()).resolve()
        detected_chrome_binary = _first_existing_path(
            [
                "/snap/chromium/current/usr/lib/chromium-browser/chrome",
                "/usr/bin/chromium",
                "/usr/bin/chromium-browser",
                "/usr/bin/google-chrome",
            ]
        )
        detected_chromedriver = _first_existing_path(
            [
                "/snap/chromium/current/usr/lib/chromium-browser/chromedriver",
                "/usr/bin/chromedriver",
            ]
        )

        settings = cls(
            project_root=root,
            aws_region=os.getenv("CHECKLIST_AWS_REGION", "us-west-2"),
            checklist_table_name=os.getenv("CHECKLIST_TABLE_NAME", "Checklist"),
            match_data_table_name=os.getenv("MATCH_DATA_TABLE_NAME", "MatchData"),
            discord_bot_token=os.getenv("DISCORD_BOT_TOKEN", ""),
            discord_channel_id=os.getenv("DISCORD_CHANNEL_ID", ""),
            csv_directory=_resolve_path(root, os.getenv("CHECKLIST_CSV_DIRECTORY"), "checklist_csvs"),
            log_directory=_resolve_path(root, os.getenv("CHECKLIST_LOG_DIRECTORY"), "logs"),
            display_timezone=os.getenv("CHECKLIST_DISPLAY_TIMEZONE", "US/Eastern"),
            monitor_poll_seconds=_env_int("CHECKLIST_MONITOR_POLL_SECONDS", 300),
            per_match_sleep_min_seconds=_env_int("CHECKLIST_PER_MATCH_SLEEP_MIN_SECONDS", 3),
            per_match_sleep_max_seconds=_env_int("CHECKLIST_PER_MATCH_SLEEP_MAX_SECONDS", 8),
            round_sleep_min_seconds=_env_int("CHECKLIST_ROUND_SLEEP_MIN_SECONDS", 40),
            round_sleep_max_seconds=_env_int("CHECKLIST_ROUND_SLEEP_MAX_SECONDS", 50),
            fotmob_wait_timeout_seconds=_env_int("CHECKLIST_FOTMOB_WAIT_TIMEOUT_SECONDS", 20),
            fotmob_chrome_binary=os.getenv("CHECKLIST_FOTMOB_CHROME_BINARY", detected_chrome_binary or ""),
            fotmob_chromedriver_path=os.getenv("CHECKLIST_FOTMOB_CHROMEDRIVER_PATH", detected_chromedriver or ""),
        )

        if settings.per_match_sleep_min_seconds > settings.per_match_sleep_max_seconds:
            raise ValueError("Per-match sleep min cannot be greater than max.")
        if settings.round_sleep_min_seconds > settings.round_sleep_max_seconds:
            raise ValueError("Round sleep min cannot be greater than max.")
        return settings

    @property
    def discord_configured(self) -> bool:
        return bool(self.discord_bot_token and self.discord_channel_id)
