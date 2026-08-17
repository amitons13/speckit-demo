"""Privacy-safe logging helpers.

The guardrail must never write prompts, detected PII values, API keys, or other
sensitive content into logs/traces/errors. This module provides a logger that only
ever records de-identified, structured metadata (counts, entity types, request ids).

There is deliberately NO helper here that accepts raw content — the absence of such
an API is the safeguard. Callers pass only safe, aggregate fields.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

_CONFIGURED = False


def configure_logging(level: int = logging.INFO) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root = logging.getLogger("pii_guardrails")
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)
    root.propagate = False
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(f"pii_guardrails.{name}")


# Fields that are always safe to log. Anything not in this set must not be logged.
_SAFE_KEYS = {
    "request_id",
    "event",
    "format",
    "outcome",
    "detection_count",
    "entity_types",
    "action_counts",
    "duration_ms",
    "error_kind",
    "status_code",
}


def safe_extra(**fields: Any) -> dict[str, Any]:
    """Return only allow-listed, de-identified fields; drop anything else defensively."""
    return {k: v for k, v in fields.items() if k in _SAFE_KEYS}
