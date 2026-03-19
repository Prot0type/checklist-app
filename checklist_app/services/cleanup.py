from __future__ import annotations

import logging

from checklist_app.domain.models import ChecklistRecord


LOGGER = logging.getLogger(__name__)


class ChecklistCleanupService:
    def cleanup(self, checklist: ChecklistRecord) -> None:
        LOGGER.info(
            "Checklist '%s' is settled. Cleanup is intentionally a no-op until archival rules are defined.",
            checklist.checklist_name,
        )
