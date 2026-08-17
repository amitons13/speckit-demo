"""OpenAI-backed PII detector.

Design safeguards (per implementation constraints):
  - Uses structured/schema-constrained output rather than free-form text.
  - NEVER trusts model-provided spans: we locate every value in the ORIGINAL text
    ourselves, so redaction only ever acts on real substrings.
  - Validates and constrains model output (entity type, confidence, value presence)
    before it is used.
  - Malformed/unexpected responses and timeouts fail closed
    (DetectionUnavailableError).
  - Does not log prompts, values, or the API key.
"""

from __future__ import annotations

import json
from typing import Any

from ..core.config import Settings
from ..core.errors import DetectionUnavailableError
from ..core.logging import get_logger, safe_extra
from .base import SUPPORTED_ENTITY_TYPES, Detection, EntityType

logger = get_logger("detector.openai")

# JSON schema the model must conform to (schema-constrained structured output).
_DETECTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "type": {"type": "string", "enum": sorted(SUPPORTED_ENTITY_TYPES)},
                    "value": {"type": "string"},
                    "confidence": {"type": "number"},
                },
                "required": ["type", "value", "confidence"],
            },
        }
    },
    "required": ["entities"],
}

_SYSTEM_PROMPT = (
    "You are a PII detection function. Identify personally identifiable information "
    "in the user's text. Return ONLY structured JSON matching the schema. For each "
    "entity, return its type, the exact substring `value` as it appears in the text, "
    "and a confidence between 0 and 1. Do not paraphrase values. Do not include "
    "anything that is not PII."
)


def _find_all_spans(text: str, value: str) -> list[tuple[int, int]]:
    """Return all non-overlapping [start, end) spans where `value` occurs in `text`."""
    spans: list[tuple[int, int]] = []
    if not value:
        return spans
    start = 0
    while True:
        idx = text.find(value, start)
        if idx == -1:
            break
        spans.append((idx, idx + len(value)))
        start = idx + len(value)
    return spans


def _normalize_type(raw_type: Any) -> str:
    if not isinstance(raw_type, str):
        return EntityType.OTHER.value
    candidate = raw_type.strip().upper()
    return candidate if candidate in SUPPORTED_ENTITY_TYPES else EntityType.OTHER.value


def _normalize_confidence(raw_conf: Any) -> float:
    try:
        conf = float(raw_conf)
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, conf))


def build_detections(raw_items: Any, text: str) -> list[Detection]:
    """Validate model output and compute trustworthy spans against `text`.

    - Drops entries whose value is missing or not actually present in the text
      (hallucination guard).
    - Normalizes unknown entity types to OTHER and clamps confidence to [0, 1].
    - Expands each value to ALL of its occurrences (handles repeated PII).
    - Resolves overlaps deterministically (higher confidence / longer span wins).
    """
    if not isinstance(raw_items, list):
        raise DetectionUnavailableError("Model returned an unexpected structure.")

    candidates: list[Detection] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        value = item.get("value")
        if not isinstance(value, str) or not value.strip():
            continue
        entity_type = _normalize_type(item.get("type"))
        confidence = _normalize_confidence(item.get("confidence"))
        for start, end in _find_all_spans(text, value):
            candidates.append(
                Detection(
                    entity_type=entity_type,
                    start=start,
                    end=end,
                    confidence=confidence,
                    value=value,
                )
            )

    return _resolve_overlaps(candidates)


def _resolve_overlaps(candidates: list[Detection]) -> list[Detection]:
    # Deterministic ordering: earliest start, then higher confidence, then longer span.
    ordered = sorted(
        candidates,
        key=lambda d: (d.start, -d.confidence, -(d.end - d.start)),
    )
    accepted: list[Detection] = []
    for det in ordered:
        if any(det.start < a.end and a.start < det.end for a in accepted):
            continue  # overlaps an already-accepted span
        accepted.append(det)
    return accepted


class OpenAIDetector:
    """PIIDetector implementation backed by the OpenAI API.

    `client` may be injected (e.g., for testing). If omitted, a client is built from
    settings. The model name, temperature, and timeout come from configuration.
    """

    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        self._settings = settings
        self._client = client

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self._settings.openai_configured:
            raise DetectionUnavailableError("Detection is not configured.")
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - dependency guaranteed in prod
            raise DetectionUnavailableError("Detection backend unavailable.") from exc
        self._client = OpenAI(
            api_key=self._settings.openai_api_key,
            timeout=self._settings.openai_timeout_seconds,
        )
        return self._client

    def _request_detections(self, text: str) -> Any:
        client = self._get_client()
        try:
            response = client.chat.completions.create(
                model=self._settings.openai_model,
                temperature=self._settings.openai_temperature,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "pii_detections",
                        "schema": _DETECTION_SCHEMA,
                        "strict": True,
                    },
                },
            )
            content = response.choices[0].message.content
        except DetectionUnavailableError:
            raise
        except Exception as exc:  # timeouts, connection, API errors, shape errors
            # Do not include the exception message (may echo input); log only the kind.
            logger.warning("detection_call_failed", extra=safe_extra(error_kind=type(exc).__name__))
            raise DetectionUnavailableError("Detection call failed.") from exc

        if not isinstance(content, str) or not content.strip():
            raise DetectionUnavailableError("Empty detection response.")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise DetectionUnavailableError("Malformed detection response.") from exc
        if not isinstance(parsed, dict) or "entities" not in parsed:
            raise DetectionUnavailableError("Unexpected detection response.")
        return parsed["entities"]

    def detect(self, text: str) -> list[Detection]:
        raw_items = self._request_detections(text)
        return build_detections(raw_items, text)
