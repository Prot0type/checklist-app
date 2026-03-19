from __future__ import annotations

import unittest
from datetime import datetime, timezone

from checklist_app.domain.enums import BetStatus, MatchStatus, WagerSide
from checklist_app.domain.models import MatchState, TrackedMatch, Wager
from checklist_app.domain.policies import evaluate_legacy_bet_status


class SettlementPolicyTests(unittest.TestCase):
    def test_home_side_is_marked_won_when_two_goals_ahead_live(self) -> None:
        tracked_match = TrackedMatch.from_state(
            MatchState(
                match_url="match-1",
                home_team="Home",
                away_team="Away",
                start_time=datetime(2026, 3, 17, tzinfo=timezone.utc),
                status=MatchStatus.IN_PLAY,
                score="2 - 0",
            ),
            Wager(match_url="match-1", side_wagered_on=WagerSide.HOME),
        )

        self.assertEqual(evaluate_legacy_bet_status(tracked_match), BetStatus.WON)

    def test_away_side_is_marked_lost_at_full_time_when_trailing(self) -> None:
        tracked_match = TrackedMatch.from_state(
            MatchState(
                match_url="match-2",
                home_team="Home",
                away_team="Away",
                start_time=datetime(2026, 3, 17, tzinfo=timezone.utc),
                status=MatchStatus.FULL_TIME,
                score="3 - 1",
            ),
            Wager(match_url="match-2", side_wagered_on=WagerSide.AWAY),
        )

        self.assertEqual(evaluate_legacy_bet_status(tracked_match), BetStatus.LOST)

    def test_missing_score_keeps_match_pending(self) -> None:
        tracked_match = TrackedMatch.from_state(
            MatchState(
                match_url="match-3",
                home_team="Home",
                away_team="Away",
                start_time=datetime(2026, 3, 17, tzinfo=timezone.utc),
                status=MatchStatus.NOT_STARTED,
                score=None,
            ),
            Wager(match_url="match-3", side_wagered_on=WagerSide.HOME),
        )

        self.assertEqual(evaluate_legacy_bet_status(tracked_match), BetStatus.PENDING)
