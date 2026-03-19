from __future__ import annotations

import logging


LOGGER = logging.getLogger(__name__)


def cleanup_checklist(checklist_name: str) -> None:
    LOGGER.info(
        "Cleanup for checklist '%s' is now handled by checklist_app.services.cleanup.",
        checklist_name,
    )
