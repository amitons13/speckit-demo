"""Tests for output validation: we never blindly trust model spans/types."""

from pii_guardrails.detectors.base import EntityType
from pii_guardrails.detectors.openai_detector import _find_all_spans, build_detections


def test_find_all_spans_multiple():
    assert _find_all_spans("a@b.com x a@b.com", "a@b.com") == [(0, 7), (10, 17)]


def test_hallucinated_value_not_in_text_is_dropped():
    text = "no pii here"
    dets = build_detections([{"type": "EMAIL", "value": "ghost@x.com", "confidence": 0.99}], text)
    assert dets == []


def test_unknown_entity_type_normalized_to_other():
    text = "value SECRET123 here"
    dets = build_detections([{"type": "MYSTERY", "value": "SECRET123", "confidence": 0.8}], text)
    assert len(dets) == 1
    assert dets[0].entity_type == EntityType.OTHER.value


def test_confidence_clamped_and_defaulted():
    text = "a@b.com and c@d.com"
    dets = build_detections(
        [
            {"type": "EMAIL", "value": "a@b.com", "confidence": 5},      # clamp to 1.0
            {"type": "EMAIL", "value": "c@d.com", "confidence": "oops"}, # default 0.5
        ],
        text,
    )
    by_value = {d.value: d.confidence for d in dets}
    assert by_value["a@b.com"] == 1.0
    assert by_value["c@d.com"] == 0.5


def test_spans_are_computed_not_trusted():
    text = "start a@b.com end"
    # Model supplies a wrong offset; we ignore it and compute the real span.
    dets = build_detections([{"type": "EMAIL", "value": "a@b.com", "confidence": 0.9}], text)
    assert len(dets) == 1
    assert text[dets[0].start : dets[0].end] == "a@b.com"


def test_overlaps_resolved_deterministically():
    text = "john@example.com"
    # Two overlapping candidates; only one non-overlapping detection should remain.
    dets = build_detections(
        [
            {"type": "EMAIL", "value": "john@example.com", "confidence": 0.9},
            {"type": "PERSON", "value": "john", "confidence": 0.6},
        ],
        text,
    )
    assert len(dets) == 1
    assert dets[0].entity_type == "EMAIL"


def test_empty_or_malformed_items_skipped():
    text = "a@b.com"
    dets = build_detections(
        [
            {"type": "EMAIL", "value": "", "confidence": 0.9},   # empty value
            "not-a-dict",                                          # wrong shape
            {"type": "EMAIL", "value": "a@b.com", "confidence": 0.9},
        ],
        text,
    )
    assert len(dets) == 1
