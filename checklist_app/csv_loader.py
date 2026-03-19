from __future__ import annotations

import csv
from pathlib import Path

from checklist_app.domain.models import Wager


def load_wagers_from_csv(csv_path: Path) -> list[Wager]:
    wagers: list[Wager] = []

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row_number, row in enumerate(reader, start=2):
            match_url = (row.get("match_url") or "").strip()
            side = (row.get("side_wagered_on") or "").strip()
            if not match_url or not side:
                raise ValueError(f"Invalid CSV row {row_number} in {csv_path.name}.")
            wagers.append(Wager(match_url=match_url, side_wagered_on=side))

    if not wagers:
        raise ValueError(f"No wagers found in {csv_path.name}.")

    return wagers
