from __future__ import annotations

from pathlib import Path

from checklist_app.csv_loader import load_wagers_from_csv
from checklist_app.domain.models import ChecklistRecord, TrackedMatch
from checklist_app.domain.policies import evaluate_legacy_bet_status
from checklist_app.integrations.discord_client import DiscordClient
from checklist_app.integrations.fotmob_client import FotMobClient
from checklist_app.repositories.protocols import ChecklistRepository, MatchRepository


class ChecklistImportService:
    def __init__(
        self,
        checklist_repository: ChecklistRepository,
        match_repository: MatchRepository,
        fotmob_client: FotMobClient,
        discord_client: DiscordClient,
        csv_directory: Path,
    ) -> None:
        self.checklist_repository = checklist_repository
        self.match_repository = match_repository
        self.fotmob_client = fotmob_client
        self.discord_client = discord_client
        self.csv_directory = csv_directory

    def import_csv(self, csv_reference: str) -> ChecklistRecord:
        csv_path = self._resolve_csv_path(csv_reference)
        checklist_name = csv_path.stem
        wagers = load_wagers_from_csv(csv_path)

        tracked_matches: list[TrackedMatch] = []
        for wager in wagers:
            match_state = self.match_repository.get(wager.match_url)
            if match_state is None:
                match_state = self.fotmob_client.fetch_match_state(wager.match_url)
                self.match_repository.upsert(match_state)

            tracked_match = TrackedMatch.from_state(match_state, wager)
            tracked_match.bet_status = evaluate_legacy_bet_status(tracked_match)
            tracked_matches.append(tracked_match)

        start_time = min(match.start_time for match in tracked_matches)
        end_time = max(match.match.expected_end_time for match in tracked_matches)
        message_id = self.discord_client.create_checklist_message(checklist_name, tracked_matches)

        checklist = ChecklistRecord(
            checklist_name=checklist_name,
            wagers=wagers,
            start_time=start_time,
            end_time=end_time,
            in_progress=False,
            is_settled=False,
            cleaned_up=False,
            message_id=message_id,
        )
        self.checklist_repository.upsert(checklist)
        return checklist

    def _resolve_csv_path(self, csv_reference: str) -> Path:
        candidate = Path(csv_reference)
        candidates = [candidate, self.csv_directory / candidate]

        if not candidate.suffix:
            candidates.extend([candidate.with_suffix(".csv"), (self.csv_directory / candidate).with_suffix(".csv")])

        for path in candidates:
            if path.exists():
                return path.resolve()

        raise FileNotFoundError(f"Could not find CSV '{csv_reference}'.")
