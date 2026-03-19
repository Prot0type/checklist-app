from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from checklist_app.domain.enums import BetStatus, MatchStatus, WagerSide


def parse_datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def serialize_datetime(value: datetime) -> str:
    normalized = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return normalized.isoformat(timespec="seconds")


def normalize_score(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned or cleaned.upper() == "N/A":
        return None
    return cleaned


def parse_score(value: str | None) -> tuple[int, int] | None:
    cleaned = normalize_score(value)
    if cleaned is None:
        return None

    separators = ["-", ":"]
    for separator in separators:
        if separator in cleaned:
            left, right = cleaned.split(separator, maxsplit=1)
            return int(left.strip()), int(right.strip())
    return None


@dataclass(frozen=True, slots=True)
class Wager:
    match_url: str
    side_wagered_on: WagerSide

    def __post_init__(self) -> None:
        object.__setattr__(self, "match_url", self.match_url.strip())
        object.__setattr__(self, "side_wagered_on", WagerSide.from_value(self.side_wagered_on))

    def to_dict(self) -> dict[str, str]:
        return {
            "match_url": self.match_url,
            "side_wagered_on": self.side_wagered_on.value,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "Wager":
        return cls(
            match_url=str(payload["match_url"]),
            side_wagered_on=WagerSide.from_value(str(payload["side_wagered_on"])),
        )


@dataclass(slots=True)
class MatchState:
    match_url: str
    home_team: str
    away_team: str
    start_time: datetime
    status: MatchStatus = MatchStatus.NOT_STARTED
    score: str | None = None

    def __post_init__(self) -> None:
        self.start_time = parse_datetime(self.start_time)
        self.status = MatchStatus.from_value(self.status)
        self.score = normalize_score(self.score)

    @property
    def expected_end_time(self) -> datetime:
        return self.start_time + timedelta(hours=2)

    def score_tuple(self) -> tuple[int, int] | None:
        return parse_score(self.score)

    def clone(self) -> "MatchState":
        return MatchState(
            match_url=self.match_url,
            home_team=self.home_team,
            away_team=self.away_team,
            start_time=self.start_time,
            status=self.status,
            score=self.score,
        )

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "match_url": self.match_url,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "start_time": serialize_datetime(self.start_time),
            "status": self.status.value,
        }
        if self.score is not None:
            payload["score"] = self.score
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "MatchState":
        return cls(
            match_url=str(payload["match_url"]),
            home_team=str(payload.get("home_team", "Unknown")),
            away_team=str(payload.get("away_team", "Unknown")),
            start_time=payload["start_time"],
            status=MatchStatus.from_value(str(payload.get("status", MatchStatus.NOT_STARTED.value))),
            score=str(payload["score"]) if "score" in payload and payload["score"] is not None else None,
        )


@dataclass(slots=True)
class TrackedMatch:
    match: MatchState
    wager: Wager
    bet_status: BetStatus = BetStatus.PENDING

    @classmethod
    def from_state(cls, match: MatchState, wager: Wager) -> "TrackedMatch":
        return cls(match=match.clone(), wager=wager, bet_status=BetStatus.PENDING)

    @property
    def match_url(self) -> str:
        return self.match.match_url

    @property
    def home_team(self) -> str:
        return self.match.home_team

    @property
    def away_team(self) -> str:
        return self.match.away_team

    @property
    def start_time(self) -> datetime:
        return self.match.start_time

    @property
    def status(self) -> MatchStatus:
        return self.match.status

    @property
    def score(self) -> str | None:
        return self.match.score

    def sync_state(self, state: MatchState) -> None:
        self.match = state.clone()


@dataclass(slots=True)
class ChecklistRecord:
    checklist_name: str
    wagers: list[Wager] = field(default_factory=list)
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    in_progress: bool = False
    is_settled: bool = False
    cleaned_up: bool = False
    message_id: str | None = None

    def __post_init__(self) -> None:
        self.start_time = parse_datetime(self.start_time)
        self.end_time = parse_datetime(self.end_time)

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "checklist_name": self.checklist_name,
            "wagers": [wager.to_dict() for wager in self.wagers],
            "start_time": serialize_datetime(self.start_time),
            "end_time": serialize_datetime(self.end_time),
            "in_progress": self.in_progress,
            "is_settled": self.is_settled,
            "cleaned_up": self.cleaned_up,
        }
        if self.message_id:
            payload["message_id"] = self.message_id
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ChecklistRecord":
        wager_payloads = payload.get("wagers", [])
        return cls(
            checklist_name=str(payload["checklist_name"]),
            wagers=[Wager.from_dict(item) for item in wager_payloads if isinstance(item, dict)],
            start_time=payload["start_time"],
            end_time=payload["end_time"],
            in_progress=bool(payload.get("in_progress", False)),
            is_settled=bool(payload.get("is_settled", False)),
            cleaned_up=bool(payload.get("cleaned_up", False)),
            message_id=str(payload["message_id"]) if payload.get("message_id") else None,
        )
