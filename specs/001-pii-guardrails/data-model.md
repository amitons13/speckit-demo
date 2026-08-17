# Phase 1 Data Model: PII Guardrails

Entities derived from the spec's Key Entities and requirements. **No entity stores raw PII.** Raw
content and raw detected values are transient (in-memory, request-scoped) and never persisted.

## Persisted entities

### Policy

Governs protection for a scope. Versioned, validated, tenant-isolated.

| Field | Type | Notes |
|-------|------|-------|
| id | uuid | PK |
| tenant_id | string | isolation key (required) |
| scope_type | enum(use_case, application, environment, tenant) | precedence dimension |
| scope_id | string | e.g., app id, env name, use-case id |
| version | int | monotonically increasing per (tenant, scope) |
| status | enum(draft, active, retired) | only one active per (tenant, scope) |
| protected_entities | list<EntityRule> | see below |
| default_below_threshold_stance | enum(allow, fail_safe) | default `allow` |
| fail_safe_stance | enum(fail_closed, fail_open) | default `fail_closed`; `fail_open` audited |
| created_at / created_by | timestamp / identity | audit |

Validation: must not weaken below the secure-default floor; `fail_open` allowed only for
explicitly designated low-risk use cases; exactly one `active` per (tenant, scope).

### EntityRule (embedded in Policy)

| Field | Type | Notes |
|-------|------|-------|
| entity_type | enum + custom | e.g., EMAIL, PHONE, CREDIT_CARD, GOV_ID, custom |
| action | enum(redact, mask, block, allow) | per-type action |
| mask_config | object? | e.g., keep_last=4, mask_char |
| threshold | float [0..1]? | overrides policy/entity default |

### SecureDefaultPolicy (system-owned floor)

The non-weakenable baseline: the standard entity set (FR-002) each protected with a safe default
action (redact) and default threshold. Tenant/app policies may strengthen but never drop below it.

### AuditRecord (de-identified)

| Field | Type | Notes |
|-------|------|-------|
| id | uuid | PK |
| tenant_id / application_id | string | scoping |
| request_id | string | correlation |
| event_type | enum(decision, access_denied, fail_open_used, raw_value_optin_used, config_change) | |
| entity_summary | list<{type, count, confidence_bucket}> | **no raw values, no spans of raw text content** |
| action_summary | list<{type, action, count}> | |
| outcome | enum(allowed, transformed, blocked, error) | |
| policy_version | int | reproducibility |
| identity | string | actor (attributable) |
| created_at | timestamp | append-only, tamper-evident |

## Transient (in-memory, never persisted) structures

### EvaluationRequest

Direction (inbound|outbound), format (text|json), payload (transient), tenant/app/env/use-case
context, optional options (Redaction) or params (Detection). Dropped at end of request scope.

### Detection

| Field | Type | Notes |
|-------|------|-------|
| entity_type | string | |
| confidence | float [0..1] | |
| start / end | int | span in Unicode code points (text) |
| path | string? | JSON field path (json) |
| occurrence_id | string | groups repeated identical values |
| value | string? | **omitted by default**; present only under gated Detection opt-in |

### DetectionResult

List<Detection> + optional policy_version + request_id. Detection never modifies input.

### RedactionOptions

entities: list<entity_type>, strategy_per_type: map<type, redact|mask>, mask_config?, threshold?.
Layered above the secure-default floor.

### EnforcementDecision / RedactionResult

transformed_payload (transient, returned to caller), action_summary (types/actions/counts/spans),
outcome, policy_version, request_id. No raw PII beyond the transformed payload itself.

## Relationships

- Tenant 1—* Policy; Policy 1—* EntityRule (embedded).
- Policy resolution combines matching Policies by precedence, clamped by SecureDefaultPolicy.
- Each API call produces one EnforcementDecision/DetectionResult and one (or more) AuditRecord(s).
- AuditRecord references policy_version but never the raw content.

## State transitions

- **Policy**: draft → active (on validated publish; supersedes prior active) → retired.
- **Request outcome**: received → validated → detected → {transformed | blocked | allowed | error}.
  `error` (uncertain result) always maps to fail-closed `blocked` under default stance.
