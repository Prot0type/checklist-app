from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone

from checklist_app.services.cleanup import ChecklistCleanupService
from checklist_app.services.executor import ChecklistExecutionService
from checklist_app.repositories.protocols import ChecklistRepository


LOGGER = logging.getLogger(__name__)


class ChecklistMonitorService:
    def __init__(
        self,
        checklist_repository: ChecklistRepository,
        execution_service: ChecklistExecutionService,
        cleanup_service: ChecklistCleanupService,
        poll_seconds: int,
        sleep_fn: Callable[[float], None] = time.sleep,
        now_fn: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        run_in_background: bool = True,
    ) -> None:
        self.checklist_repository = checklist_repository
        self.execution_service = execution_service
        self.cleanup_service = cleanup_service
        self.poll_seconds = poll_seconds
        self.sleep_fn = sleep_fn
        self.now_fn = now_fn
        self.run_in_background = run_in_background

    def run_once(self) -> list[str]:
        current_time = self.now_fn()
        started: list[str] = []

        for checklist in self.checklist_repository.list_all():
            if checklist.is_settled:
                if not checklist.cleaned_up:
                    self.cleanup_service.cleanup(checklist)
                    self.checklist_repository.mark_cleaned_up(checklist.checklist_name, True)
                continue

            if checklist.in_progress or checklist.start_time > current_time:
                continue

            LOGGER.info("Checklist '%s' is due. Starting execution.", checklist.checklist_name)
            self.checklist_repository.set_execution_state(
                checklist.checklist_name,
                in_progress=True,
                is_settled=False,
            )
            self.checklist_repository.mark_cleaned_up(checklist.checklist_name, False)

            if self.run_in_background:
                thread = threading.Thread(
                    target=self.execution_service.run,
                    args=(checklist.checklist_name,),
                    daemon=True,
                )
                thread.start()
            else:
                self.execution_service.run(checklist.checklist_name)

            started.append(checklist.checklist_name)

        return started

    def run_forever(self) -> None:
        LOGGER.info("Starting checklist monitor loop.")
        while True:
            self.run_once()
            self.sleep_fn(self.poll_seconds)
