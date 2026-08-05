"""Backward-compatible logging shim for the structured RealAI server."""

from .logging_utils import setup_logging


def get_logger(name='realai'):
    """Return the configured RealAI logger."""
    return setup_logging()


def log_event(level, event, **fields):
    """Emit a simple structured log line."""
    logger = setup_logging()
    extra = ' '.join('{0}={1}'.format(key, value) for key, value in sorted(fields.items()))
    message = event if not extra else '{0} {1}'.format(event, extra)
    logger.log(level, message)
