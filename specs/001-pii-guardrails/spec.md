# Feature Specification: Enterprise PII Guardrails for AI Platform

**Feature Branch**: `001-pii-guardrails`

**Created**: 2026-08-16

**Status**: Draft

**Input**: User description: "Create a specification for an enterprise PII Guardrails capability for an AI platform. AI applications can send prompts, conversations, tool inputs, tool outputs, and model responses containing personally identifiable information. The platform needs a centralized guardrail that can detect and protect PII before sensitive information is unnecessarily exposed to downstream AI services, logs, traces, or other platform components."

## Overview

The PII Guardrails capability is a centralized policy-enforcement service that inspects content
flowing through the enterprise AI platform and protects personally identifiable information (PII)
before it is exposed to downstream AI services, logs, traces, metrics, or other components. It
evaluates both inbound content (user prompts, conversation history, tool inputs) and outbound
content (model responses, tool outputs), applies a configurable policy, and returns a protected
version of the content along with explanatory metadata — without ever exposing or persisting the
original sensitive values.

This capability exists so that every AI application on the platform inherits consistent, auditable,
fail-safe PII protection without each team having to build its own. It directly operationalizes
the project constitution: privacy by default, defense in depth, fail-safe behavior, data
minimization, explainability, configurability, predictable performance, security & tenant
isolation, observability without leakage, and testability.

## Clarifications

### Session 2026-08-16

- Q: How should the guardrail handle streaming model responses where PII may span chunk
  boundaries? → A: Streaming is disabled for guarded responses in v1; the full response MUST be
  evaluated before any content is returned (no incremental/token-by-token emission through the
  guardrail).
- Q: When multiple policies match (application, tenant, environment, use case), how is the
  effective policy determined? → A: Most-specific-wins (precedence: use case > application >
  environment > tenant), bounded by a mandatory secure-default floor that a more specific policy
  can strengthen but never weaken.
- Q: Within a single request, when detected entities map to different actions, how is the outcome
  decided? → A: Per-entity independent — each detected entity's configured action is applied to
  its own occurrence/segment; the "block" action rejects/removes only that offending segment and
  the rest of the request still proceeds (it does not abort the whole request).
- Q: For a low-confidence detection, does below-threshold mean "allow" (FR-007) or "fail-safe"
  (FR-014)? → A: Configurable per policy — each policy chooses "allow below threshold" or
  "fail-safe below threshold"; the default is allow. FR-014's "uncertain result" refers to
  detector errors/indeterminate/no-score responses, not merely low confidence scores.
- Q: When the detection service is unavailable or times out, what does the default fail-closed
  behavior return? → A: Block the entire request with a safe, actionable error outcome; no content
  is forwarded downstream; the caller may retry.
- Q: What API surface must the solution expose? → A: (Firm requirement) Exactly two primary APIs
  with separated responsibilities — a detection-only **PII Detection API** ("what PII is present?")
  and a policy-driven **PII Redaction API** ("given options, protect the PII"). See the API Surface
  section.
- Q: Should the PII Detection API return the raw detected value? → A: Off by default; raw values may
  be returned only via an explicit, authorization-gated (privileged scope), audited opt-in. Raw PII
  MUST never appear in logs/traces/metrics/errors regardless of this option. (Constitution-safe
  default retained; overrides an earlier "always return value" selection.)
- Q: What is the Redaction API's default when no options/policy are provided? → A: Apply the caller's
  resolved effective policy (FR-005); if none exists, apply the secure-default policy (privacy by
  default). It MUST NOT be a no-op. (Constitution-safe default retained; overrides an earlier
  "no-op" selection.)
- Q: In the Redaction API, what happens to a detected entity type not listed in the caller's
  options? → A: It is still protected per the non-weakenable secure-default floor; caller options
  may strengthen but never drop below the floor. (Constitution-safe default retained; overrides an
  earlier "leave unprotected" selection.)
- Q: How is the confidence threshold applied across the two APIs? → A: Both APIs support threshold
  filtering — the Detection API accepts an optional threshold (defaulting to a minimal floor) and
  returns all detections at/above it with their confidence scores; the Redaction API applies the
  effective policy threshold to decide which detections to act on.
- Q: Is the Redaction API idempotent? → A: No idempotency guarantee; callers MUST NOT rely on
  repeated calls producing identical output.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Protect inbound user input containing PII (Priority: P1)

An AI application forwards a user's prompt to the guardrail before sending it to a model or
downstream service. The guardrail detects PII in the prompt and applies the configured enforcement
action (e.g., redact or mask) so that the downstream service never receives raw PII, then returns
the protected content plus metadata describing what was found and what action was taken.

**Why this priority**: This is the core value of the capability and the most common flow. Without
inbound protection, sensitive data leaks to models, vendors, and logs on every request. This
single story delivers a viable MVP on its own.

**Independent Test**: Send a prompt containing a known PII value through the guardrail with a
default policy and verify the returned content has the PII removed/transformed, that the response
includes decision metadata, and that no raw PII appears anywhere in the output or telemetry.

**Acceptance Scenarios**:

1. **Given** a default policy with redaction enabled, **When** a user submits a prompt containing an
   email address, **Then** the returned content has the email replaced with a redaction placeholder
   and the response reports one detected `EMAIL` entity with its position and the action taken.
2. **Given** a policy that protects multiple entity types, **When** a prompt contains an email, a
   phone number, and a credit card number, **Then** all three are detected and protected, and the
   metadata lists each entity type and count without exposing the original values.
3. **Given** a request where the same PII value appears multiple times, **When** the guardrail
   processes it, **Then** every occurrence is protected consistently and the reported count reflects
   all occurrences.
4. **Given** a request whose body contains both structured JSON fields and unstructured natural
   language, **When** the guardrail processes it, **Then** PII is detected and protected in both the
   structured values and the free text, and the returned structure remains well-formed.

---

### User Story 2 - Protect outbound model responses (Priority: P1)

An AI application passes a model's response (or a tool's output) through the guardrail before
returning it to the end user or persisting it, so any PII generated or echoed by the model is
protected according to policy.

**Why this priority**: Models can emit or reflect PII (from context, retrieval, or hallucination).
Protecting only inbound content would still leak PII on the return path. Combined with Story 1 this
closes both directions of the data flow.

**Independent Test**: Feed a synthetic model response containing PII through the guardrail with a
policy that redacts on the outbound path, and verify the returned response is protected and
accompanied by decision metadata.

**Acceptance Scenarios**:

1. **Given** an outbound policy with redaction enabled, **When** a model response contains a
   person's name and a physical address, **Then** those values are redacted before the response is
   returned and the metadata records the detections.
2. **Given** the same policy configuration, **When** a model response contains no PII, **Then** the
   content is returned unchanged and metadata indicates zero detections with an `allow` outcome.
3. **Given** a guarded outbound response in v1, **When** the source produces the response as a
   token stream, **Then** the guardrail evaluates the complete response before returning any
   content (streaming/incremental emission through the guardrail is disabled), so no unevaluated
   tokens reach the caller.

---

### User Story 3 - Block (reject) highly sensitive content segments (Priority: P2)

For content that policy deems too sensitive to redact or mask (e.g., certain government identifiers
or financial data), the guardrail applies the **block** action to that occurrence: the offending
segment is rejected/removed rather than transformed, and a safe, actionable notice is returned,
while the remainder of the request still proceeds (per the per-entity resolution clarified for this
feature). Whole-request rejection is reserved for the fail-safe path (see User Story 6), not for the
normal block action.

**Why this priority**: Some values must never be passed through in any form, even redacted. Blocking
is a distinct enforcement outcome (reject vs. transform) that protects against the highest-risk
categories, and it builds on the detection foundation from P1.

**Independent Test**: Configure a policy to block on a specific high-sensitivity entity type, submit
content containing that entity alongside lower-sensitivity content, and verify the block-designated
segment is rejected/removed with a safe, non-leaking notice while the rest is processed normally.

**Acceptance Scenarios**:

1. **Given** a policy configured to block on government identifiers, **When** a request contains a
   government identifier, **Then** the guardrail rejects/removes that segment, returns a block
   outcome with a safe, actionable message for it, and does not forward that raw value downstream.
2. **Given** a blocked segment, **When** the caller inspects the response, **Then** it explains that
   the segment was blocked and which policy/entity category triggered it, without echoing the
   original sensitive value.
3. **Given** a request containing one block-designated entity and one mask-designated entity,
   **When** the guardrail processes it, **Then** the block-designated segment is rejected while the
   mask-designated value is masked in place, and the request otherwise proceeds.

---

### User Story 4 - Mask instead of fully redact (Priority: P2)

An application needs partial visibility (e.g., last four digits of a card) for usability while
still protecting the sensitive portion. The guardrail applies a masking strategy that preserves a
configured, non-sensitive portion.

**Why this priority**: Masking is a common enforcement action distinct from full redaction, needed
for support and verification use cases. It extends the enforcement actions from the P1 foundation.

**Independent Test**: Configure a masking strategy for a card number, submit content containing one,
and verify the output preserves only the configured visible portion and hides the rest.

**Acceptance Scenarios**:

1. **Given** a policy that masks credit card numbers to the last four digits, **When** a request
   contains a full card number, **Then** the returned content shows only the last four digits with
   the remainder masked.
2. **Given** a masking strategy for a given entity type, **When** multiple values of that type
   appear, **Then** each is masked consistently according to the configured strategy.

---

### User Story 5 - Configure detection policies, entity types, and confidence thresholds (Priority: P2)

Platform and application teams configure which entity types are protected, which enforcement action
applies to each, and the confidence threshold for detection — scoped by application, tenant,
environment, or use case — so behavior fits their domain and false positives can be tuned.

**Why this priority**: Different domains (healthcare, finance, support) require different entities,
actions, and sensitivity. Configurability makes the capability reusable across the platform, but it
depends on the detection/enforcement core existing first.

**Independent Test**: Define two different policies (e.g., one strict, one lenient with a higher
confidence threshold) and verify the guardrail applies the correct policy per scope and that raising
the threshold suppresses a borderline (false-positive) detection.

**Acceptance Scenarios**:

1. **Given** two applications with different policies, **When** each submits identical content,
   **Then** each result reflects its own application's configured entities and actions.
2. **Given** a borderline detection that was previously a false positive, **When** the confidence
   threshold for that entity type is raised above the detection's confidence, **Then** that value is
   no longer flagged, while genuine high-confidence detections still are.
3. **Given** a policy where an entity type is not in the protected set, **When** content contains
   that entity type, **Then** it is not acted upon (subject to privacy-by-default rules in
   Assumptions).

---

### User Story 6 - Fail safe when detection is unavailable or uncertain (Priority: P1)

When the underlying PII detection is unavailable, times out, errors, or returns an uncertain
result, the guardrail applies fail-safe behavior per policy (default fail-closed) rather than
letting unprotected content pass through.

**Why this priority**: This is the constitution's non-negotiable safety guarantee. A guardrail that
silently passes raw data through on failure is worse than none, because it creates false
confidence. It is P1 because correctness under failure is essential to trust.

**Independent Test**: Simulate detection-service unavailability and a timeout, and verify the
guardrail blocks/holds (default fail-closed) rather than returning unprotected content, and records
the failure without raw PII.

**Acceptance Scenarios**:

1. **Given** the detection service is unavailable, **When** a request is submitted under the default
   fail-closed policy, **Then** the guardrail blocks the entire request, does not forward any
   content downstream, and returns a safe, actionable response indicating protection could not be
   guaranteed (the caller may retry).
2. **Given** detection exceeds its latency budget, **When** the timeout triggers, **Then** the
   configured fail-safe action is applied instead of an unbounded wait or silent pass-through.
3. **Given** a policy that explicitly permits fail-open for a low-risk use case, **When** detection
   fails, **Then** content may pass, and the fail-open exception is recorded as an auditable event.

---

### User Story 7 - Enforce tenant isolation and authorization (Priority: P1)

Every call is authenticated and authorized, and policies, configuration, and audit records are
strictly isolated per tenant, so one tenant can never read or apply another tenant's PII policy or
data.

**Why this priority**: A shared guardrail holding the most sensitive data and policies must be a
hard security boundary. A cross-tenant leak would compromise everything the capability protects.

**Independent Test**: Attempt to read or apply Tenant B's policy while authenticated as Tenant A and
verify the attempt is denied and audited, and that Tenant A only ever sees its own configuration.

**Acceptance Scenarios**:

1. **Given** a caller authenticated for Tenant A, **When** it requests Tenant B's policy, **Then**
   the request is denied with an authorization error and the attempt is recorded in the audit trail.
2. **Given** an unauthenticated or unauthorized caller, **When** it invokes the guardrail, **Then**
   the request is rejected before any content processing occurs.

---

### User Story 8 - Observe operations without leaking PII (Priority: P2)

Operators get metrics and audit records — detection counts, redaction/mask/block counts, latency,
and failures — that are sufficient to run and investigate the system, while raw PII never appears in
logs, traces, metrics, or audit records.

**Why this priority**: The capability must be operable and auditable, but observability must not
become an exfiltration channel. It builds on the enforcement flow producing decisions to measure.

**Independent Test**: Process a batch of PII-bearing requests, then inspect all emitted logs,
traces, metrics, and audit records to confirm they contain aggregate/de-identified data only and no
raw PII.

**Acceptance Scenarios**:

1. **Given** normal processing, **When** requests containing PII are handled, **Then** metrics
   report detection/redaction/mask/block counts, latency, and failure counts without any raw PII.
2. **Given** logs and traces are generated during processing, **When** they are inspected, **Then**
   they contain only de-identified references (e.g., entity type, counts, positions, hashes/tokens)
   and never the original values.

---

### Edge Cases

- **Repeated PII**: The same value appearing many times is protected at every occurrence with a
  consistent transformation and an accurate count.
- **Mixed structured + unstructured content**: JSON payloads with free-text fields are protected in
  both the structured values and the natural-language text while remaining well-formed.
- **Large payloads**: Very large prompts and responses are processed within latency budgets or
  handled by a defined safe behavior (e.g., chunked processing, or fail-safe if limits are
  exceeded) rather than silently truncating or passing unprotected content.
- **Overlapping / adjacent entities**: When detected spans overlap (e.g., an email embedded in a
  longer identifier), the guardrail resolves them deterministically without corrupting surrounding
  text.
- **No PII present**: Content with no detections is returned unchanged with an `allow` outcome and
  zero-count metadata.
- **Partial detection failure on multi-part content**: If one segment cannot be evaluated reliably,
  fail-safe behavior applies to that segment per policy rather than to nothing.
- **Uncertain / borderline confidence**: A low confidence score below the threshold is governed by
  the policy's configurable below-threshold stance (allow-below-threshold by default, or
  fail-safe-below-threshold); a genuinely uncertain result (detector error/indeterminate) triggers
  fail-closed per FR-014. The two are handled distinctly, not by arbitrary guessing.
- **Malformed or non-text content**: Unsupported or malformed inputs are handled safely (rejected or
  fail-closed) rather than bypassing protection.
- **Configuration missing for a scope**: If no explicit policy exists for an application/tenant, the
  secure default policy applies (privacy by default).
- **Streaming responses (v1)**: A response produced as a token stream is fully buffered and
  evaluated before any content is returned; no partial/unevaluated tokens are streamed through the
  guardrail.
- **Mixed actions in one request**: Entities mapping to different actions (e.g., mask vs. block) are
  resolved per entity — the block-designated segment is rejected while others are transformed in
  place and the request otherwise proceeds.

## API Surface *(firm requirement)*

The solution MUST expose exactly two primary APIs with clearly separated responsibilities. Both
APIs are subject to all security, privacy, observability, and fail-safe requirements in this spec.

### 1. PII Detection API — "What PII is present?"

- **Purpose**: Detection-only. It answers what PII exists in the input so the caller can decide how
  to handle it.
- **Input**: A text payload — either plain text or structured JSON (see FR-032). Optional parameters
  include a confidence threshold and the entity types of interest.
- **Behavior**: MUST detect PII entities and MUST NOT modify, redact, or transform the input in any
  way.
- **Output**: A list of detections, each with **entity type**, **confidence score**, and
  **location/span** (and, for JSON, the field path), plus occurrence grouping for repeated values.
  By default the response MUST NOT include the raw detected value. Raw values MAY be returned only
  when an explicit, authorization-gated (privileged scope), audited opt-in is provided; even then,
  raw PII MUST NOT appear in logs, traces, metrics, or errors.
- **Threshold**: Accepts an optional confidence threshold (defaulting to a minimal floor) and
  returns all detections at or above it, with their scores, leaving the act/ignore decision to the
  caller.

### 2. PII Redaction API — "Given these options, protect the PII."

- **Purpose**: Given a payload and redaction options/policy, return a protected version of the
  payload.
- **Input**: A text payload (plain text or structured JSON) plus redaction options: which entity
  types to protect, the handling strategy per type (**redact** or **mask**), and an optional
  confidence threshold.
- **Behavior**: Detects PII and applies the configured actions **per entity/occurrence**
  (see FR-025). When **no options are provided**, it applies the caller's resolved effective policy
  (FR-005) or, if none exists, the secure-default policy — it MUST NOT be a no-op. A detected entity
  type not listed in the caller's options is still protected per the non-weakenable secure-default
  floor. The Redaction API applies the effective policy threshold to decide what to act on.
- **Output**: The transformed/redacted payload plus safe metadata describing the actions performed
  (entity types, counts, spans, actions, policy version) — with **no raw PII** in the response,
  logs, traces, metrics, or errors.
- **Idempotency**: Not guaranteed; callers MUST NOT rely on repeated calls producing identical
  output.

### Shared API Requirements

- Both APIs MUST enforce authentication, authorization, and tenant isolation (FR-016, FR-017).
- Both APIs MUST accept plain text and structured JSON and report detections/actions with
  format-appropriate locations (character spans for text, field paths for JSON).
- Both APIs MUST handle Unicode and multilingual text correctly, with spans expressed in a
  well-defined unit (Unicode code points).
- Both APIs MUST validate input and return a safe validation error for empty or malformed input,
  without leaking raw PII or internal detail.
- Both APIs MUST define and enforce per-API latency budgets and apply fail-safe behavior (FR-014) on
  detection failure/timeout.
- Both APIs MUST be versioned; backward-compatible (additive) changes MUST NOT break existing
  callers, and breaking changes MUST be introduced under a new explicit version.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST accept content for evaluation from any AI application on the platform
  through a single, consistent policy-evaluation flow, regardless of which application invokes it.
- **FR-002**: The system MUST detect configurable PII entity types including, at minimum: person
  names, email addresses, phone numbers, physical addresses, credit card numbers, bank account
  information, IP addresses, dates of birth, and government identifiers, plus additional
  configurable custom entity types.
- **FR-003**: The system MUST evaluate both inbound content (user prompts, conversation history,
  tool inputs) and outbound content (model/tool responses) using the applicable policy.
- **FR-004**: The system MUST support the enforcement actions **redact**, **mask**, **block**, and
  **allow**, selectable per entity type within a policy. Action semantics: **redact** replaces the
  value with a non-reversible placeholder; **mask** hides a configured portion while preserving a
  configured non-sensitive portion; **block** rejects/removes the offending segment (the request
  still proceeds — see FR-025); **allow** passes the value through unchanged.
- **FR-005**: The system MUST support policies scoped and resolvable by application, tenant,
  environment, and use case. When multiple policies match, the effective policy MUST be resolved by
  **most-specific-wins** precedence (use case > application > environment > tenant), bounded by a
  mandatory secure-default floor: a more specific policy MAY strengthen protection but MUST NOT
  weaken it below the secure default. The system MUST record which policy (and version) was
  effective for each decision (see FR-024).
- **FR-006**: The system MUST allow teams to define which PII entity types are protected within a
  given policy.
- **FR-007**: The system MUST support a configurable confidence threshold per entity type (and/or
  per policy) that determines whether a detection is acted upon. Each policy MUST support a
  configurable below-threshold stance of either **allow-below-threshold** (below-threshold
  detections are treated as no detection) or **fail-safe-below-threshold** (below-threshold
  detections are protected); the default stance is allow-below-threshold. A below-threshold
  confidence score is distinct from an "uncertain result" as defined in FR-014.
- **FR-008**: The system MUST return protected content in which every acted-upon detection has been
  transformed according to its enforcement action, applied **per entity/occurrence independently**,
  preserving the surrounding non-sensitive content and structural validity (e.g., valid JSON
  remains valid).
- **FR-009**: The system MUST return decision metadata for each evaluation, including the policy
  applied, entity types detected, occurrence counts, positions, confidence, and the action taken —
  expressed without exposing the original sensitive values.
- **FR-010**: The system MUST NOT write raw PII into application logs, traces, metrics, audit
  records, or error messages at any point.
- **FR-011**: The system MUST return safe, actionable responses when content is blocked or
  transformed, explaining the outcome without echoing the original sensitive value.
- **FR-012**: The system MUST protect all occurrences of a detected value consistently within a
  single evaluation and report an accurate occurrence count.
- **FR-013**: The system MUST detect and protect PII within both structured (e.g., JSON) and
  unstructured natural-language content in the same request.
- **FR-014**: The system MUST apply a defined fail-safe behavior when detection cannot be completed
  reliably — i.e., an **uncertain result**, defined as a detector error, timeout, unavailability,
  or indeterminate/no-score response (not merely a low confidence score, which is governed by
  FR-007). The default fail-safe behavior is **fail-closed**: the system MUST block the entire
  request with a safe, actionable error outcome, MUST NOT forward any content downstream, and the
  caller MAY retry. The system MUST never silently pass unprotected content downstream.
- **FR-015**: The system MUST allow a policy to explicitly opt into a fail-open exception for a
  defined low-risk use case, and MUST record each fail-open occurrence as an auditable event.
- **FR-016**: The system MUST authenticate and authorize every request before processing content.
- **FR-017**: The system MUST enforce tenant isolation so that policies, configuration, and audit
  records of one tenant are never readable or applicable by another tenant.
- **FR-018**: The system MUST record an audit trail of policy decisions and access-control events
  (including denied cross-tenant attempts) using de-identified references only.
- **FR-019**: The system MUST emit metrics for detection counts, redaction counts, mask counts,
  block counts, allow counts, latency, and failure counts, without recording sensitive values.
- **FR-020**: The system MUST apply the secure default policy (privacy by default) when no explicit
  policy is configured for the requesting scope.
- **FR-021**: The system MUST validate policy configuration before it takes effect and reject
  invalid configuration with a clear, non-leaking error.
- **FR-022**: The system MUST handle large inbound and outbound payloads by either processing them
  within the latency budget or applying a defined safe behavior when configured limits are exceeded.
- **FR-023**: The system MUST resolve overlapping or adjacent detected entities deterministically
  without corrupting surrounding content.
- **FR-024**: The system MUST expose which policy version was in effect for each decision to support
  auditing and reproducibility.
- **FR-025**: When a single request contains multiple detected entities that map to different
  enforcement actions, the system MUST resolve them **per entity independently** — each entity's
  configured action applies to its own occurrence. A **block** action MUST reject/remove only its
  own offending segment and MUST NOT abort the entire request; whole-request rejection occurs only
  on the fail-safe path (FR-014).
- **FR-026**: For guarded outbound responses in v1, the system MUST evaluate the complete response
  before returning any content; streaming/incremental (token-by-token) emission through the
  guardrail is disabled, and no unevaluated content may reach the caller.

#### API Surface Requirements

- **FR-027**: The system MUST expose exactly two primary APIs — a **PII Detection API** and a **PII
  Redaction API** — with clearly separated responsibilities (detection vs. protection).
- **FR-028**: The PII Detection API MUST be detection-only: it MUST NOT modify, redact, or transform
  the input, and MUST return, per detection, the entity type, confidence score, and location/span
  (plus field path for JSON) with occurrence grouping for repeated values.
- **FR-029**: The PII Detection API MUST NOT return raw detected values by default. Raw values MAY
  be returned only via an explicit, authorization-gated (privileged scope), audited opt-in; even
  when enabled, raw PII MUST NOT appear in logs, traces, metrics, or errors.
- **FR-030**: The PII Redaction API MUST accept a payload plus redaction options (entity types to
  protect, per-type strategy of redact or mask, optional threshold). When no options are provided,
  it MUST apply the caller's resolved effective policy (FR-005) or, if none exists, the
  secure-default policy — it MUST NOT be a no-op. A detected entity type not present in the caller's
  options MUST still be protected per the non-weakenable secure-default floor.
- **FR-031**: The PII Redaction API MUST return the transformed payload plus safe metadata (entity
  types, counts, spans, actions taken, policy version) without any raw PII in the response, logs,
  traces, metrics, or errors.
- **FR-032**: Both APIs MUST accept plain-text and structured-JSON payloads and report locations in a
  format-appropriate way (character spans for text, field paths for JSON).
- **FR-033**: Both APIs MUST correctly handle Unicode and multilingual text, expressing spans in a
  well-defined unit (Unicode code points).
- **FR-034**: Both APIs MUST validate input and return a safe validation error for empty or malformed
  input, without leaking raw PII or internal implementation detail.
- **FR-035**: Both APIs MUST define and enforce per-API latency budgets (p50/p95/p99) integrated with
  fail-safe behavior; on detection failure or timeout the Detection API MUST return a safe error
  (never unreliable partial results presented as authoritative) and the Redaction API MUST fail
  closed per FR-014.
- **FR-036**: The PII Redaction API MUST handle partial redaction failure by failing closed for the
  whole request (block) rather than returning partially-protected content as if complete.
- **FR-037**: The PII Redaction API is NOT required to be idempotent; the system MUST NOT rely on,
  nor promise, identical output across repeated calls with the same input and options.
- **FR-038**: Both APIs MUST be versioned. Backward-compatible (additive) changes MUST NOT break
  existing callers; breaking changes MUST be introduced under a new explicit API version.
- **FR-039**: Both APIs MUST support confidence-threshold filtering: the Detection API accepts an
  optional threshold (default minimal floor) and returns all detections at or above it with scores;
  the Redaction API applies the effective policy threshold to decide which detections to act on.

### Key Entities *(include if feature involves data)*

- **Evaluation Request**: A unit of content submitted for protection, with direction (inbound or
  outbound), the requesting application/tenant/environment context, and the content itself
  (structured and/or unstructured). Raw content is transient and never persisted.
- **Policy**: The set of rules governing protection for a scope — protected entity types, per-entity
  enforcement action, confidence thresholds, masking strategies, fail-safe stance, and precedence.
  Policies are versioned, validated, and tenant-isolated.
- **Detection**: A single identified PII occurrence — its entity type, position/span, occurrence
  grouping, and confidence — represented without the raw value.
- **Enforcement Decision**: The outcome for a request or detection — action taken (redact/mask/
  block/allow), resulting transformation reference, and the policy/version that produced it.
- **Audit Record**: A tamper-evident, tenant-scoped, de-identified record of a decision or
  access-control event, sufficient to reconstruct *why* an outcome occurred without revealing PII.
- **Tenant**: An isolation boundary owning its policies, configuration, and audit records, with
  associated authorization scopes.
- **Metric / Telemetry Event**: An aggregated, de-identified operational signal (counts, latency,
  failures) emitted for observability.
- **Detection Result**: The Detection API's response for one input — a collection of Detections
  (type, confidence, span/field path, occurrence grouping), with raw values omitted unless the
  authorized opt-in is set.
- **Redaction Options**: Caller-supplied configuration for the Redaction API — protected entity
  types, per-type strategy (redact/mask), and optional threshold — layered above the secure-default
  floor.
- **Redaction Result**: The Redaction API's response — the transformed payload plus safe action
  metadata (types, counts, spans, actions, policy version), never containing raw PII.

## Non-Functional Requirements

### Performance & Scalability

- **NFR-001**: The system MUST define and enforce latency budgets (p50/p95/p99) per evaluation and
  MUST integrate timeouts with fail-safe behavior (no unbounded waits).
- **NFR-002**: The system MUST provide predictable, measurable overhead suitable for production AI
  workloads and MUST scale horizontally to sustain the platform's concurrent request volume.
- **NFR-003**: Added latency introduced by the guardrail MUST be measurable and reportable so teams
  can budget for it.

### Reliability & Failure Behavior

- **NFR-004**: The system MUST fail closed by default under partial or total dependency outages.
- **NFR-005**: Every external dependency call MUST have a timeout wired to a defined fail-safe
  action.
- **NFR-006**: Degraded modes (e.g., one detection layer unavailable) MUST still uphold the
  fail-safe stance rather than silently reducing protection.

### Security & Privacy

- **NFR-007**: Raw PII MUST NOT be persisted; original values exist only transiently in memory for
  the duration of the evaluation (data minimization).
- **NFR-008**: All access MUST be authenticated, authorized, and least-privilege, with security
  enforced server-side and never dependent on caller cooperation.
- **NFR-009**: Content in transit MUST be encrypted, and secrets MUST be managed securely.
- **NFR-010**: Defense in depth — protection MUST NOT depend on a single detection mechanism; the
  design MUST allow multiple independent detection techniques to be combined.

### Observability

- **NFR-011**: All telemetry (metrics, logs, traces, audit) MUST be de-identified and MUST be
  reviewable to guarantee raw PII cannot be reconstructed.
- **NFR-012**: The system MUST provide enough decision metadata to debug and audit outcomes without
  exposing sensitive values (explainability).

### Testability

- **NFR-013**: Detection, redaction, masking, blocking, policy enforcement, threshold behavior,
  tenant isolation, and failure scenarios MUST be covered by automated tests, including
  fault-injection tests for fail-safe behavior.
- **NFR-014**: Detection quality MUST be measurable via precision/recall against curated datasets so
  regressions can be detected.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Across a representative test corpus, at least 95% of PII occurrences of the configured
  entity types are detected and protected (recall ≥ 95% for in-scope entities).
- **SC-002**: Zero raw PII values appear in any log, trace, metric, or audit record across the full
  test corpus (100% suppression).
- **SC-003**: 100% of requests processed while the detection service is unavailable or times out
  result in fail-safe handling (no unprotected content forwarded), verified by fault-injection.
- **SC-004**: 100% of cross-tenant access attempts are denied and audited in testing.
- **SC-005**: The guardrail adds no more than a defined, published latency budget at p95 (e.g.,
  within the agreed millisecond target) under expected production load.
- **SC-006**: Every enforcement decision returns metadata identifying the policy (and version),
  entity types, counts, and action, for 100% of evaluations, with no sensitive values present.
- **SC-007**: When a confidence threshold is raised above a borderline detection's confidence, that
  false-positive detection is suppressed while all genuine high-confidence detections remain — the
  false-positive rate is tunable via configuration.
- **SC-008**: The same content submitted under two different application/tenant policies yields
  outcomes consistent with each policy in 100% of cases (correct policy resolution).
- **SC-009**: All configured enforcement actions (redact, mask, block, allow) produce their expected
  transformation for their configured entity types across the test suite.
- **SC-010**: Large payloads at the defined maximum size are either processed within budget or
  handled by the defined safe behavior in 100% of cases — never passed through unprotected.
- **SC-011**: When multiple policies match a request, the effective policy equals the most-specific
  matching policy strengthened to never fall below the secure-default floor, in 100% of tested
  scope combinations.
- **SC-012**: In requests mixing block-designated and transform-designated entities, the
  block-designated segment is rejected and the transform-designated values are transformed in place
  while the request proceeds, in 100% of tested cases.
- **SC-013**: 100% of guarded outbound responses are fully evaluated before any content is returned;
  no unevaluated/partial content is emitted (verified by streaming-source tests).
- **SC-014**: The Detection API returns entity type, confidence, and span for 100% of detected
  entities, and returns zero raw values unless the authorized opt-in is set (0 raw values in the
  default configuration).
- **SC-015**: The Detection API never modifies the input — the input is byte-for-byte unchanged by a
  detection call in 100% of tested cases.
- **SC-016**: The Redaction API called with no options applies the resolved or secure-default policy
  (never a no-op) in 100% of tested cases, and unconfigured entity types remain protected per the
  secure-default floor.
- **SC-017**: Across both APIs and all telemetry, zero raw PII values appear in logs, traces,
  metrics, audit records, or error messages (100% suppression), including for the Detection API's
  authorized raw-value opt-in path.
- **SC-018**: Redaction partial failures result in fail-closed (whole-request block) — never
  partially-protected output presented as complete — in 100% of fault-injection tests.
- **SC-019**: Both APIs meet their published per-API p95 latency budgets under expected production
  load.
- **SC-020**: Backward-compatible API changes do not break a conformance suite representing existing
  API-version callers (100% pass).
- **SC-021**: Both APIs correctly detect/protect PII in plain-text and structured-JSON payloads,
  including multilingual/Unicode text, across the test corpus, with spans that map back to the exact
  source positions.

## Assumptions

- **Privacy by default scope**: When no explicit policy is configured for a scope, a secure default
  policy protecting the standard entity set (FR-002) applies. Entity types outside a *configured*
  policy's protected set are not acted upon, but the absence of any policy never means "no
  protection."
- **Detection mechanism is abstracted**: The specification does not prescribe a specific detection
  engine or vendor. It assumes one or more detection mechanisms can be integrated and combined
  (defense in depth) behind the guardrail's evaluation flow.
- **Invocation pattern**: AI applications call the guardrail as a service on both the inbound and
  outbound paths. The exact transport/protocol is an implementation detail and out of scope here.
- **Identity & tenancy**: An existing platform identity/authorization mechanism provides
  authenticated caller identity and tenant context that the guardrail consumes.
- **Standard PII definitions**: "Government identifiers," "bank account information," and similar
  categories follow common enterprise/industry definitions; exact per-region formats are
  configurable and expandable via custom entity types.
- **Default enforcement stance**: The default fail-safe behavior is fail-closed; fail-open is only
  available as an explicit, audited, per-policy exception.
- **Retention**: Only de-identified audit and telemetry data are retained, following industry-
  standard retention practices; raw content is not retained.
- **Latency budget value**: A concrete numeric p95 latency target will be finalized during planning
  with platform stakeholders; the requirement to define, publish, and enforce one is fixed here.
- **Out of scope (v1)**: Non-text modalities (images, audio, video), automatic de-tokenization/
  re-identification workflows, long-term PII vaulting, and streaming/incremental (token-by-token)
  guarded emission are out of scope for the initial version. Guarded responses are evaluated as
  complete payloads before return (FR-026).
- **Below-threshold default stance**: Policies default to allow-below-threshold; high-sensitivity
  policies may opt into fail-safe-below-threshold (FR-007).
- **Policy precedence**: Most-specific-wins (use case > application > environment > tenant) bounded
  by a non-weakenable secure-default floor (FR-005).
- **Two-API architecture (firm)**: The solution exposes exactly two primary APIs — Detection and
  Redaction — with separated responsibilities (FR-027). This is a fixed architectural requirement,
  not an assumption open to change.
- **Detection raw-value exposure**: Off by default; available only via an authorization-gated,
  audited opt-in (FR-029). This preserves the constitution's data-minimization principle and
  overrides an earlier request to always return raw values.
- **Redaction defaults**: With no options, the Redaction API applies the resolved/secure-default
  policy (never a no-op), and unconfigured entity types stay protected per the floor (FR-030). This
  preserves privacy-by-default and overrides earlier "no-op" / "leave unprotected" selections.
- **Threshold filtering**: Both APIs support threshold filtering (FR-039); the Detection API's
  default is a minimal floor so callers see all candidate detections with scores.
- **Idempotency**: The Redaction API is not guaranteed idempotent (FR-037).

## Dependencies

- An existing platform authentication/authorization and tenant-context mechanism.
- One or more PII detection mechanisms that can be integrated behind the guardrail.
- A platform observability stack capable of ingesting de-identified metrics, logs, traces, and
  audit records.
