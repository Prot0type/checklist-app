from __future__ import annotations

from checklist_app.domain.models import ChecklistRecord, MatchState


class InMemoryChecklistRepository:
    def __init__(self) -> None:
        self._items: dict[str, ChecklistRecord] = {}

    def get(self, checklist_name: str) -> ChecklistRecord | None:
        return self._items.get(checklist_name)

    def list_all(self) -> list[ChecklistRecord]:
        return list(self._items.values())

    def upsert(self, checklist: ChecklistRecord) -> None:
        self._items[checklist.checklist_name] = checklist

    def set_execution_state(self, checklist_name: str, *, in_progress: bool, is_settled: bool | None = None) -> None:
        checklist = self._items[checklist_name]
        checklist.in_progress = in_progress
        if is_settled is not None:
            checklist.is_settled = is_settled

    def mark_cleaned_up(self, checklist_name: str, cleaned_up: bool = True) -> None:
        self._items[checklist_name].cleaned_up = cleaned_up


class InMemoryMatchRepository:
    def __init__(self) -> None:
        self._items: dict[str, MatchState] = {}

    def get(self, match_url: str) -> MatchState | None:
        return self._items.get(match_url)

    def upsert(self, match: MatchState) -> None:
        self._items[match.match_url] = match.clone()
