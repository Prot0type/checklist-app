from __future__ import annotations

import logging
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from checklist_app.domain.enums import MatchStatus, WagerSide
from checklist_app.domain.models import ChecklistRecord, MatchState, Wager
from checklist_app.repositories.in_memory import InMemoryChecklistRepository, InMemoryMatchRepository
from checklist_app.services.cleanup import ChecklistCleanupService
from checklist_app.services.executor import ChecklistExecutionService
from checklist_app.services.monitor import ChecklistMonitorService


def _test_logger(_name: str, _path: Path) -> logging.Logger:
    logger = logging.getLogger("checklist_app.tests")
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())
    return logger


class FakeDiscordClient:
    def __init__(self) -> None:
        self.edits: list[tuple[str, str]] = []

    def edit_checklist_message(self, checklist_name: str, matches, message_id: str) -> str:
        self.edits.append((checklist_name, message_id))
        return message_id


class FakeFotMobClient:
    def __init__(self, refreshed_state: MatchState) -> None:
        self.refreshed_state = refreshed_state
        self.refresh_calls: list[str] = []

    def fetch_match_state(self, match_url: str) -> MatchState:
        return self.refreshed_state

    def refresh_match_state(self, current_state: MatchState) -> MatchState:
        self.refresh_calls.append(current_state.match_url)
        return self.refreshed_state


class RecordingExecutionService:
    def __init__(self) -> None:
        self.started: list[str] = []

    def run(self, checklist_name: str) -> None:
        self.started.append(checklist_name)


class ExecutionAndMonitorTests(unittest.TestCase):
    def test_execution_marks_checklist_as_settled(self) -> None:
        checklist_repo = InMemoryChecklistRepository()
        match_repo = InMemoryMatchRepository()

        wager = Wager(match_url="match-1", side_wagered_on=WagerSide.HOME)
        checklist_repo.upsert(
            ChecklistRecord(
                checklist_name="ticket",
                wagers=[wager],
                start_time=datetime(2026, 3, 17, tzinfo=timezone.utc),
                end_time=datetime(2026, 3, 17, 2, tzinfo=timezone.utc),
                message_id="message-123",
            )
        )

        initial_state = MatchState(
            match_url="match-1",
            home_team="Home",
            away_team="Away",
            start_time=datetime(2026, 3, 17, tzinfo=timezone.utc),
            status=MatchStatus.NOT_STARTED,
            score=None,
        )
        final_state = MatchState(
            match_url="match-1",
            home_team="Home",
            away_team="Away",
            start_time=datetime(2026, 3, 17, tzinfo=timezone.utc),
            status=MatchStatus.FULL_TIME,
            score="2 - 0",
        )
        match_repo.upsert(initial_state)

        executor = ChecklistExecutionService(
            checklist_repository=checklist_repo,
            match_repository=match_repo,
            fotmob_client=FakeFotMobClient(final_state),
            discord_client=FakeDiscordClient(),
            log_directory=Path("."),
            per_match_sleep_range=(0, 0),
            round_sleep_range=(0, 0),
            sleep_fn=lambda _seconds: None,
            randint_fn=lambda minimum, maximum: minimum,
            logger_factory=_test_logger,
        )

        results = executor.run("ticket")

        self.assertEqual(len(results), 1)
        self.assertTrue(checklist_repo.get("ticket").is_settled)
        self.assertFalse(checklist_repo.get("ticket").in_progress)
        self.assertEqual(match_repo.get("match-1").score, "2 - 0")

    def test_monitor_starts_due_checklists(self) -> None:
        checklist_repo = InMemoryChecklistRepository()

        wager = Wager(match_url="match-2", side_wagered_on=WagerSide.AWAY)
        checklist_repo.upsert(
            ChecklistRecord(
                checklist_name="due-ticket",
                wagers=[wager],
                start_time=datetime.now(timezone.utc) - timedelta(minutes=5),
                end_time=datetime.now(timezone.utc) + timedelta(hours=2),
            )
        )
        executor = RecordingExecutionService()

        monitor = ChecklistMonitorService(
            checklist_repository=checklist_repo,
            execution_service=executor,
            cleanup_service=ChecklistCleanupService(),
            poll_seconds=0,
            sleep_fn=lambda _seconds: None,
            now_fn=lambda: datetime.now(timezone.utc),
            run_in_background=False,
        )

        started = monitor.run_once()

        self.assertEqual(started, ["due-ticket"])
        self.assertEqual(executor.started, ["due-ticket"])
