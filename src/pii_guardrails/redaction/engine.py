"""Redaction/masking engine.

Pure functions that transform text given a set of detections and caller options.
No model calls, no I/O, no logging of content — trivially unit-testable.

Strategies:
  - redact: replace the value with a type placeholder, e.g. ``[REDACTED_EMAIL]``.
  - mask:  keep the last ``keep_last`` characters, mask the rest with ``mask_char``.

Non-PII content is preserved. Multiple and repeated entities are handled by applying
replacements from right to left so earlier offsets remain valid.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..detectors.base import Detection


@dataclass(frozen=True)
class RedactionOptions:
    """Caller-provided redaction options.

    - ``entities``: which entity types to protect. ``None`` means "protect all
      detected types" (privacy-preserving default so the API is never a silent no-op).
    - ``strategy_per_type``: optional per-type override of the strategy.
    - ``default_strategy``: strategy for types without an explicit override.
    """

    entities: frozenset[str] | None = None
    strategy_per_type: dict[str, str] = field(default_factory=dict)
    default_strategy: str = "redact"
    mask_keep_last: int = 4
    mask_char: str = "*"

    def strategy_for(self, entity_type: str) -> str:
        return self.strategy_per_type.get(entity_type, self.default_strategy)

    def protects(self, entity_type: str) -> bool:
        return self.entities is None or entity_type in self.entities


@dataclass(frozen=True)
class ActionResult:
    entity_type: str
    action: str
    count: int


@dataclass(frozen=True)
class RedactionResult:
    text: str
    actions: list[ActionResult]


def _mask_value(value: str, keep_last: int, mask_char: str) -> str:
    keep_last = max(0, keep_last)
    if keep_last >= len(value):
        # Value too short to safely reveal any part — mask entirely.
        return mask_char * len(value)
    masked_len = len(value) - keep_last
    return (mask_char * masked_len) + value[-keep_last:]


def _placeholder(entity_type: str) -> str:
    return f"[REDACTED_{entity_type}]"


def redact(text: str, detections: list[Detection], options: RedactionOptions) -> RedactionResult:
    """Apply redaction/masking to `text` for the detections the options select."""
    selected = [d for d in detections if options.protects(d.entity_type)]

    # Apply from right to left so earlier spans keep their offsets.
    selected_sorted = sorted(selected, key=lambda d: d.start, reverse=True)

    result = text
    counts: dict[tuple[str, str], int] = {}
    for det in selected_sorted:
        strategy = options.strategy_for(det.entity_type)
        original = result[det.start : det.end]
        if strategy == "mask":
            replacement = _mask_value(original, options.mask_keep_last, options.mask_char)
        else:  # default to redact for unknown/unspecified strategies (fail safe)
            strategy = "redact"
            replacement = _placeholder(det.entity_type)
        result = result[: det.start] + replacement + result[det.end :]
        counts[(det.entity_type, strategy)] = counts.get((det.entity_type, strategy), 0) + 1

    actions = [
        ActionResult(entity_type=etype, action=action, count=count)
        for (etype, action), count in sorted(counts.items())
    ]
    return RedactionResult(text=result, actions=actions)
