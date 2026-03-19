from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from checklist_app.domain.enums import BetStatus, MatchStatus, WagerSide
from checklist_app.domain.models import TrackedMatch


LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class DiscordEmbedFormatter:
    timezone_name: str = "US/Eastern"

    def render(self, checklist_name: str, matches: list[TrackedMatch]) -> dict[str, object]:
        return {
            "title": checklist_name,
            "description": self._render_description(matches),
            "color": self._embed_color(matches),
        }

    def _render_description(self, matches: list[TrackedMatch]) -> str:
        local_tz = ZoneInfo(self.timezone_name)
        sorted_matches = sorted(matches, key=lambda match: (match.start_time, match.home_team))

        lines: list[str] = []
        for match in sorted_matches:
            local_time = match.start_time.astimezone(local_tz)
            kickoff = local_time.strftime("%A, %I:%M %p %Z")

            if match.wager.side_wagered_on == WagerSide.HOME:
                home_team = f"**{match.home_team}**"
                away_team = match.away_team
            else:
                home_team = match.home_team
                away_team = f"**{match.away_team}**"

            if match.score:
                matchup = f"{home_team} {match.score} {away_team}"
            else:
                matchup = f"{home_team} vs {away_team}"

            lines.append(f"{self._status_symbol(match)} {matchup} - {kickoff}")

        return "\n".join(lines)

    def _embed_color(self, matches: list[TrackedMatch]) -> int:
        if any(match.bet_status == BetStatus.LOST for match in matches):
            return 0xED4245
        if matches and all(match.bet_status == BetStatus.WON for match in matches):
            return 0x57F287
        if matches and all(match.status == MatchStatus.NOT_STARTED for match in matches):
            return 0x9B59B6
        if any(match.bet_status == BetStatus.PENDING for match in matches):
            return 0x00FFFF
        return 0x2C2F33

    @staticmethod
    def _status_symbol(match: TrackedMatch) -> str:
        if match.bet_status == BetStatus.WON:
            return "\u2705"
        if match.bet_status == BetStatus.LOST:
            return "\u274C"
        if match.status == MatchStatus.NOT_STARTED:
            return "\U0001F552"
        if match.status == MatchStatus.IN_PLAY:
            return "\u26BD"
        if match.status == MatchStatus.HALF_TIME:
            return "\u23F8"
        return "\u2753"


class DiscordClient:
    def __init__(
        self,
        bot_token: str,
        channel_id: str,
        formatter: DiscordEmbedFormatter | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        self.bot_token = bot_token
        self.channel_id = channel_id
        self.formatter = formatter or DiscordEmbedFormatter()
        self.timeout_seconds = timeout_seconds
        self._warned_unconfigured = False

    @property
    def configured(self) -> bool:
        return bool(self.bot_token and self.channel_id)

    def create_checklist_message(self, checklist_name: str, matches: list[TrackedMatch]) -> str | None:
        if not self.configured:
            self._warn_missing_configuration()
            return None

        payload = {"embeds": [self.formatter.render(checklist_name, matches)]}
        response = self._request("post", self._channel_messages_url(), payload)
        return str(response.json()["id"])

    def edit_checklist_message(
        self,
        checklist_name: str,
        matches: list[TrackedMatch],
        message_id: str,
    ) -> str | None:
        if not self.configured:
            self._warn_missing_configuration()
            return None

        payload = {"embeds": [self.formatter.render(checklist_name, matches)]}
        response = self._request("patch", f"{self._channel_messages_url()}/{message_id}", payload)
        return str(response.json()["id"])

    def _request(self, method: str, url: str, payload: dict[str, object]):
        import requests

        headers = {
            "Authorization": f"Bot {self.bot_token}",
            "Content-Type": "application/json",
        }
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=payload,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response

    def _channel_messages_url(self) -> str:
        return f"https://discord.com/api/v10/channels/{self.channel_id}/messages"

    def _warn_missing_configuration(self) -> None:
        if self._warned_unconfigured:
            return
        LOGGER.warning("Discord is not configured. Skipping Discord message publishing.")
        self._warned_unconfigured = True
