from __future__ import annotations

from enum import StrEnum


class _ValueEnum(StrEnum):
    @classmethod
    def from_value(cls, value: str | "_ValueEnum") -> "_ValueEnum":
        if isinstance(value, cls):
            return value
        return cls(value)


class WagerSide(_ValueEnum):
    HOME = "HOME"
    AWAY = "AWAY"


class MatchStatus(_ValueEnum):
    NOT_STARTED = "NS"
    IN_PLAY = "IP"
    HALF_TIME = "HT"
    FULL_TIME = "FT"


class BetStatus(_ValueEnum):
    PENDING = "PENDING"
    WON = "WON"
    LOST = "LOST"
