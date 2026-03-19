from __future__ import annotations

from checklist_app.domain.models import ChecklistRecord, MatchState


class DynamoChecklistRepository:
    def __init__(self, table) -> None:
        self._table = table

    def get(self, checklist_name: str) -> ChecklistRecord | None:
        response = self._table.get_item(Key={"checklist_name": checklist_name})
        item = response.get("Item")
        if not item:
            return None
        return ChecklistRecord.from_dict(item)

    def list_all(self) -> list[ChecklistRecord]:
        return [ChecklistRecord.from_dict(item) for item in self._scan_all_items()]

    def upsert(self, checklist: ChecklistRecord) -> None:
        self._table.put_item(Item=checklist.to_dict())

    def set_execution_state(self, checklist_name: str, *, in_progress: bool, is_settled: bool | None = None) -> None:
        expressions = ["in_progress = :in_progress"]
        values: dict[str, object] = {":in_progress": in_progress}

        if is_settled is not None:
            expressions.append("is_settled = :is_settled")
            values[":is_settled"] = is_settled

        self._table.update_item(
            Key={"checklist_name": checklist_name},
            UpdateExpression=f"SET {', '.join(expressions)}",
            ExpressionAttributeValues=values,
        )

    def mark_cleaned_up(self, checklist_name: str, cleaned_up: bool = True) -> None:
        self._table.update_item(
            Key={"checklist_name": checklist_name},
            UpdateExpression="SET cleaned_up = :cleaned_up",
            ExpressionAttributeValues={":cleaned_up": cleaned_up},
        )

    def _scan_all_items(self) -> list[dict[str, object]]:
        items: list[dict[str, object]] = []
        response = self._table.scan()
        items.extend(response.get("Items", []))

        while "LastEvaluatedKey" in response:
            response = self._table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))

        return items


class DynamoMatchRepository:
    def __init__(self, table) -> None:
        self._table = table

    def get(self, match_url: str) -> MatchState | None:
        response = self._table.get_item(Key={"match_url": match_url})
        item = response.get("Item")
        if not item:
            return None
        return MatchState.from_dict(item)

    def upsert(self, match: MatchState) -> None:
        self._table.put_item(Item=match.to_dict())
