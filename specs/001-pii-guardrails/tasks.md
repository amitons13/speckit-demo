---

description: "Task list for PII Guardrails implementation"
---

# Tasks: Enterprise PII Guardrails for AI Platform

**Input**: Design documents from `/specs/001-pii-guardrails/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests ARE included — the spec mandates automated coverage of detection, masking, blocking,
policy enforcement, and failure scenarios (Principle X / NFR-013, NFR-014, SC-001..SC-021).

## MVP Implementation Status (2026-08-16)

`/speckit-implement` was run scoped to the **two-API MVP** per an explicit directive. Conflict with
the broader plan (Presidio engine, PostgreSQL policy store, cache, outbound path, full observability
stack) was **resolved in favor of the two-API MVP**. Substitutions/deferrals:

- **Detection**: OpenAI-backed detector behind a swappable `PIIDetector` interface (instead of
  Presidio/spaCy). Structured output + span re-computation + output validation + fail-closed.
- **Done (this MVP)**: T001, T002, T005, T006, T007, T008, T024, T025, T026, T028, T029, T030, T031,
  T032, T034, T052, T056 (marked `[X]` below), plus partial safe-logging (T045-lite) and
  detector-swappability (T011-intent).
- **Deferred (out of MVP scope)**: PostgreSQL policy store & migrations, cache, secure-default-floor
  policy service, outbound/streaming path, tenant DB isolation, Presidio recognizers, JSON/Unicode
  span handling, full OTel metrics/traces/audit sinks, perf/load harness, precision-recall corpus,
  SDK, deploy/rollout. These remain unchecked for a future iteration.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Maps to a spec user story (US1..US8) when the task directly serves one; cross-cutting
  tasks reference FR/SC/NFR IDs instead
- File paths follow the structure in [plan.md](./plan.md)

## Story ↔ capability map

- US1 inbound protection · US2 outbound protection · US3 block · US4 mask · US5 configurable policies
- US6 fail-safe · US7 tenant isolation · US8 observability without leakage

---

## Phase 1: Foundation and Project Setup

**Purpose**: Project skeleton, dependencies, and shared scaffolding.

- [X] T001 Create the service structure per plan.md in `src/pii_guardrails/` (`api/`, `engine/`, `policy/`, `security/`, `observability/`, `core/`, `sdk/`) and `tests/` (`contract/`, `integration/`, `unit/`, `security/`, `resilience/`, `quality/`, `perf/`)
- [X] T002 Initialize the Python 3.11+ project with FastAPI, Pydantic, Presidio Analyzer/Anonymizer, spaCy, OpenTelemetry, pytest in `pyproject.toml`
- [ ] T003 [P] Configure linting/formatting/type-checking (ruff, black, mypy) in `pyproject.toml` and pre-commit config
- [ ] T004 [P] Add the base spaCy model as a build asset and document it in `README` (offline, shipped in image)
- [X] T005 Create `src/pii_guardrails/core/config.py` for environment-driven configuration (timeouts=300ms, max payload=256KB, budgets) per plan Constraints
- [X] T006 [P] Create `src/pii_guardrails/core/errors.py` with safe error types (no raw PII) and a request-id helper
- [X] T007 Add a health/readiness router in `src/pii_guardrails/api/health.py` and the FastAPI app factory in `src/pii_guardrails/api/app.py`

**Checkpoint**: App boots, health endpoint responds, tooling green.

---

## Phase 2: PII Detection Engine (defense in depth)

**Purpose**: Layered detection producing type/confidence/span — the core of both APIs (FR-002, FR-028, Principle II).

- [X] T008 [P] Define detection domain types (Detection, DetectionResult) in `src/pii_guardrails/engine/types.py` per data-model.md
- [ ] T009 [P] Implement regex/pattern recognizers (email, phone, credit card, IP, gov-id, bank acct, DOB) in `src/pii_guardrails/engine/detectors/regex_recognizers.py` (FR-002)
- [ ] T010 [P] Implement the NER recognizer adapter (Presidio+spaCy) in `src/pii_guardrails/engine/detectors/ner_recognizer.py` (FR-002, Principle II)
- [ ] T011 [P] Implement the custom/tenant recognizer plug-in interface in `src/pii_guardrails/engine/detectors/custom_recognizer.py` (FR-006, Principle VI)
- [ ] T012 Implement the layered analyzer that runs all recognizers and returns merged detections in `src/pii_guardrails/engine/analyzer.py` (depends on T009–T011)
- [ ] T013 Implement overlap/adjacency span resolution in `src/pii_guardrails/engine/resolver.py` (FR-023)
- [ ] T014 Implement JSON-aware traversal (field-path spans) + Unicode code-point spans in `src/pii_guardrails/engine/text_json.py` (FR-013, FR-032, FR-033)
- [ ] T015 [P] Unit tests for recognizers, analyzer merge, overlap resolver, JSON/Unicode spans in `tests/unit/test_engine_*.py` (SC-001 basis, SC-021)

**Checkpoint**: Given text/JSON, the engine returns accurate, de-duplicated detections with spans.

---

## Phase 3: Policy Management

**Purpose**: Tenant-aware policy storage, resolution, and the non-weakenable secure floor (US5, FR-005, FR-006, FR-007).

- [ ] T016 [P] [US5] Define Policy, EntityRule, SecureDefaultPolicy models in `src/pii_guardrails/policy/models.py` per data-model.md
- [ ] T017 [US5] Create the policy schema + migration for reused PostgreSQL in `src/pii_guardrails/policy/migrations/`
- [ ] T018 [US5] Implement the policy repository (CRUD, versioning, active-per-scope invariant) in `src/pii_guardrails/policy/store.py` (depends on T017)
- [ ] T019 [P] [US5] Implement the secure-default floor definition in `src/pii_guardrails/policy/secure_default.py` (FR-020, Principle I)
- [ ] T020 [US5] Implement scope-precedence resolution (use case > app > env > tenant) clamped to the floor in `src/pii_guardrails/policy/resolver.py` (FR-005; depends on T016, T019)
- [ ] T021 [US5] Implement the resolved-policy cache (Redis or in-process TTL, tenant-keyed) in `src/pii_guardrails/policy/cache.py` (Principle VII)
- [ ] T022 [P] [US5] Implement policy-config validation with safe errors in `src/pii_guardrails/policy/validation.py` (FR-021)
- [ ] T023 [P] [US5] Unit tests for precedence + floor clamping + validation in `tests/unit/test_policy_resolver.py` (SC-008, SC-011, SC-016)

**Checkpoint**: Effective policy resolves correctly per scope and never drops below the floor.

---

## Phase 4: Redaction and Masking

**Purpose**: Transform detected entities per action; threshold + below-threshold stance (US4, FR-004, FR-007, FR-008, FR-039).

- [X] T024 [P] [US4] Implement the redaction strategy (non-reversible placeholder) in `src/pii_guardrails/engine/transformers/redact.py` (FR-004)
- [X] T025 [P] [US4] Implement the masking strategy (keepLast/maskChar) in `src/pii_guardrails/engine/transformers/mask.py` (FR-004, US4)
- [X] T026 [US4] Implement the per-entity enforcement evaluator (apply action per occurrence; threshold; below-threshold stance) in `src/pii_guardrails/policy/evaluator.py` (FR-007, FR-008, FR-025, FR-039; depends on T020, T024, T025)
- [ ] T027 [US4] Ensure JSON structural validity after transformation in `src/pii_guardrails/engine/transformers/json_apply.py` (FR-008)
- [X] T028 [P] [US4] Unit tests for redact/mask correctness, repeated/consistent occurrences, threshold tuning in `tests/unit/test_transformers.py` (SC-007, SC-009, FR-012)

**Checkpoint**: Detected entities are transformed correctly and consistently per policy.

---

## Phase 5: Request/Input Guardrails — Detection & Redaction APIs 🎯 MVP

**Purpose**: Expose the two APIs on the inbound path (US1, FR-027–FR-031, FR-034). This is the MVP.

- [X] T029 [P] [US1] Add Pydantic request/response schemas from `contracts/detection-api.yaml` and `contracts/redaction-api.yaml` in `src/pii_guardrails/api/schemas.py`
- [X] T030 [US1] Implement `POST /v1/detect` (detection-only, must not modify input; raw values gated) in `src/pii_guardrails/api/detection.py` (FR-028, FR-029; depends on T012, T014)
- [X] T031 [US1] Implement `POST /v1/redact` (options or resolved/secure-default; never no-op; unconfigured → floor) in `src/pii_guardrails/api/redaction.py` (FR-030, FR-031; depends on T026)
- [X] T032 [US1] Implement input validation + payload-size limit (safe errors) in `src/pii_guardrails/api/validation.py` (FR-034, FR-022)
- [ ] T033 [P] [US1] Contract tests for both APIs (schemas, error bodies, detection-does-not-modify, versioning) in `tests/contract/test_detect_api.py`, `tests/contract/test_redact_api.py` (SC-014, SC-015, SC-020)
- [X] T034 [P] [US1] Integration tests: inbound prompt with single + multiple + repeated PII, JSON+text, no-options default in `tests/integration/test_inbound.py` (SC-016, SC-021, FR-012)

**Checkpoint (MVP)**: An app can detect PII and redact inbound prompts end-to-end with secure defaults.

---

## Phase 6: Response/Output Guardrails

**Purpose**: Protect model/tool responses; streaming disabled in v1 (US2, US3, FR-003, FR-026).

- [ ] T035 [US2] Implement the outbound evaluation path (full-response buffering; streaming disabled) in `src/pii_guardrails/api/redaction.py` outbound handler (FR-026; depends on T031)
- [ ] T036 [US3] Implement the block action (reject/remove offending segment per-entity; request proceeds) in `src/pii_guardrails/policy/evaluator.py` (FR-025; extends T026)
- [ ] T037 [P] [US2] Integration test: model response with PII redacted before return; zero-detection passthrough in `tests/integration/test_outbound.py` (SC-013)
- [ ] T038 [P] [US3] Integration test: block-designated + mask-designated entities in one request resolve per-entity in `tests/integration/test_block_mixed.py` (SC-012)
- [ ] T039 [P] [US2] Integration test: streaming source is fully evaluated before any content returns in `tests/integration/test_streaming_disabled.py` (SC-013)

**Checkpoint**: Both directions protected; mixed actions and block semantics correct.

---

## Phase 7: Security and Tenant Isolation

**Purpose**: AuthN/Z on every call; strict tenant isolation (US7, FR-016, FR-017, FR-035, NFR-008).

- [ ] T040 [US7] Implement authentication + authorization dependencies (reuse platform JWT/mTLS + scopes) in `src/pii_guardrails/security/authz.py` (FR-016, FR-035)
- [ ] T041 [US7] Implement tenant-context resolution + isolation enforcement (tenant-keyed policy/cache/audit) in `src/pii_guardrails/api/deps.py` (FR-017; depends on T021, T040)
- [ ] T042 [US7] Gate the Detection raw-value opt-in behind a privileged scope + audit hook in `src/pii_guardrails/api/detection.py` (FR-029; extends T030)
- [ ] T043 [P] [US7] Security tests: cross-tenant policy access denied + audited; unauthenticated/unauthorized rejected pre-processing in `tests/security/test_tenant_isolation.py` (SC-004)
- [ ] T044 [P] [US7] Security test: raw-value opt-in requires privileged scope and is audited in `tests/security/test_raw_value_gate.py` (FR-029)

**Checkpoint**: No cross-tenant access; all calls authenticated/authorized; raw-value path gated.

---

## Phase 8: Privacy-Safe Logging and Observability

**Purpose**: Metrics/traces/audit with de-identified data only (US8, FR-009, FR-010, FR-018, FR-019, NFR-011).

- [ ] T045 [US8] Implement the telemetry scrubber (allow-listed fields; blocks raw PII) in `src/pii_guardrails/security/scrubbing.py` (FR-010, NFR-011)
- [ ] T046 [P] [US8] Implement OTel metrics (detect/redact/mask/block/allow counts, per-API latency, failures, cache hit rate) in `src/pii_guardrails/observability/metrics.py` (FR-019)
- [ ] T047 [P] [US8] Implement OTel tracing with de-identified attributes only in `src/pii_guardrails/observability/tracing.py` (NFR-011)
- [ ] T048 [US8] Implement the de-identified audit emitter (decision, access-denied, fail-open, raw-value-optin, config-change) to reused audit store in `src/pii_guardrails/observability/audit.py` (FR-018; depends on T045)
- [ ] T049 [US8] Ensure decision metadata (types, counts, spans, confidence, policy version) returned without raw values in API responses (FR-009; touches T030, T031)
- [ ] T050 [P] [US8] Security/leakage tests scanning logs/traces/metrics/errors for raw PII across all scenarios in `tests/security/test_no_leakage.py` (SC-002, SC-017)

**Checkpoint**: Full observability with verified zero raw-PII leakage.

---

## Phase 9: Failure Handling and Resilience

**Purpose**: Fail-safe defaults, timeouts, partial-failure handling (US6, FR-014, FR-015, FR-036, NFR-004..NFR-006).

- [ ] T051 [US6] Implement fail-safe primitives (timeouts→safe action, uncertain-result classification) in `src/pii_guardrails/core/failsafe.py` (FR-014)
- [X] T052 [US6] Wire detection/redaction calls to fail-closed on error/timeout/unavailable (whole-request block) in `src/pii_guardrails/policy/evaluator.py` (FR-014; depends on T051)
- [ ] T053 [US6] Implement partial-redaction-failure → whole-request fail-closed in `src/pii_guardrails/api/redaction.py` (FR-036)
- [ ] T054 [P] [US6] Implement per-policy fail-open exception (low-risk use cases) with mandatory audit in `src/pii_guardrails/policy/evaluator.py` (FR-015)
- [ ] T055 [US6] Implement policy-store-outage fallback (last-known-good cache within TTL, else fail-closed) in `src/pii_guardrails/policy/store.py` (plan Failure Modes)
- [X] T056 [P] [US6] Resilience/fault-injection tests: detection timeout/outage → block; partial failure → block; store outage → fallback in `tests/resilience/test_failsafe.py` (SC-003, SC-018)

**Checkpoint**: System fails safe under all injected faults; fail-open only where explicitly configured + audited.

---

## Phase 10: Performance and Scalability

**Purpose**: Meet latency budgets and scale statelessly (FR-035, NFR-001..NFR-003, SC-005, SC-019).

- [ ] T057 Ensure the service is stateless and horizontally scalable (no local session state) — review in `src/pii_guardrails/api/app.py`
- [ ] T058 [P] Optimize hot paths (compiled recognizers, cached resolved policies, async I/O) in `src/pii_guardrails/engine/analyzer.py` and `policy/cache.py`
- [ ] T059 Enforce per-API latency budgets + timeouts and expose latency metrics (p50/p95/p99) (NFR-001; depends on T046)
- [ ] T060 [P] Implement large-payload safe behavior at max size (reject/fail-closed, never unprotected) in `src/pii_guardrails/api/validation.py` (FR-022, SC-010)
- [ ] T061 [P] Performance/load tests validating p95 ≤50ms (≤4KB) and ≤150ms (≤100KB) and max-payload behavior in `tests/perf/test_latency.py` (SC-005, SC-019, SC-010)

**Checkpoint**: Latency budgets met under load; large payloads handled safely.

---

## Phase 11: Testing (system-level & quality gates)

**Purpose**: Cross-cutting suites not owned by a single capability phase (avoids duplication).

- [ ] T062 [P] Build the labeled PII corpus + harness measuring precision/recall in `tests/quality/test_precision_recall.py` (SC-001, NFR-014, recall ≥95% in-scope)
- [ ] T063 [P] Add property/fuzz contract tests (schemathesis) against `contracts/*.yaml` in `tests/contract/test_property.py` (FR-038 versioning, FR-034 validation)
- [ ] T064 [P] End-to-end integration suite covering all 12 spec scenarios (multi-PII, JSON+text, large, multilingual) in `tests/integration/test_e2e_scenarios.py`
- [ ] T065 Add CI quality gates: block merge if leakage found, recall regresses, or p95 budget exceeded, in CI config
- [ ] T066 Run `quickstart.md` validation end-to-end and record results

**Checkpoint**: All quality gates green; measurable criteria (SC-001..SC-021) verified.

---

## Phase 12: Documentation and Rollout

**Purpose**: Make the capability usable and safely adoptable.

- [ ] T067 [P] Write the service README (run, configure, deploy) and API usage docs referencing `contracts/` in `docs/`
- [ ] T068 [P] Implement the optional thin client SDK/middleware (inbound+outbound interception; always calls Redaction with a resolved policy) in `src/pii_guardrails/sdk/`
- [ ] T069 [P] Document policy authoring + the secure-default floor + fail-open governance in `docs/policies.md` (FR-005, FR-015)
- [ ] T070 Add deployment manifests reusing existing platform infra (no new infra) in `deploy/`
- [ ] T071 Define a staged rollout (shadow/detect-only → enforce) and on-call/runbook in `docs/rollout.md`
- [ ] T072 Constitution compliance review sign-off before GA (Principles I–X) recorded in `docs/rollout.md`

**Checkpoint**: Documented, deployable, and rolled out with governance sign-off.

---

## Dependencies & Execution Order

### Phase-level

- **Phase 1 (Foundation)** → blocks everything.
- **Phase 2 (Detection)** + **Phase 3 (Policy)** → prerequisites for Phase 4 (Redaction) and the APIs.
- **Phase 4 (Redaction/Masking)** depends on Phases 2–3.
- **Phase 5 (Input APIs = MVP)** depends on Phases 2–4.
- **Phase 6 (Output)** depends on Phase 5.
- **Phases 7–10** are cross-cutting; start after Phase 5 (can overlap), but security (7), leakage (8),
  and fail-safe (9) MUST be complete before GA.
- **Phase 11 (Testing)** runs continuously; final gates after Phases 5–10.
- **Phase 12 (Docs/Rollout)** last.

### Story completion order (MVP-first)

1. **US1 (inbound detect+redact)** — MVP (Phase 5).
2. **US6 (fail-safe)** + **US7 (tenant isolation)** + **US8 (no leakage)** — required before GA (Phases 7–9).
3. **US2 (outbound)**, **US3 (block)**, **US4 (mask)** — Phases 4/6.
4. **US5 (configurable policies)** — Phase 3 (foundational for real multi-tenant use).

### Parallel opportunities

- Phase 1: T003, T004, T006 in parallel.
- Phase 2: T008–T011 and T015 in parallel (different files).
- Phase 3: T016, T019, T022, T023 in parallel.
- Phase 4: T024, T025, T028 in parallel.
- Cross-cutting test tasks (T033, T034, T037–T039, T043, T044, T050, T056, T061, T062–T064) are [P].

---

## Implementation Strategy

### MVP (strong privacy protection, minimal surface)

1. Phase 1 (Foundation) → Phase 2 (Detection) → Phase 3 (Policy) → Phase 4 (Redaction/Masking).
2. Phase 5 (Input APIs) with secure-default floor + fail-closed → **STOP & VALIDATE** (US1).
3. Add fail-safe (Phase 9), tenant isolation (Phase 7), and no-leakage (Phase 8) — these make the MVP
   safe to expose. This yields strong privacy protection while leaving policy richness and new
   detectors (custom recognizers, additional entity types) as incremental additions.

### Incremental delivery after MVP

- Outbound protection (Phase 6) → richer policy config/UX (Phase 3 extensions) → performance
  hardening (Phase 10) → SDK + rollout (Phase 12).

## Notes

- Tests are included per the spec's testability mandate (Principle X); each capability phase carries
  its focused tests, while Phase 11 owns system-level/quality-gate suites to avoid duplication.
- Every task references the FR/SC/NFR or design decision it satisfies for traceability.
- Security/privacy validation is embedded in Phases 7–9 and enforced as CI gates (T065).
