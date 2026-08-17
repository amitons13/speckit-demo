from pii_guardrails.detectors.openai_detector import build_detections
from pii_guardrails.redaction.engine import RedactionOptions, redact


def _detect(items, text):
    return build_detections(items, text)


def test_redact_single_email():
    text = "Email me at jane@example.com please"
    dets = _detect([{"type": "EMAIL", "value": "jane@example.com", "confidence": 0.99}], text)
    result = redact(text, dets, RedactionOptions())
    assert "jane@example.com" not in result.text
    assert "[REDACTED_EMAIL]" in result.text
    assert result.actions[0].action == "redact"
    assert result.actions[0].count == 1


def test_mask_credit_card_keeps_last_four():
    text = "card 4111111111111111 end"
    dets = _detect([{"type": "CREDIT_CARD", "value": "4111111111111111", "confidence": 0.9}], text)
    opts = RedactionOptions(strategy_per_type={"CREDIT_CARD": "mask"}, mask_keep_last=4)
    result = redact(text, dets, opts)
    assert "************1111" in result.text
    assert "4111111111111111" not in result.text


def test_repeated_pii_all_replaced():
    text = "a@b.com then a@b.com again"
    dets = _detect([{"type": "EMAIL", "value": "a@b.com", "confidence": 0.9}], text)
    result = redact(text, dets, RedactionOptions())
    assert "a@b.com" not in result.text
    assert result.text.count("[REDACTED_EMAIL]") == 2
    assert result.actions[0].count == 2


def test_multiple_types_and_selective_protection():
    text = "email a@b.com phone 555-111-2222"
    items = [
        {"type": "EMAIL", "value": "a@b.com", "confidence": 0.9},
        {"type": "PHONE", "value": "555-111-2222", "confidence": 0.9},
    ]
    dets = _detect(items, text)
    # Only protect EMAIL.
    result = redact(text, dets, RedactionOptions(entities=frozenset({"EMAIL"})))
    assert "a@b.com" not in result.text
    assert "555-111-2222" in result.text  # phone preserved because not selected


def test_no_detections_preserves_text():
    text = "nothing sensitive here"
    result = redact(text, [], RedactionOptions())
    assert result.text == text
    assert result.actions == []


def test_non_pii_content_preserved():
    text = "Hello jane@example.com, welcome to ACME!"
    dets = _detect([{"type": "EMAIL", "value": "jane@example.com", "confidence": 0.9}], text)
    result = redact(text, dets, RedactionOptions())
    assert result.text.startswith("Hello ")
    assert result.text.endswith(", welcome to ACME!")
