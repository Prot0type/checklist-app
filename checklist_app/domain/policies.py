from __future__ import annotations

from checklist_app.domain.enums import BetStatus, MatchStatus, WagerSide
from checklist_app.domain.models import TrackedMatch


def evaluate_legacy_bet_status(match: TrackedMatch) -> BetStatus:
    score = match.match.score_tuple()
    if score is None:
        return BetStatus.PENDING

    home_score, away_score = score

    if match.wager.side_wagered_on == WagerSide.HOME:
        if home_score >= away_score + 2:
            return BetStatus.WON
        if match.status == MatchStatus.FULL_TIME:
            return BetStatus.WON if home_score > away_score else BetStatus.LOST
        return BetStatus.PENDING

    if away_score >= home_score + 2:
        return BetStatus.WON
    if match.status == MatchStatus.FULL_TIME:
        return BetStatus.WON if away_score > home_score else BetStatus.LOST
    return BetStatus.PENDING
