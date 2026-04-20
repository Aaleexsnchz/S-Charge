import logging
import sys
from typing import Any

from pythonjsonlogger.json import JsonFormatter

_logger = logging.getLogger("audit")


def _configure() -> None:
    if _logger.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            timestamp=True,
        )
    )
    _logger.addHandler(handler)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False


_configure()


def audit(event: str, **fields: Any) -> None:
    _logger.info(event, extra=fields)
