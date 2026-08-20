import json
import logging
import sys
from typing import Any


def configure_logging(level: str) -> None:
    logger = logging.getLogger("liara_assistant")
    logger.setLevel(level.upper())
    logger.propagate = False
    if logger.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)


def telemetry_event(event: str, **fields: Any) -> None:
    payload = {"event": event, **fields}
    logging.getLogger("liara_assistant").info(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
    )
