from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path

from checklist_app.domain.enums import MatchStatus
from checklist_app.domain.models import MatchState
from checklist_app.repositories.in_memory import InMemoryChecklistRepository, InMemoryMatchRepository
from checklist_app.services.importer import ChecklistImportService


class FakeFotMobClient:
    def __init__(self) -> None:
        self.requested: list[str] = []

    def fetch_match_state(self, match_url: str) -> MatchState:
        self.requested.append(match_url)
        return MatchState(
            match_url=match_url,
            home_team="Arsenal",
            away_team="Barcelona",
            start_time=datetime(2026, 3, 17, 18, 0, tzinfo=timezone.utc),
            status=MatchStatus.NOT_STARTED,
            score=None,
        )


class FakeDiscordClient:
    def __init__(self) -> None:
        self.created_messages: list[tuple[str, int]] = []

    def create_checklist_message(self, checklist_name: str, matches) -> str:
        self.created_messages.append((checklist_name, len(matches)))
        return "message-123"


class ChecklistImportServiceTests(unittest.TestCase):
    def test_import_creates_checklist_and_persists_match_cache(self) -> None:
        checklist_repo = InMemoryChecklistRepository()
        match_repo = InMemoryMatchRepository()
        fotmob_client = FakeFotMobClient()
        discord_client = FakeDiscordClient()

        csv_path = Path("tests_import_ticket.csv")
        csv_path.write_text(
            "match_url,side_wagered_on\narsenal-vs-barcelona/abc#123,HOME\n",
            encoding="utf-8",
        )

        try:
            service = ChecklistImportService(
                checklist_repository=checklist_repo,
                match_repository=match_repo,
                fotmob_client=fotmob_client,
                discord_client=discord_client,
                csv_directory=Path("."),
            )

            checklist = service.import_csv("tests_import_ticket.csv")
        finally:
            if csv_path.exists():
                csv_path.unlink()

        self.assertEqual(checklist.checklist_name, "tests_import_ticket")
        self.assertEqual(checklist.message_id, "message-123")
        self.assertIsNotNone(match_repo.get("arsenal-vs-barcelona/abc#123"))
        self.assertEqual(discord_client.created_messages, [("tests_import_ticket", 1)])
        self.assertEqual(fotmob_client.requested, ["arsenal-vs-barcelona/abc#123"])
