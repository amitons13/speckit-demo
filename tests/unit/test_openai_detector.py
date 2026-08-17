"""Tests for the OpenAI detector wrapper using an injected fake client.

These verify structured-output parsing plus safe (fail-closed) handling of malformed
responses and transport errors — without any network calls.
"""

import json
from types import SimpleNamespace

import pytest

from pii_guardrails.core.config import Settings
from pii_guardrails.core.errors import DetectionUnavailableError
from pii_guardrails.detectors.openai_detector import OpenAIDetector


def _fake_client(content=None, raise_exc=None):
    def create(**kwargs):
        if raise_exc is not None:
            raise raise_exc
        message = SimpleNamespace(content=content)
        choice = SimpleNamespace(message=message)
        return SimpleNamespace(choices=[choice])

    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


def _settings():
    return Settings(OPENAI_API_KEY="test-key")


def test_success_parses_structured_output():
    content = json.dumps({"entities": [{"type": "EMAIL", "value": "a@b.com", "confidence": 0.9}]})
    detector = OpenAIDetector(settings=_settings(), client=_fake_client(content=content))
    dets = detector.detect("contact a@b.com now")
    assert len(dets) == 1
    assert dets[0].entity_type == "EMAIL"


def test_transport_error_fails_closed():
    detector = OpenAIDetector(settings=_settings(), client=_fake_client(raise_exc=TimeoutError("slow")))
    with pytest.raises(DetectionUnavailableError):
        detector.detect("a@b.com")


def test_malformed_json_fails_closed():
    detector = OpenAIDetector(settings=_settings(), client=_fake_client(content="{not json"))
    with pytest.raises(DetectionUnavailableError):
        detector.detect("a@b.com")


def test_missing_entities_key_fails_closed():
    detector = OpenAIDetector(settings=_settings(), client=_fake_client(content=json.dumps({"foo": 1})))
    with pytest.raises(DetectionUnavailableError):
        detector.detect("a@b.com")


def test_empty_content_fails_closed():
    detector = OpenAIDetector(settings=_settings(), client=_fake_client(content=""))
    with pytest.raises(DetectionUnavailableError):
        detector.detect("a@b.com")
