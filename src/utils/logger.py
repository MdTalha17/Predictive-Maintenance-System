"""Utility module for application-wide logging configuration.

This module provides functions to configure logging from a configuration file
(`config/logging.conf`) if available, and to obtain module-specific loggers.
If the configuration file is missing, it falls back to a sensible default
console configuration to ensure logs are still emitted.

Usage:
    from src.utils.logger import setup_logging, get_logger

    setup_logging()  # optional; called on import with defaults
    logger = get_logger(__name__)
    logger.info("Hello")

The logging configuration path can be overridden using the `LOG_CFG` environment
variable or by passing a path to `setup_logging`.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import logging.config
import os
from pathlib import Path
from typing import Optional


# Default relative path to the logging configuration file
DEFAULT_LOGGING_CONF_PATH = Path("config") / "logging.conf"


def _resolve_logging_config_path(override_path: Optional[str | Path] = None, env_var: str = "LOG_CFG") -> Optional[Path]:
    """Resolve the logging configuration file path.

    Resolution order:
    1) Explicit ``override_path`` argument if provided and exists
    2) Environment variable specified by ``env_var`` (default: ``LOG_CFG``) if set and exists
    3) Project default at ``config/logging.conf`` if exists

    Returns None if no existing path is found.

    Parameters
    ----------
    override_path : Optional[str | Path]
        An explicit path to a logging configuration file.
    env_var : str
        Name of the environment variable to check for a config path.

    Returns
    -------
    Optional[Path]
        Path to an existing logging configuration file or None.
    """
    candidates: list[Path] = []

    if override_path:
        candidates.append(Path(override_path))

    env_value = os.getenv(env_var)
    if env_value:
        candidates.append(Path(env_value))

    candidates.append(DEFAULT_LOGGING_CONF_PATH)

    for candidate in candidates:
        try:
            if candidate and candidate.is_file():
                return candidate
        except Exception:
            # If any unexpected error occurs while probing, ignore and continue
            continue

    return None


def setup_logging(config_path: Optional[str | Path] = None, env_var: str = "LOG_CFG") -> None:
    """Initialize the logging system for the application.

    Attempts to configure logging from a file if found. If no configuration is
    available, falls back to a basic console configuration.

    Parameters
    ----------
    config_path : Optional[str | Path]
        Optional explicit path to a logging configuration file.
    env_var : str
        Environment variable name that can contain the path to the logging
        configuration file. Defaults to ``"LOG_CFG"``.
    """
    resolved_path = _resolve_logging_config_path(config_path, env_var)

    if resolved_path is not None:
        try:
            logging.config.fileConfig(str(resolved_path), disable_existing_loggers=False)
            logging.getLogger(__name__).debug(
                "Logging configured from file: %s", resolved_path.as_posix()
            )
            return
        except Exception:  # Fallback if config file is malformed
            logging.getLogger(__name__).exception(
                "Failed to configure logging from %s. Falling back to basicConfig.",
                resolved_path
            )

    # If we reach here, no configuration file is available; set a reasonable default
    log_level = logging.DEBUG if os.getenv("DEBUG", "0") == "1" else logging.INFO

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force = True
    )

    # Add rotating file handler to persist logs

    log_file = Path("logs/app.log")
    log_file.parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(log_file, maxBytes=5_000_000, backupCount=5, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        "%Y-%m-%d %H:%M:%S"
    ))
    file_handler.setLevel(log_level)
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)

    logging.getLogger(__name__).debug("Logging configured with basicConfig + RotatingFileHandler (no config file found)")


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a module-specific logger.

    Parameters
    ----------
    name : Optional[str]
        Logger name. Typically ``__name__`` of the calling module. If omitted,
        returns the root application logger named ``predictive_maintenance_system``.

    Returns
    -------
    logging.Logger
        Configured logger instance.
    """
    DEFAULT_LOGGER_NAME = "predictive_maintenance_system"

    return logging.getLogger(name if name else DEFAULT_LOGGER_NAME)


# Configure logging on import using defaults; users may call setup_logging again
# explicitly if they need to switch configs dynamically.
setup_logging()