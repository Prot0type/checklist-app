from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable
from pathlib import Path

from checklist_app.domain.enums import BetStatus
from checklist_app.domain.models import ChecklistRecord, TrackedMatch
from checklist_app.domain.policies import evaluate_legacy_bet_status
from checklist_app.integrations.discord_client import DiscordClient
from checklist_app.integrations.fotmob_client import FotMobClient
from checklist_app.logging_utils import build_checklist_logger
from checklist_app.repositories.protocols import ChecklistRepository, MatchRepository


class ChecklistExecutionService:
    def __init__(
        self,
        checklist_repository: ChecklistRepository,
        match_repository: MatchRepository,
        fotmob_client: FotMobClient,
        discord_client: DiscordClient,
        log_directory: Path,
        per_match_sleep_range: tuple[int, int],
        round_sleep_range: tuple[int, int],
        sleep_fn: Callable[[float], None] = time.sleep,
        randint_fn: Callable[[int, int], int] = random.randint,
        logger_factory: Callable[[str, Path], logging.Logger] = build_checklist_logger,
    ) -> None:
        self.checklist_repository = checklist_repository
        self.match_repository = match_repository
        self.fotmob_client = fotmob_client
        self.discord_client = discord_client
        self.log_directory = log_directory
        self.per_match_sleep_range = per_match_sleep_range
        self.round_sleep_range = round_sleep_range
        self.sleep_fn = sleep_fn
        self.randint_fn = randint_fn
        self.logger_factory = logger_factory

    def run(self, checklist_name: str, *, once: bool = False) -> list[TrackedMatch]:
        checklist = self.checklist_repository.get(checklist_name)
        if checklist is None:
            raise LookupError(f"Checklist '{checklist_name}' was not found.")

        logger = self.logger_factory(checklist_name, self.log_directory)
        logger.info("Starting checklist execution.")

        self.checklist_repository.set_execution_state(checklist_name, in_progress=True, is_settled=False)
        self.checklist_repository.mark_cleaned_up(checklist_name, False)

        tracked_matches = self._load_tracked_matches(checklist)

        try:
            while True:
                all_settled = True

                for tracked_match in tracked_matches:
                    try:
                        refreshed_state = self.fotmob_client.refresh_match_state(tracked_match.match)
                    except Exception:
                        logger.exception("Failed to refresh match '%s'. Keeping the previous state.", tracked_match.match_url)
                        all_settled = False
                        continue

                    tracked_match.sync_state(refreshed_state)
                    tracked_match.bet_status = evaluate_legacy_bet_status(tracked_match)
                    self.match_repository.upsert(refreshed_state)

                    logger.info(
                        "%s vs %s | status=%s | score=%s | bet_status=%s",
                        tracked_match.home_team,
                        tracked_match.away_team,
                        tracked_match.status.value,
                        tracked_match.score or "N/A",
                        tracked_match.bet_status.value,
                    )

                    if tracked_match.bet_status == BetStatus.PENDING:
                        all_settled = False

                    self._sleep_with_jitter(logger, self.per_match_sleep_range, "before checking the next match")

                if checklist.message_id:
                    self.discord_client.edit_checklist_message(checklist_name, tracked_matches, checklist.message_id)

                if all_settled:
                    logger.info("All matches are settled. Finishing checklist execution.")
                    self.checklist_repository.set_execution_state(checklist_name, in_progress=False, is_settled=True)
                    return tracked_matches

                if once:
                    logger.info("Stopping after a single execution round because --once was requested.")
                    self.checklist_repository.set_execution_state(checklist_name, in_progress=False, is_settled=False)
                    return tracked_matches

                self._sleep_with_jitter(logger, self.round_sleep_range, "before the next checklist sweep")

        except Exception:
            self.checklist_repository.set_execution_state(checklist_name, in_progress=False, is_settled=False)
            logger.exception("Checklist execution failed.")
            raise

    def _load_tracked_matches(self, checklist: ChecklistRecord) -> list[TrackedMatch]:
        tracked_matches: list[TrackedMatch] = []

        for wager in checklist.wagers:
            match_state = self.match_repository.get(wager.match_url)
            if match_state is None:
                match_state = self.fotmob_client.fetch_match_state(wager.match_url)
                self.match_repository.upsert(match_state)

            tracked_match = TrackedMatch.from_state(match_state, wager)
            tracked_match.bet_status = evaluate_legacy_bet_status(tracked_match)
            tracked_matches.append(tracked_match)

        return tracked_matches

    def _sleep_with_jitter(
        self,
        logger: logging.Logger,
        delay_range: tuple[int, int],
        reason: str,
    ) -> None:
        minimum, maximum = delay_range
        delay = minimum if minimum == maximum else self.randint_fn(minimum, maximum)
        logger.info("Sleeping for %s seconds %s.", delay, reason)
        self.sleep_fn(delay)
