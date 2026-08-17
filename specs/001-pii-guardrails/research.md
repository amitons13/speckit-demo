# Phase 0 Research: PII Guardrails

This document records the key technical decisions, their rationale, and alternatives considered.
It resolves the items the spec deferred to planning (notably the concrete latency budget and
max-payload size) and the technology choices needed for tasks.

## D1. Detection engine — layered, pluggable (defense in depth)

- **Decision**: Use Microsoft Presidio (Analyzer + Anonymizer) with spaCy NER, plus regex/pattern
  recognizers and custom/tenant recognizers, orchestrated behind our own analyzer that merges and
  de-duplicates spans.
- **Rationale**: Directly implements Constitution Principle II (defense in depth) — regex + NER +
  custom recognizers are independent layers; no single mechanism is authoritative. Presidio is
  open-source, self-hostable (no new SaaS), supports redaction/masking, custom recognizers, and
  confidence scores/spans out of the box.
- **Alternatives considered**:
  - Single regex library — rejected: no NER, weak recall, single point of failure.
  - Cloud DLP SaaS (e.g., vendor PII APIs) — rejected for v1: adds external dependency, data-egress
    and residency concerns, and cost; can be added later as an additional recognizer layer.
  - Train a bespoke model — rejected: unnecessary complexity for v1; Presidio + custom recognizers
    cover the required entity set.

## D2. Language & framework

- **Decision**: Python 3.11+ with FastAPI + Pydantic.
- **Rationale**: Best PII/NLP ecosystem (Presidio/spaCy are Python); FastAPI gives typed contracts,
  OpenAPI generation, and async I/O for predictable latency. Language-agnostic HTTP API means AI
  apps in any language integrate via the thin SDK or direct calls.
- **Alternatives**: Go/Java service calling a Python detection sidecar — rejected for v1 as
  unnecessary infrastructure; a single Python service is simpler and meets latency budgets.

## D3. API shape — two APIs, URI-versioned

- **Decision**: `POST /v1/detect` (detection-only) and `POST /v1/redact` (protection). URI
  versioning; additive changes backward compatible; breaking changes under a new version.
- **Rationale**: Matches the firm requirement (FR-027) and separation of concerns; URI versioning is
  the simplest, most cache/gateway-friendly scheme and satisfies FR-038.
- **Alternatives**: Header-based versioning — rejected as less transparent for callers and gateways;
  single combined endpoint with a mode flag — rejected: blurs the detection/redaction boundary.

## D4. Policy resolution — most-specific-wins with a non-weakenable floor

- **Decision**: Resolve effective policy by precedence use case > application > environment > tenant,
  then clamp so it never drops below the secure-default floor (privacy by default).
- **Rationale**: Implements clarified FR-005 and Principles I & VI (configurable but safe). The floor
  guarantees new/misconfigured scopes are protected.
- **Alternatives**: Most-restrictive-merge — rejected (harder to reason about/test, surprising to
  configure); tenant-always-wins — rejected (too coarse).

## D5. Confidence threshold placement

- **Decision**: Detection API returns all detections at/above an optional threshold (default minimal
  floor) with scores; Redaction API applies the effective policy threshold to decide actions. Each
  policy has a below-threshold stance (default allow-below-threshold).
- **Rationale**: Matches clarified FR-039/FR-007; keeps Detection "informational" and Redaction
  "enforcing"; makes false-positive rate tunable (SC-007).

## D6. Fail-safe behavior & timeouts

- **Decision**: Default fail-closed. Detection timeout default **300 ms** (configurable) wired to a
  safe action. Uncertain result (error/timeout/unavailable/indeterminate) → block the whole request.
  Partial redaction failure → block the whole request. Explicit per-policy fail-open only for
  designated low-risk use cases, always audited.
- **Rationale**: Principle III (non-negotiable). Distinguishes "uncertain result" from low confidence
  (FR-014 vs FR-007).
- **Alternatives**: Fail-open default — rejected (violates the constitution).

## D7. Performance budgets & payload limits (resolves deferred SC-005 / large-payload size)

- **Decision**: Guardrail-added latency budgets — **p95 ≤ 50 ms** for payloads ≤ 4 KB and
  **p95 ≤ 150 ms** for payloads ≤ 100 KB (excluding network). **Max payload 256 KB** (configurable);
  above the limit → reject/fail-closed. Scale horizontally (stateless pods); initial capacity guide
  ≥ 500 req/s per pod for typical payloads.
- **Rationale**: Fixes the numbers the spec intentionally deferred (NFR-001, SC-005, FR-022, SC-010)
  with production-reasonable defaults; timeouts integrate with fail-safe (Principle VII + III).
- **Alternatives**: No hard max — rejected (unbounded latency/DoS risk); stricter 20 ms budget —
  rejected as unrealistic with NER on larger payloads.

## D8. Preventing PII leakage in telemetry

- **Decision**: Centralized telemetry **scrubber** between the engine and all sinks; structured
  logging with allow-listed fields only; safe error objects; automated leakage-scan tests.
- **Rationale**: Principle IV/IX; FR-010, FR-029, FR-031; verified by SC-002/SC-017.
- **Alternatives**: Rely on developer discipline — rejected (not testable/guaranteed).

## D9. Storage & caching (reuse, minimal new infra)

- **Decision**: Reuse platform PostgreSQL for policy/config + de-identified audit; reuse platform
  Redis (or in-process TTL cache) for compiled resolved policies. No raw PII persisted.
- **Rationale**: Minimizes new infrastructure (explicit user requirement); policies are small,
  read-heavy, and benefit from caching for latency.
- **Alternatives**: Dedicated new datastore — rejected (unnecessary infra).

## D10. Streaming (v1 scope)

- **Decision**: Streaming guarded emission disabled in v1; responses fully buffered and evaluated
  before return.
- **Rationale**: Clarified decision (FR-026); avoids boundary-spanning PII leakage risk. Revisit in a
  later version with buffer-and-scan windows.

## D11. JSON & multilingual/Unicode handling

- **Decision**: Support plain text and structured JSON; report character spans for text and field
  paths for JSON; express spans in Unicode code points; run detection on both structured values and
  free-text fields.
- **Rationale**: FR-013, FR-032, FR-033; keeps JSON structurally valid after transformation (FR-008).

## D12. Detection raw-value exposure

- **Decision**: Detection API omits raw values by default; returns them only with an explicit,
  authorization-gated (privileged scope), audited opt-in; never in telemetry.
- **Rationale**: Reconciles the requested behavior with Principle IV (data minimization); clarified
  FR-029.
