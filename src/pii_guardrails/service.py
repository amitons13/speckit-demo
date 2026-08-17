"""Reusable PII detection component shared by BOTH APIs.

This is the single place that turns "text" into validated detections, using whatever
detector is configured. The Detection and Redaction APIs both depend on this, keeping
detection logic in one reusable component and detection/redaction responsibilities
separate.
"""

from __future__ import annotations

from .core.errors import InvalidInputError, PayloadTooLargeError
from .detectors.base import Detection, PIIDetector
from .redaction.engine import RedactionOptions, RedactionResult, redact


class GuardrailService:
    def __init__(self, detector: PIIDetector, max_payload_bytes: int) -> None:
        self._detector = detector
        self._max_payload_bytes = max_payload_bytes

    def _validate(self, text: object) -> str:
        if not isinstance(text, str) or text == "":
            raise InvalidInputError("Input text must be a non-empty string.")
        if len(text.encode("utf-8")) > self._max_payload_bytes:
            raise PayloadTooLargeError("Input exceeds the maximum allowed size.")
        return text

    def detect(self, text: str) -> list[Detection]:
        """Detection-only: never modifies input. May raise DetectionUnavailableError."""
        clean = self._validate(text)
        return self._detector.detect(clean)

    def redact(self, text: str, options: RedactionOptions) -> tuple[RedactionResult, list[Detection]]:
        """Detect then protect. Reuses the same detection component as `detect`."""
        clean = self._validate(text)
        detections = self._detector.detect(clean)
        result = redact(clean, detections, options)
        return result, detections
