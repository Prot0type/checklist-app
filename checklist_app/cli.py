from __future__ import annotations

import argparse
import logging

from checklist_app.bootstrap import build_application
from checklist_app.logging_utils import configure_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="checklist-app", description="Checklist tracker CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    import_parser = subparsers.add_parser("import-csv", help="Import a checklist CSV into storage.")
    import_parser.add_argument("csv_reference", help="CSV filename or path.")

    execute_parser = subparsers.add_parser("run-checklist", help="Run a checklist execution loop.")
    execute_parser.add_argument("checklist_name", help="Checklist name.")
    execute_parser.add_argument("--once", action="store_true", help="Run only a single sweep.")

    monitor_parser = subparsers.add_parser("monitor", help="Run the checklist monitor loop.")
    monitor_parser.add_argument("--once", action="store_true", help="Run one monitor scan and exit.")
    monitor_parser.add_argument(
        "--foreground",
        action="store_true",
        help="Run checklist execution inline instead of background threads.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    configure_logging()
    run_monitor_in_background = not getattr(args, "foreground", False)
    if args.command == "monitor" and args.once:
        run_monitor_in_background = False

    app = build_application(run_monitor_in_background=run_monitor_in_background)

    try:
        if args.command == "import-csv":
            checklist = app.importer.import_csv(args.csv_reference)
            logging.getLogger(__name__).info("Imported checklist '%s'.", checklist.checklist_name)
            return 0

        if args.command == "run-checklist":
            app.executor.run(args.checklist_name, once=args.once)
            return 0

        if args.command == "monitor":
            if args.once:
                started = app.monitor.run_once()
                logging.getLogger(__name__).info("Monitor scan finished. Started %s checklist(s).", len(started))
                return 0

            app.monitor.run_forever()
            return 0

        parser.error(f"Unsupported command '{args.command}'.")
        return 2
    finally:
        app.close()
