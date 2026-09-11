"""Logging helpers for the structured RealAI server."""

import logging
import sys


def setup_logging():
    """Configure and return the RealAI logger."""
    logger = logging.getLogger('realai')
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logger.addHandler(handler)
    return logger
