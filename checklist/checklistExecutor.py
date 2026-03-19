from __future__ import annotations

import sys

from checklist_app.bootstrap import build_application


def execute_checklist(checklist_name: str, *, once: bool = False):
    app = build_application()
    try:
        return app.executor.run(checklist_name, once=once)
    finally:
        app.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python checklist/checklistExecutor.py <checklist_name> [--once]")

    execute_checklist(sys.argv[1], once="--once" in sys.argv[2:])
