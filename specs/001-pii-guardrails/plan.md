# Implementation Plan: Enterprise PII Guardrails for AI Platform

**Branch**: `001-pii-guardrails` | **Date**: 2026-08-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-pii-guardrails/spec.md`

## Summary

Deliver a centralized **PII Guardrails service** that every AI application on the platform can call
to (a) detect PII ("what PII is present?") and (b) protect PII ("given options, redact/mask/block").
The service exposes exactly two APIs (Detection, Redaction) behind a shared **policy evaluation
layer** and a pluggable, multi-technique **detection engine** (regex + NER + custom recognizers =
defense in depth). It is invoked at two interception points — inbound (prompts/tool inputs) and
outbound (model/tool responses) — enforces tenant-aware policies with a non-weakenable secure
default, and is fail-closed by default. Raw PII is transient (in-memory only), never persisted, and
never written to logs/traces/metrics/errors. The design reuses existing platform capabilities
(identity/authorization, tenant context, config store, observability/audit pipeline) and adds only
the guardrail service plus a policy store, keeping infrastructure minimal.

## Technical Context

**Language/Version**: Python 3.11+ (strong PII/NLP ecosystem; enables regex + NER + custom
recognizers for defense in depth). A thin client SDK is language-agnostic over HTTP.

**Primary Dependencies**: FastAPI (API surface), Pydantic (contract validation), Microsoft Presidio
Analyzer + Anonymizer (detection + redaction/masking engine with pluggable recognizers), spaCy
(NER model backing Presidio). All are permissively licensed and self-hostable — no new external SaaS.

**Storage**: Reuse the platform's managed PostgreSQL for the **Policy/Configuration store** (policies,
versions, tenant scoping) and the **audit metadata store** (de-identified audit records). No raw PII
is ever stored. A cache (reuse platform Redis if present, else in-process TTL cache) holds resolved,
compiled policies for low-latency lookup.

**Testing**: pytest (unit, integration, contract), Schemathesis (contract/property tests against the
OpenAPI contracts), plus a curated labeled corpus for precision/recall measurement and a
fault-injection harness for fail-safe tests.

**Target Platform**: Linux containers on the platform's existing orchestrator (e.g., Kubernetes),
deployed as a horizontally scalable stateless service.

**Project Type**: Backend web service (two HTTP APIs) + optional thin client SDK/middleware for AI
applications.

**Performance Goals** (resolves deferred SC-005/NFR-001): Guardrail-added latency budgets —
**p95 ≤ 50 ms** for typical payloads (≤ 4 KB), **p95 ≤ 150 ms** for large payloads (≤ 100 KB),
measured excluding network. Sustain platform concurrency by scaling horizontally (stateless pods);
target ≥ 500 req/s per pod for typical payloads as an initial capacity guide.

**Constraints**: Fail-closed by default; timeouts wired to fail-safe (detection timeout default
**300 ms**, configurable). **Maximum payload size 256 KB** (configurable); above the limit the
request is rejected/fail-closed, never passed unprotected. Streaming guarded emission is disabled in
v1 (full-response evaluation). No raw PII in any telemetry.

**Scale/Scope**: Multi-tenant, many AI applications; v1 targets text (plain + JSON), the standard
entity set plus custom recognizers, and the two APIs. Non-text modalities, de-tokenization, vaulting,
and streaming are out of scope for v1.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How the plan satisfies it | Gate |
|-----------|---------------------------|------|
| I. Privacy by Default | Secure-default policy applies when no options/policy; non-weakenable floor; opt-out is explicit & audited | PASS |
| II. Defense in Depth | Detection engine layers regex + NER + custom recognizers; no single mechanism is authoritative | PASS |
| III. Fail-Safe (NON-NEGOTIABLE) | Default fail-closed; every dependency call has a timeout → defined safe action; partial redaction failure blocks whole request | PASS |
| IV. Data Minimization | Raw PII in-memory only; never persisted/logged; Detection raw-value return off by default & gated | PASS |
| V. Explainability & Auditability | Decision metadata (types, spans, counts, confidence, policy version) with no raw values; audit records de-identified | PASS |
| VI. Configurability | Tenant/app/env/use-case policies; per-entity actions, thresholds, masking strategies; pluggable recognizers | PASS |
| VII. Predictable Performance | Explicit p95 budgets + timeouts tied to fail-safe; horizontal scaling; policy cache | PASS |
| VIII. Security & Tenant Isolation | AuthN/Z on every call (reuse platform identity); tenant-scoped policies/audit; least privilege; server-side enforcement | PASS |
| IX. Observability Without Leakage | OpenTelemetry metrics/traces + audit carry only de-identified aggregates/references | PASS |
| X. Testability (NON-NEGOTIABLE) | Unit/integration/contract tests, precision/recall corpus, fault-injection for fail-safe | PASS |

**Result**: PASS (no violations). See Complexity Tracking (none required).

## Project Structure

### Documentation (this feature)

```text
specs/001-pii-guardrails/
├── plan.md              # This file
├── research.md          # Phase 0 output (decisions/rationale/alternatives)
├── data-model.md        # Phase 1 output (entities)
├── quickstart.md        # Phase 1 output (validation guide)
├── contracts/           # Phase 1 output (OpenAPI for Detection & Redaction APIs)
│   ├── detection-api.yaml
│   └── redaction-api.yaml
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
src/pii_guardrails/
├── api/                     # FastAPI routers: detection, redaction, health
│   ├── detection.py
│   ├── redaction.py
│   └── deps.py              # auth, tenant-context, request-context dependencies
├── engine/                  # Detection + transformation (defense in depth)
│   ├── detectors/           # regex, NER, custom recognizer adapters
│   ├── analyzer.py          # orchestrates layered detection, merges spans
│   ├── transformer.py       # redact / mask strategies
│   └── resolver.py          # overlap/adjacency resolution
├── policy/                  # Policy evaluation layer
│   ├── models.py            # policy schema
│   ├── resolver.py          # scope precedence + secure-default floor
│   ├── store.py             # policy repository (PostgreSQL) + cache
│   └── evaluator.py         # applies actions per entity, threshold, fail-safe stance
├── security/                # authz, tenant isolation, redaction of telemetry
│   ├── authz.py
│   └── scrubbing.py         # ensures no raw PII escapes into logs/traces/errors
├── observability/           # OTel metrics/traces + audit emitter (de-identified)
│   ├── metrics.py
│   ├── tracing.py
│   └── audit.py
├── core/                    # config, errors, fail-safe primitives, timeouts
└── sdk/                     # optional thin client middleware for AI apps

tests/
├── contract/                # OpenAPI/schemathesis contract tests
├── integration/             # end-to-end API + policy + engine flows
├── unit/                    # detectors, transformer, resolver, policy resolver
├── security/                # tenant isolation, leakage scans, authz
├── resilience/              # fault injection: timeouts, outages, partial failures
└── quality/                 # precision/recall corpus harness
```

**Structure Decision**: Single backend service (two HTTP APIs) with clear internal separation of
concerns — `api` (transport) → `policy` (evaluation) → `engine` (detection/transformation) →
`security`/`observability` (cross-cutting). A thin optional `sdk` provides inbound/outbound
interception middleware so applications integrate consistently. This keeps a single deployable while
enforcing interface boundaries.

## Architecture & Major Components

1. **API Layer (`api/`)** — Two endpoints (Detection, Redaction) plus health/readiness. Validates
   contracts (Pydantic), authenticates/authorizes, resolves tenant context, and enforces payload
   limits. Never logs bodies.
2. **Policy Evaluation Layer (`policy/`)** — Resolves the effective policy by scope precedence
   (use case > application > environment > tenant) bounded by the non-weakenable secure-default
   floor; supplies per-entity actions, thresholds, masking strategies, and the fail-safe stance.
3. **Detection Engine (`engine/detectors`, `analyzer`)** — Defense in depth: runs regex recognizers,
   NER, and custom/tenant recognizers, then merges/deduplicates spans and resolves overlaps. Emits
   detections with type, span, confidence, occurrence grouping — no raw values leave unless gated.
4. **Transformer (`engine/transformer`)** — Applies redact/mask per entity; block rejects the
   offending segment (per-entity resolution). Preserves structural validity for JSON.
5. **Security (`security/`)** — Authz checks, tenant isolation enforcement, and a **telemetry
   scrubber** guaranteeing raw PII cannot enter logs/traces/metrics/errors.
6. **Observability (`observability/`)** — OpenTelemetry metrics/traces and a de-identified **audit
   emitter** (decision + access-control events).
7. **Optional Client SDK (`sdk/`)** — Middleware that wires the two interception points into AI apps
   and always calls Redaction with a resolved policy (this is where platform-level privacy-by-default
   is guaranteed for the raw API primitives).

## Data Flow

**Inbound (request) path**: AI app → SDK/interceptor → Redaction API → authN/Z + tenant context →
payload validation → policy resolution → detection engine (layered) → per-entity transform (redact/
mask/block) → return protected payload + safe metadata → app forwards protected content downstream.

**Outbound (response) path**: model/tool response (fully buffered; streaming disabled v1) → Redaction
API → same evaluation → protected response returned to end user.

**Detection-only path**: caller → Detection API → authN/Z → validation → detection engine → return
detections (type/confidence/span; raw values only if gated) — input never modified.

**Failure path**: any detection error/timeout/unavailability (an "uncertain result") → fail-closed:
block the whole request with a safe error; audit the event (de-identified).

## Security Boundaries

- **Trust boundary at the API layer**: every call authenticated and authorized (reuse platform
  identity/JWT/mTLS); unauthenticated/unauthorized calls rejected before any content processing.
- **Tenant isolation boundary**: policies, config, cache entries, and audit records are keyed by
  tenant; cross-tenant access is denied and audited. Cache keys include tenant id.
- **PII containment boundary**: raw PII exists only in-process for the duration of a call; the
  telemetry scrubber sits between the engine and all observability sinks. Error handlers return safe
  messages only.
- **Least privilege**: the service holds minimal credentials (policy DB read, audit write, model
  files); no broad platform access.

## Data Handling Lifecycle

1. **Ingest**: payload received over TLS; held in memory; size-checked (≤ 256 KB).
2. **Process**: detection + transformation operate on in-memory buffers only.
3. **Respond**: protected payload + de-identified metadata returned.
4. **Discard**: raw buffers dropped at end of request scope; not persisted, not cached, not logged.
5. **Audit**: only de-identified references (entity types, counts, spans, confidence, policy version,
   outcome, tenant/app ids) are written.

## API Contracts

Full OpenAPI in [`contracts/`](./contracts/). Summary:

- **Detection API** (`POST /v1/detect`): input `{ payload (text|json), format, threshold?, entityTypes?,
  returnValues? (gated) }` → `{ detections: [{ type, confidence, start, end, path?, occurrenceId }],
  policyVersion?, requestId }`. Never modifies input; `returnValues` requires a privileged scope and
  is audited.
- **Redaction API** (`POST /v1/redact`): input `{ payload, format, options? { entities, strategyPerType
  (redact|mask), maskConfig?, threshold? } }` → `{ transformedPayload, actions: [{ type, action, count,
  spans }], policyVersion, outcome (transformed|blocked|allowed), requestId }`. No options → resolved/
  secure-default policy. No raw PII in response beyond the transformed payload the caller submitted.
- **Versioning**: URI-versioned (`/v1/…`); additive changes are backward compatible; breaking changes
  ship under a new version (FR-038).
- **Errors**: safe, structured error objects; validation errors for empty/malformed input; 4xx for
  authz/validation, 5xx maps to fail-closed block with a safe body.

## Storage Requirements

- **Policy/Config store (PostgreSQL, reused)**: policies with tenant/app/env/use-case scope, versions,
  entity sets, per-type actions/strategies, thresholds, fail-safe stance. Validated on write.
- **Policy cache (Redis or in-process)**: compiled resolved policies keyed by (tenant, scope,
  version) with TTL/invalidation for low-latency evaluation.
- **Audit metadata store (reused)**: append-only, tamper-evident, de-identified records.
- **No raw PII storage anywhere.** Detection models (spaCy) are static assets shipped with the image.

## Observability Approach

- **Metrics (OTel)**: detection/redaction/mask/block/allow counts, per-API latency histograms
  (p50/p95/p99), failure/timeout counts, fail-open-exception counts, cache hit rate — all aggregate,
  no values.
- **Traces (OTel)**: spans for auth, policy resolve, detect, transform — attributes limited to
  de-identified metadata (entity types/counts, policy version), enforced by the scrubber.
- **Audit**: decision events and access-control events (incl. denied cross-tenant attempts, raw-value
  opt-in uses, fail-open exceptions).
- **Leakage guard**: a centralized scrubbing layer + tests assert no field can carry raw PII.

## Failure Modes & Fail-Open vs Fail-Closed

| Failure | Behavior |
|---------|----------|
| Detection engine error/timeout/unavailable ("uncertain result") | **Fail-closed**: block whole request, safe error, audited |
| Partial redaction failure (some segments un-transformable) | **Fail-closed** for the whole request (FR-036) — never partial-protected-as-complete |
| Policy store unavailable | Serve last-known-good cached policy if within TTL; else fail-closed to secure-default-or-block |
| Payload exceeds max size | Reject/fail-closed (never pass unprotected) |
| Low-confidence (below threshold) detection | Governed by policy's below-threshold stance (default allow-below-threshold) — distinct from fail-safe |
| Explicit fail-open policy (low-risk use case) | Content may pass; each occurrence audited as a fail-open exception (FR-015) |

**Fail-open vs fail-closed by policy type**: security/compliance-sensitive policies (e.g., financial,
health, government identifiers) MUST be fail-closed; explicitly designated low-risk, non-sensitive
use cases MAY opt into fail-open with mandatory auditing. Default for any unspecified policy is
fail-closed.

## Testing Strategy

- **Unit**: detectors (regex/NER/custom), transformer (redact/mask), overlap resolver, policy
  resolver (precedence + floor), scrubber.
- **Contract**: OpenAPI/schemathesis for both APIs (request/response shapes, error bodies, versioning,
  detection-does-not-modify-input).
- **Integration**: end-to-end inbound/outbound flows, JSON + unstructured, repeated/overlapping PII,
  multilingual/Unicode, large payloads, no-options default behavior, unconfigured-entity floor.
- **Security**: tenant isolation (cross-tenant denial + audit), authz, and **leakage scans** asserting
  zero raw PII in logs/traces/metrics/errors (SC-002, SC-017).
- **Resilience (fault injection)**: detection timeout/outage → fail-closed (SC-003), partial redaction
  failure → block (SC-018), policy-store outage → cached/secure fallback.
- **Detection quality**: labeled corpus measuring precision/recall (recall ≥ 95% in-scope, SC-001) with
  regression thresholds (NFR-014).
- **Performance**: load tests validating per-API p95 budgets (SC-019) and max-payload safe behavior
  (SC-010).

## Reuse of Existing Platform Capabilities (avoid new infrastructure)

- **Identity/Authorization**: reuse platform authN (JWT/mTLS) and authz scopes — no new IdP.
- **Tenant context**: reuse platform tenant-resolution mechanism.
- **Configuration/Policy storage**: reuse managed PostgreSQL; only add the guardrail schema.
- **Cache**: reuse platform Redis if available; otherwise in-process cache (no new dependency).
- **Observability/Audit**: reuse the platform OpenTelemetry collector and audit pipeline.
- **Orchestration/Deploy**: reuse existing container platform and CI/CD.
- **New components (minimal)**: the stateless PII Guardrails service, the policy schema, and the
  optional thin client SDK.

## Complexity Tracking

> No constitution violations — this section intentionally left empty (no unjustified complexity).
