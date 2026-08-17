"""Detector interface and domain types.

The rest of the system depends ONLY on this interface, so the underlying detection
mechanism (OpenAI here) can be swapped later without touching the APIs or redaction.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable


class EntityType(str, Enum):
    """Supported PII entity types (from the specification, FR-002)."""

    PERSON = "PERSON"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    ADDRESS = "ADDRESS"
    CREDIT_CARD = "CREDIT_CARD"
    BANK_ACCOUNT = "BANK_ACCOUNT"
    IP_ADDRESS = "IP_ADDRESS"
    DATE_OF_BIRTH = "DATE_OF_BIRTH"
    GOV_ID = "GOV_ID"
    OTHER = "OTHER"


SUPPORTED_ENTITY_TYPES: frozenset[str] = frozenset(e.value for e in EntityType)


@dataclass(frozen=True)
class Detection:
    """A single detected PII occurrence.

    `start`/`end` are Unicode code-point offsets into the original text and are
    computed/validated by the service against the actual text — never blindly taken
    from the model. `value` is kept internal for redaction and is NOT returned by the
    Detection API by default.
    """

    entity_type: str
    start: int
    end: int
    confidence: float
    value: str

    @property
    def occurrence_key(self) -> tuple[str, str]:
        """Groups repeated identical values of the same type."""
        return (self.entity_type, self.value)


@runtime_checkable
class PIIDetector(Protocol):
    """Interface every detector must implement.

    Implementations MUST:
      - return only entities actually present in `text`,
      - restrict entity types to SUPPORTED_ENTITY_TYPES,
      - never raise for "no PII" (return an empty list),
      - raise DetectionUnavailableError on failure/timeout/unusable output.
    """

    def detect(self, text: str) -> list[Detection]:
        ...
