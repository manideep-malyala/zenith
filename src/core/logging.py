"""Structured logging configuration for ZENITH.

Provides unified log formatters and handlers supporting standard, verbose,
and quiet operational modes for CLI and enterprise CI/CD workflows.
"""

import logging
import sys


def setup_logger(verbose: bool = False, quiet: bool = False) -> logging.Logger:
    """Configures and returns the central zenith logger.

    Args:
        verbose: If True, sets logging level to DEBUG.
        quiet: If True, suppresses INFO logs and only emits WARNING/ERROR.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger("zenith")

    if quiet:
        level = logging.WARNING
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates on re-configuration
    logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


logger = logging.getLogger("zenith")
