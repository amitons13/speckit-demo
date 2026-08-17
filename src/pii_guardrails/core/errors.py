"""Safe error types. Messages here must never contain raw PII or secrets."""

from __future__ import annotations


class GuardrailError(Exception):
    """Base class for guardrail errors. Carries only a safe, generic message."""

    code = "guardrail_error"
    http_status = 500

    def __init__(self, message: str = "An internal guardrail error occurred.") -> None:
        super().__init__(message)
        self.message = message


class InvalidInputError(GuardrailError):
    code = "invalid_input"
    http_status = 400


class PayloadTooLargeError(GuardrailError):
    code = "payload_too_large"
    http_status = 413


class DetectionUnavailableError(GuardrailError):
    """Raised when the detector fails, times out, or returns an unusable result.

    Triggers fail-closed behavior: detection returns a safe error; redaction blocks.
    """

    code = "detection_unavailable"
    http_status = 503
