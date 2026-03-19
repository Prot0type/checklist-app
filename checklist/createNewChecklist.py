from __future__ import annotations

import logging
import sys

from checklist_app.bootstrap import build_application


LOGGER = logging.getLogger(__name__)


def process_csv_and_update_dynamodb(csv_filename: str):
    app = build_application()
    try:
        return app.importer.import_csv(csv_filename)
    finally:
        app.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python checklist/createNewChecklist.py <csv_filename>")
    process_csv_and_update_dynamodb(sys.argv[1])
