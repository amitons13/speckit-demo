"""Shared test fixtures.

A FakeDetector substitutes the OpenAI detector (proving the swappable interface) and
makes tests deterministic and offline. It reuses the production `build_detections`
helper so computed spans behave exactly like the real path.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from pii_guardrails.api.app import create_app
from pii_guardrails.detectors.base import Detection
from pii_guardrails.detectors.openai_detector import build_detections
from pii_guardrails.service import GuardrailService


class FakeDetector:
    """Configurable, offline PIIDetector for tests."""

    def __init__(self, items: list[dict[str, Any]] | None = None, error: Exception | None = None) -> None:
        self._items = items or []
        self._error = error

    def detect(self, text: str) -> list[Detection]:
        if self._error is not None:
            raise self._error
        return build_detections(self._items, text)


def make_service(items=None, error=None, max_payload_bytes: int = 262_144) -> GuardrailService:
    return GuardrailService(detector=FakeDetector(items=items, error=error), max_payload_bytes=max_payload_bytes)


@pytest.fixture
def make_client():
    def _make(items=None, error=None, max_payload_bytes: int = 262_144) -> TestClient:
        service = make_service(items=items, error=error, max_payload_bytes=max_payload_bytes)
        return TestClient(create_app(service=service), raise_server_exceptions=False)

    return _make
