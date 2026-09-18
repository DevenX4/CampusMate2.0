"""Logging setup: one consistent, timestamped format for the whole application."""

import logging

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"


def setup_logging(level: str) -> None:
    # force=True replaces any handlers configured earlier, so calling this twice is safe.
    logging.basicConfig(level=level, format=LOG_FORMAT, force=True)
