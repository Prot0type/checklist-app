from __future__ import annotations

from typing import Protocol

from checklist_app.domain.models import ChecklistRecord, MatchState


class ChecklistRepository(Protocol):
    def get(self, checklist_name: str) -> ChecklistRecord | None:
        ...

    def list_all(self) -> list[ChecklistRecord]:
        ...

    def upsert(self, checklist: ChecklistRecord) -> None:
        ...

    def set_execution_state(self, checklist_name: str, *, in_progress: bool, is_settled: bool | None = None) -> None:
        ...

    def mark_cleaned_up(self, checklist_name: str, cleaned_up: bool = True) -> None:
        ...


class MatchRepository(Protocol):
    def get(self, match_url: str) -> MatchState | None:
        ...

    def upsert(self, match: MatchState) -> None:
        ...
