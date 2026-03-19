from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def configure_logging(level: int = logging.INFO) -> None:
    root_logger = logging.getLogger()
    if root_logger.handlers:
        root_logger.setLevel(level)
        return

    logging.basicConfig(level=level, format=LOG_FORMAT)


def build_checklist_logger(checklist_name: str, log_directory: Path) -> logging.Logger:
    log_directory.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    logger_name = f"checklist_app.run.{checklist_name}.{timestamp}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.handlers:
        return logger

    formatter = logging.Formatter(LOG_FORMAT)
    log_file = log_directory / f"{checklist_name}_{timestamp}.log"

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger
