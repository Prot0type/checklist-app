from __future__ import annotations

import logging
from dataclasses import dataclass
from collections.abc import Callable
from datetime import datetime, timezone
import random
import time

from checklist_app.config import Settings
from checklist_app.integrations.discord_client import DiscordClient, DiscordEmbedFormatter
from checklist_app.integrations.fotmob_client import FotMobClient
from checklist_app.repositories.dynamodb import DynamoChecklistRepository, DynamoMatchRepository
from checklist_app.repositories.protocols import ChecklistRepository, MatchRepository
from checklist_app.services.cleanup import ChecklistCleanupService
from checklist_app.services.executor import ChecklistExecutionService
from checklist_app.services.importer import ChecklistImportService
from checklist_app.services.monitor import ChecklistMonitorService


LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class Application:
    settings: Settings
    importer: ChecklistImportService
    executor: ChecklistExecutionService
    monitor: ChecklistMonitorService
    fotmob_client: FotMobClient

    def close(self) -> None:
        self.fotmob_client.close()


def build_application(
    settings: Settings | None = None,
    *,
    checklist_repository: ChecklistRepository | None = None,
    match_repository: MatchRepository | None = None,
    discord_client: DiscordClient | None = None,
    fotmob_client: FotMobClient | None = None,
    sleep_fn: Callable[[float], None] | None = None,
    randint_fn: Callable[[int, int], int] | None = None,
    now_fn: Callable[[], datetime] | None = None,
    run_monitor_in_background: bool = True,
) -> Application:
    settings = settings or Settings.from_env()

    if checklist_repository is None or match_repository is None:
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover - depends on runtime environment
            raise RuntimeError("boto3 is required to use the DynamoDB repositories.") from exc

        dynamodb = boto3.resource("dynamodb", region_name=settings.aws_region)
        checklist_repository = checklist_repository or DynamoChecklistRepository(
            dynamodb.Table(settings.checklist_table_name)
        )
        match_repository = match_repository or DynamoMatchRepository(
            dynamodb.Table(settings.match_data_table_name)
        )

    discord_client = discord_client or DiscordClient(
        bot_token=settings.discord_bot_token,
        channel_id=settings.discord_channel_id,
        formatter=DiscordEmbedFormatter(timezone_name=settings.display_timezone),
    )
    fotmob_client = fotmob_client or FotMobClient(
        wait_timeout_seconds=settings.fotmob_wait_timeout_seconds,
        chrome_binary=settings.fotmob_chrome_binary,
        chromedriver_path=settings.fotmob_chromedriver_path,
    )

    importer = ChecklistImportService(
        checklist_repository=checklist_repository,
        match_repository=match_repository,
        fotmob_client=fotmob_client,
        discord_client=discord_client,
        csv_directory=settings.csv_directory,
    )
    executor = ChecklistExecutionService(
        checklist_repository=checklist_repository,
        match_repository=match_repository,
        fotmob_client=fotmob_client,
        discord_client=discord_client,
        log_directory=settings.log_directory,
        per_match_sleep_range=(
            settings.per_match_sleep_min_seconds,
            settings.per_match_sleep_max_seconds,
        ),
        round_sleep_range=(
            settings.round_sleep_min_seconds,
            settings.round_sleep_max_seconds,
        ),
        sleep_fn=sleep_fn or time.sleep,
        randint_fn=randint_fn or random.randint,
    )
    cleanup_service = ChecklistCleanupService()
    monitor = ChecklistMonitorService(
        checklist_repository=checklist_repository,
        execution_service=executor,
        cleanup_service=cleanup_service,
        poll_seconds=settings.monitor_poll_seconds,
        sleep_fn=sleep_fn or time.sleep,
        now_fn=now_fn or (lambda: datetime.now(timezone.utc)),
        run_in_background=run_monitor_in_background,
    )

    LOGGER.debug("Application bootstrapped with project root %s", settings.project_root)
    return Application(
        settings=settings,
        importer=importer,
        executor=executor,
        monitor=monitor,
        fotmob_client=fotmob_client,
    )
