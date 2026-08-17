import pytest

from pii_guardrails.core.errors import InvalidInputError, PayloadTooLargeError
from pii_guardrails.redaction.engine import RedactionOptions
from tests.conftest import make_service


def test_empty_input_rejected():
    service = make_service(items=[])
    with pytest.raises(InvalidInputError):
        service.detect("")


def test_non_string_input_rejected():
    service = make_service(items=[])
    with pytest.raises(InvalidInputError):
        service.detect(None)  # type: ignore[arg-type]


def test_payload_too_large_rejected():
    service = make_service(items=[], max_payload_bytes=10)
    with pytest.raises(PayloadTooLargeError):
        service.redact("x" * 50, RedactionOptions())
