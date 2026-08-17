<!--
SYNC IMPACT REPORT
==================
Version change: (none) → 1.0.0
Change type: MAJOR (initial ratification of the constitution)

Modified principles: N/A (initial adoption)

Added principles:
  - I. Privacy by Default
  - II. Defense in Depth
  - III. Fail-Safe Behavior (NON-NEGOTIABLE)
  - IV. Data Minimization
  - V. Explainability & Auditability
  - VI. Configurability
  - VII. Predictable Performance
  - VIII. Security & Tenant Isolation
  - IX. Observability Without Leakage
  - X. Testability (NON-NEGOTIABLE)

Added sections:
  - Security & Compliance Requirements
  - Performance & Reliability Standards
  - Development Workflow & Quality Gates
  - Governance

Removed sections: None

Templates requiring review:
  - .specify/templates/plan-template.md ✅ (no changes required; reads constitution at runtime)
  - .specify/templates/spec-template.md ✅ (no changes required)
  - .specify/templates/tasks-template.md ✅ (no changes required)
  - .specify/templates/checklist-template.md ✅ (no changes required)

Follow-up TODOs: None
-->

# PII Guardrails Platform Constitution

The PII Guardrails Platform ("the Platform") is an enterprise service that protects sensitive
and personally identifiable information (PII) flowing through AI applications. It detects,
redacts, masks, blocks, and audits PII across inbound prompts, tool calls, retrieved context,
and model outputs. This constitution defines the non-negotiable principles that govern how the
Platform is designed, built, operated, and evolved.

## Core Principles

### I. Privacy by Default

PII MUST be detected and protected by default; protection is opt-out, never opt-in. Any request
processed without an explicit, authorized configuration MUST be treated as requiring maximum
protection. Disabling or weakening detection for an entity type, field, or tenant MUST require
explicit configuration, MUST be attributable to an identity, and MUST be recorded in an audit
trail. Secure defaults MUST never depend on the caller remembering to enable protection.

**Rationale**: Data exposure occurs most often through omission. Defaulting to protection ensures
new applications, new routes, and misconfigured clients are safe on day one.

### II. Defense in Depth

PII protection MUST NOT depend on a single detection or redaction mechanism. The Platform MUST
layer multiple independent techniques (e.g., pattern/regex, named-entity recognition, contextual
classifiers, deny-lists, and validation checks) so that failure or evasion of one layer does not
result in unprotected data. Redaction/masking MUST be applied defensively even when upstream
detection claims a field is clean, where feasible.

**Rationale**: No single detector achieves perfect recall. Independent, overlapping layers reduce
the probability that any single gap leads to a leak.

### III. Fail-Safe Behavior (NON-NEGOTIABLE)

If PII detection or redaction cannot be completed reliably, the Platform MUST fail safe (fail
closed) rather than allow potentially sensitive data to pass through unprotected. Timeouts,
dependency failures, model unavailability, or unexpected errors MUST result in blocking, holding,
or safely degrading the request per configured policy — never in silent pass-through of raw data.
Any fail-open behavior MUST be an explicit, per-policy, auditable exception owned by an authorized
approver.

**Rationale**: When correctness is uncertain, allowing sensitive data through is the most costly
failure mode. The safe default under uncertainty is to withhold, not to expose.

### IV. Data Minimization

The Platform MUST avoid unnecessarily storing, logging, or exposing raw PII. Raw sensitive values
MUST NOT be persisted or written to logs, traces, metrics, or error messages. When retention is
required for a defined purpose, it MUST use masked, tokenized, or otherwise de-identified
representations with the shortest viable retention period and a documented justification. Original
values MUST live only as long as needed to perform the protection operation in memory.

**Rationale**: Data that is never stored cannot be breached, subpoenaed, or leaked. Minimization
shrinks the attack surface and simplifies compliance.

### V. Explainability & Auditability

Security decisions MUST provide enough metadata to debug and audit them without exposing the
underlying sensitive values. Every decision (detected, redacted, masked, blocked, allowed) MUST
record what policy applied, which entity types were matched, positions/counts, confidence, and the
resulting action — using non-reversible references (e.g., entity type + offsets + hashes/tokens),
never the raw PII. Audit records MUST be sufficient to reconstruct why a decision was made.

**Rationale**: Operators must trust and verify the system. Explanations enable debugging and
compliance review while preserving the very privacy the Platform enforces.

### VI. Configurability

The Platform MUST allow different AI applications and tenants to configure detection entities,
masking/redaction strategies, thresholds, and enforcement policies independently. Configuration
MUST be validated, versioned, and expressible without code changes. Every configurable dimension
MUST have a secure default, and configuration changes MUST be auditable and reversible.

**Rationale**: Different domains (healthcare, finance, support) have different sensitivity models.
Flexibility must not come at the cost of secure defaults or auditability.

### VII. Predictable Performance

PII protection MUST introduce predictable, measurable latency suitable for production AI
workloads. The Platform MUST define and publish latency budgets and MUST enforce them through
measured p50/p95/p99 targets and load testing. Performance-related timeouts MUST integrate with
Principle III (fail-safe): exceeding a budget MUST trigger a defined safe action, not an
unbounded wait or silent pass-through.

**Rationale**: A guardrail that makes AI applications unusably slow will be bypassed. Predictable,
bounded overhead is required for the Platform to be adopted and trusted in production.

### VIII. Security & Tenant Isolation

The Platform MUST enforce tenant isolation, authorization, secure defaults, and least-privilege
access. Every request MUST be authenticated and authorized; one tenant's data, configuration, and
audit records MUST NOT be accessible to another. Secrets MUST be managed securely, transport MUST
be encrypted, and components MUST run with the minimum privileges required. Security controls MUST
be enforced server-side and MUST NOT rely on client cooperation.

**Rationale**: A system entrusted with the most sensitive data must itself be a hardened boundary;
a breach of the guardrail is a breach of everything it protects.

### IX. Observability Without Leakage

The Platform MUST provide metrics, logs, traces, and audit information sufficient to operate and
investigate the system, while never leaking sensitive data. Telemetry MUST expose detection rates,
action counts, latency, error rates, and policy outcomes using aggregated or de-identified values
only. Any new telemetry MUST be reviewed to guarantee it cannot reconstruct raw PII.

**Rationale**: Operators need visibility to run the Platform reliably, but observability must never
become a covert exfiltration channel for the data being protected.

### X. Testability (NON-NEGOTIABLE)

PII detection, masking, redaction, blocking, policy enforcement, performance budgets, and failure
scenarios MUST be covered by automated tests. Fail-safe behavior (Principle III) MUST be verified
with explicit fault-injection tests (timeouts, dependency failures, malformed input). Detection
quality MUST be tracked with measurable precision/recall against curated datasets, and no
protection-affecting change may merge without passing the relevant test gates.

**Rationale**: Security and privacy guarantees are only real if they are continuously and
automatically verified; untested guardrails silently rot.

## Security & Compliance Requirements

- All PII-bearing data in transit MUST be encrypted; sensitive values MUST NOT be persisted in
  raw form (see Principle IV).
- Access to configuration, audit logs, and administrative functions MUST be role-based and
  least-privilege (see Principle VIII).
- Audit records MUST be tamper-evident, attributable to an identity, and retained per policy.
- Fail-open exceptions MUST be documented, time-bounded, approved, and reviewed.
- Data handling MUST support enterprise compliance obligations (e.g., data residency, retention,
  right-to-erasure) through masked/tokenized representations wherever possible.

## Performance & Reliability Standards

- Latency budgets (p50/p95/p99) MUST be defined per protection operation and validated under load.
- Every external dependency call MUST have a timeout wired to a defined fail-safe action.
- The Platform MUST degrade safely (fail closed by default) under partial outages.
- Capacity, throughput, and error-rate targets MUST be measurable and monitored (see Principle IX).

## Development Workflow & Quality Gates

- Every change affecting detection, redaction, masking, blocking, or policy enforcement MUST
  include automated tests covering success and failure paths (see Principle X).
- Code review MUST verify compliance with this constitution; reviewers MUST reject changes that
  weaken secure defaults, introduce raw-PII logging, or bypass fail-safe behavior.
- Detection-quality metrics (precision/recall) MUST NOT regress below agreed thresholds without
  explicit, documented sign-off.
- New telemetry, logs, and error messages MUST be reviewed for PII-leakage risk before merge.
- Configuration schema changes MUST be validated, versioned, and backward-compatible or
  accompanied by a migration plan.

## Governance

This constitution supersedes all other development practices for the Platform. In any conflict
between this document and other guidance, this constitution prevails.

- **Amendments**: Changes to this constitution MUST be proposed in writing, reviewed, and approved
  by the Platform's designated maintainers/security owners, and MUST include a migration or impact
  note when they change enforced behavior.
- **Versioning Policy**: This constitution follows semantic versioning:
  - MAJOR — backward-incompatible governance changes or principle removals/redefinitions.
  - MINOR — a new principle/section is added or guidance is materially expanded.
  - PATCH — clarifications, wording, and non-semantic refinements.
- **Compliance Review**: All PRs and reviews MUST verify compliance with these principles.
  Deviations MUST be justified, documented, time-bounded, and approved. Recurring or unjustified
  deviations MUST trigger remediation.

**Version**: 1.0.0 | **Ratified**: 2026-08-16 | **Last Amended**: 2026-08-16
