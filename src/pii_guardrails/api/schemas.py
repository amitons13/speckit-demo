"""Request/response models for the two APIs.

Note: the Detection API response intentionally OMITS raw detected values by default
(only type/confidence/span). The Redaction API returns the transformed prompt plus
safe action metadata — never raw PII.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ---- Detection API ----

class DetectRequest(BaseModel):
    prompt: str = Field(..., description="The text payload to analyze. Not modified.")


class DetectedEntity(BaseModel):
    type: str
    confidence: float
    start: int
    end: int
    # No `value` field: raw PII is not returned by default.


class DetectResponse(BaseModel):
    detections: list[DetectedEntity]
    detection_count: int


# ---- Redaction API ----

class RedactionOptionsModel(BaseModel):
    entities: list[str] | None = Field(
        default=None,
        description="Entity types to protect. Omit/null to protect all detected types.",
    )
    strategy_per_type: dict[str, str] = Field(
        default_factory=dict,
        description="Optional per-type strategy override: 'redact' or 'mask'.",
    )
    default_strategy: str = Field(
        default="redact", description="Strategy for types without an override."
    )
    mask_keep_last: int = Field(default=4, ge=0)
    mask_char: str = Field(default="*", min_length=1, max_length=1)


class RedactRequest(BaseModel):
    prompt: str = Field(..., description="The text payload to protect.")
    options: RedactionOptionsModel | None = None


class ActionSummary(BaseModel):
    type: str
    action: str
    count: int


class RedactResponse(BaseModel):
    redacted_prompt: str
    actions: list[ActionSummary]
    detection_count: int


class ErrorResponse(BaseModel):
    code: str
    message: str
