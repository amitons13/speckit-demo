"""Integration tests for the PII Redaction API (/v1/redact)."""

from pii_guardrails.core.errors import DetectionUnavailableError


def test_redact_with_default_options_protects_all(make_client):
    client = make_client(
        items=[
            {"type": "EMAIL", "value": "jane@example.com", "confidence": 0.95},
            {"type": "PHONE", "value": "555-111-2222", "confidence": 0.9},
        ]
    )
    resp = client.post("/v1/redact", json={"prompt": "jane@example.com 555-111-2222"})
    assert resp.status_code == 200
    body = resp.json()
    assert "jane@example.com" not in body["redacted_prompt"]
    assert "555-111-2222" not in body["redacted_prompt"]
    assert body["detection_count"] == 2


def test_redact_mask_strategy(make_client):
    client = make_client(items=[{"type": "CREDIT_CARD", "value": "4111111111111111", "confidence": 0.9}])
    resp = client.post(
        "/v1/redact",
        json={
            "prompt": "card 4111111111111111",
            "options": {"entities": ["CREDIT_CARD"], "strategy_per_type": {"CREDIT_CARD": "mask"}, "mask_keep_last": 4},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "************1111" in body["redacted_prompt"]
    assert "4111111111111111" not in body["redacted_prompt"]
    assert body["actions"][0]["action"] == "mask"


def test_redact_selective_entities(make_client):
    client = make_client(
        items=[
            {"type": "EMAIL", "value": "a@b.com", "confidence": 0.9},
            {"type": "PHONE", "value": "555-111-2222", "confidence": 0.9},
        ]
    )
    resp = client.post(
        "/v1/redact",
        json={"prompt": "a@b.com 555-111-2222", "options": {"entities": ["EMAIL"]}},
    )
    body = resp.json()
    assert "a@b.com" not in body["redacted_prompt"]
    assert "555-111-2222" in body["redacted_prompt"]  # not selected -> preserved


def test_redact_repeated_pii(make_client):
    client = make_client(items=[{"type": "EMAIL", "value": "a@b.com", "confidence": 0.9}])
    resp = client.post("/v1/redact", json={"prompt": "a@b.com and a@b.com"})
    body = resp.json()
    assert "a@b.com" not in body["redacted_prompt"]
    assert body["actions"][0]["count"] == 2


def test_redact_no_pii_returns_prompt_unchanged(make_client):
    client = make_client(items=[])
    resp = client.post("/v1/redact", json={"prompt": "hello world"})
    body = resp.json()
    assert body["redacted_prompt"] == "hello world"
    assert body["actions"] == []


def test_redact_invalid_empty_prompt(make_client):
    client = make_client(items=[])
    resp = client.post("/v1/redact", json={"prompt": ""})
    assert resp.status_code == 400
    assert resp.json()["code"] == "invalid_input"


def test_redact_model_failure_fails_closed(make_client):
    client = make_client(error=DetectionUnavailableError("down"))
    resp = client.post("/v1/redact", json={"prompt": "jane@example.com"})
    # Fail closed: blocked, and no unprotected content is returned.
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "blocked"
    assert "redacted_prompt" not in body
    assert "jane@example.com" not in resp.text
