"""
logging_config.py
==================
Centralised logging configuration for the rat connectome project.

Usage
-----
    from logging_config import setup_logging
    setup_logging(log_dir="/path/to/logs", level="INFO", script_name="my_script")
"""

import logging
import sys
from datetime import datetime
from pathlib import Path


def setup_logging(
    log_dir: str = "logs",
    level: str = "INFO",
    script_name: str = "connectome",
) -> logging.Logger:
    """Configure root logger with console and rotating file handlers.

    Parameters
    ----------
    log_dir:
        Directory where log files are written. Created if absent.
    level:
        Logging level string (``"DEBUG"``, ``"INFO"``, ``"WARNING"``, …).
    script_name:
        Used to name the log file: ``{script_name}_{timestamp}.log``.

    Returns
    -------
    logging.Logger
        Configured root logger.
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_path / f"{script_name}_{timestamp}.log"

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler
    file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)   # always capture DEBUG to file
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    root_logger.info("Logging initialised → %s", log_file)
    return root_logger
