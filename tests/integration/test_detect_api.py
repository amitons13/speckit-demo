"""Integration tests for the PII Detection API (/v1/detect)."""

from pii_guardrails.core.errors import DetectionUnavailableError


def test_detect_multiple_pii_types(make_client):
    client = make_client(
        items=[
            {"type": "EMAIL", "value": "jane@example.com", "confidence": 0.95},
            {"type": "PHONE", "value": "555-111-2222", "confidence": 0.9},
        ]
    )
    resp = client.post("/v1/detect", json={"prompt": "jane@example.com / 555-111-2222"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["detection_count"] == 2
    types = {d["type"] for d in body["detections"]}
    assert types == {"EMAIL", "PHONE"}
    # Raw values are never returned by the detection API.
    assert all("value" not in d for d in body["detections"])


def test_detect_does_not_return_raw_value_but_spans_map_to_text(make_client):
    prompt = "reach me at jane@example.com"
    client = make_client(items=[{"type": "EMAIL", "value": "jane@example.com", "confidence": 0.9}])
    resp = client.post("/v1/detect", json={"prompt": prompt})
    d = resp.json()["detections"][0]
    assert prompt[d["start"] : d["end"]] == "jane@example.com"


def test_detect_no_pii(make_client):
    client = make_client(items=[])
    resp = client.post("/v1/detect", json={"prompt": "nothing to see"})
    assert resp.status_code == 200
    assert resp.json() == {"detections": [], "detection_count": 0}


def test_detect_invalid_empty_prompt(make_client):
    client = make_client(items=[])
    resp = client.post("/v1/detect", json={"prompt": ""})
    assert resp.status_code == 400
    assert resp.json()["code"] == "invalid_input"


def test_detect_missing_prompt_field(make_client):
    client = make_client(items=[])
    resp = client.post("/v1/detect", json={})
    assert resp.status_code == 422  # pydantic validation


def test_detect_model_failure_returns_503(make_client):
    client = make_client(error=DetectionUnavailableError("down"))
    resp = client.post("/v1/detect", json={"prompt": "jane@example.com"})
    assert resp.status_code == 503
    assert resp.json()["code"] == "detection_unavailable"
