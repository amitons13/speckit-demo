# Quickstart & Validation Guide: PII Guardrails

A runnable validation guide proving the two APIs work end-to-end and uphold the key guarantees.
See [data-model.md](./data-model.md) and [contracts/](./contracts/) for details (not duplicated here).

## Prerequisites

- Python 3.11+, the service running locally (see repo README once implemented).
- A valid bearer token for a test tenant `tenant-a`; a second token for `tenant-b`.
- Base URL: `http://localhost:8080/v1`.

## Setup

```bash
# from repo root (once implemented)
uv sync                      # or: pip install -r requirements.txt
uv run pii-guardrails serve  # starts the service on :8080
```

## Scenario 1 — Detection API detects but never modifies (SC-014, SC-015)

```bash
curl -sX POST localhost:8080/v1/detect -H "Authorization: Bearer $TOKEN_A" \
  -H 'Content-Type: application/json' \
  -d '{"payload":"Email me at jane.doe@example.com","format":"text"}'
```

**Expected**: `detections` contains one `EMAIL` with `confidence`, `start`, `end`, `occurrenceId`;
**no `value` field** (default). The input is unchanged (detection-only).

## Scenario 2 — Redaction with explicit options (redact + mask) (SC-009)

```bash
curl -sX POST localhost:8080/v1/redact -H "Authorization: Bearer $TOKEN_A" \
  -H 'Content-Type: application/json' \
  -d '{"payload":"card 4111111111111111, email a@b.com","format":"text",
       "options":{"entities":["CREDIT_CARD","EMAIL"],
                  "strategyPerType":{"CREDIT_CARD":"mask","EMAIL":"redact"},
                  "maskConfig":{"keepLast":4}}}'
```

**Expected**: `outcome=transformed`; card shows only last 4 (`************1111`), email replaced with a
placeholder; `actions` lists both; no raw PII in metadata.

## Scenario 3 — Redaction with NO options applies secure-default (never no-op) (SC-016)

```bash
curl -sX POST localhost:8080/v1/redact -H "Authorization: Bearer $TOKEN_A" \
  -H 'Content-Type: application/json' \
  -d '{"payload":"SSN 123-45-6789","format":"text"}'
```

**Expected**: `outcome=transformed` (not a pass-through); the government identifier is protected per
the secure-default floor.

## Scenario 4 — Structured JSON + repeated + multilingual (FR-013, FR-032, FR-033, SC-021)

```bash
curl -sX POST localhost:8080/v1/redact -H "Authorization: Bearer $TOKEN_A" \
  -H 'Content-Type: application/json' \
  -d '{"format":"json",
       "payload":"{\"note\":\"Contact José at jose@ex.com\",\"alt\":\"jose@ex.com\"}"}'
```

**Expected**: valid JSON returned; both occurrences of the email protected consistently; spans/paths
reported; Unicode handled correctly.

## Scenario 5 — Fail-closed when detection is unavailable (SC-003)

```bash
# with the detection engine disabled/faulted via test hook
curl -isX POST localhost:8080/v1/redact -H "Authorization: Bearer $TOKEN_A" \
  -H 'Content-Type: application/json' -d '{"payload":"a@b.com","format":"text"}'
```

**Expected**: HTTP `422` with `outcome=blocked`, no `transformedPayload`, safe message — no content
forwarded.

## Scenario 6 — Tenant isolation (SC-004)

```bash
# tenant-a token attempting tenant-b policy scope
curl -isX POST localhost:8080/v1/redact -H "Authorization: Bearer $TOKEN_A" \
  -H 'X-Scope-Tenant: tenant-b' -H 'Content-Type: application/json' \
  -d '{"payload":"a@b.com","format":"text"}'
```

**Expected**: HTTP `403`; attempt recorded in audit (de-identified).

## Scenario 7 — No raw PII in telemetry (SC-002, SC-017)

After running Scenarios 1–6:

```bash
grep -R "jane.doe@example.com\|4111111111111111\|123-45-6789" ./logs ./traces || echo "CLEAN"
```

**Expected**: `CLEAN` — zero raw PII in logs/traces/metrics/errors.

## Automated validation

```bash
uv run pytest tests/contract tests/integration tests/security tests/resilience
uv run pytest tests/quality   # precision/recall corpus (recall >= 95% in-scope)
uv run pytest tests/perf      # p95 budgets: <=50ms (<=4KB), <=150ms (<=100KB)
```

**Success = all suites green**, recall ≥ 95% for in-scope entities, zero leakage findings, and p95
within budget.
