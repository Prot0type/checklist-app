from __future__ import annotations

import sys

from checklist_app.bootstrap import build_application


def monitor_checklists(*, once: bool = False, foreground: bool = False):
    app = build_application(run_monitor_in_background=not foreground)
    try:
        if once:
            return app.monitor.run_once()
        app.monitor.run_forever()
        return []
    finally:
        app.close()


def main() -> None:
    once = "--once" in sys.argv[1:]
    foreground = "--foreground" in sys.argv[1:]
    monitor_checklists(once=once, foreground=foreground)


if __name__ == "__main__":
    main()
