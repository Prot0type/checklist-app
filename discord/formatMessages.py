from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from checklist_app.config import Settings
from checklist_app.domain.enums import BetStatus, MatchStatus, WagerSide
from checklist_app.domain.models import MatchState, TrackedMatch, Wager
from checklist_app.integrations.discord_client import DiscordClient, DiscordEmbedFormatter


def _adapt_match(match) -> TrackedMatch:
    if isinstance(match, TrackedMatch):
        return match

    start_time = match.get_start_time()
    if isinstance(start_time, str):
        start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    elif not isinstance(start_time, datetime):
        start_time = datetime.now(timezone.utc)

    state = MatchState(
        match_url=match.get_match_url(),
        home_team=match.get_home_team(),
        away_team=match.get_away_team(),
        start_time=start_time,
        status=MatchStatus(match.get_status()),
        score=match.get_score(),
    )
    tracked_match = TrackedMatch.from_state(
        state,
        Wager(match_url=match.get_match_url(), side_wagered_on=WagerSide(match.get_side_wagered_on())),
    )
    tracked_match.bet_status = BetStatus(match.get_bet_status())
    return tracked_match


def _adapt_matches(matches: Iterable[object]) -> list[TrackedMatch]:
    return [_adapt_match(match) for match in matches]


def get_embed_color(matches) -> int:
    formatter = DiscordEmbedFormatter(timezone_name=Settings.from_env().display_timezone)
    return formatter._embed_color(_adapt_matches(matches))


def get_embed_description(matches) -> str:
    formatter = DiscordEmbedFormatter(timezone_name=Settings.from_env().display_timezone)
    return formatter._render_description(_adapt_matches(matches))


def get_embed(checklist_name: str, matches) -> dict[str, object]:
    formatter = DiscordEmbedFormatter(timezone_name=Settings.from_env().display_timezone)
    return formatter.render(checklist_name, _adapt_matches(matches))


def send_or_edit_discord_message(channel_id, checklist_name, matches, bot_token):
    client = DiscordClient(bot_token=bot_token, channel_id=channel_id)
    return client.create_checklist_message(checklist_name, _adapt_matches(matches))
