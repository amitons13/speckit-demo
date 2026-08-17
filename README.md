# PII Guardrails — a Spec Kit (Spec-Driven Development) Demo

This repository is a **complete, end-to-end demonstration of [GitHub Spec Kit](https://github.com/github/spec-kit)** — the toolkit for **Spec-Driven Development (SDD)**. It walks through every Spec Kit command in order, shows the *exact prompt* given to each one, and reproduces the *output* each command produced (console reports inline, and the full generated documents in collapsible sections + links to the canonical files under [`specs/`](./specs/001-pii-guardrails/)).

The example feature is an **enterprise PII Guardrails capability**: a centralized service that detects and protects personally identifiable information (PII) in AI prompts and responses. The demo ends with a working, tested **two-API MVP** (see [Part B](#part-b--the-delivered-mvp)).

> **How to read this document**
> - **[Part A](#part-a--the-spec-kit-walkthrough)** is the Spec Kit story: one section per command, each with *what it does → the prompt used → the output produced*.
> - **[Part B](#part-b--the-delivered-mvp)** is the runnable MVP that `/speckit.implement` produced (setup, run, test, configure).
> - Long generated documents are shown in `▶ collapsed` blocks so the page stays navigable. Every artifact is also a real file in this repo, linked from its section.

---

## What is Spec-Driven Development?

Traditional coding jumps straight to implementation. **SDD inverts that**: you first make the *intent* executable — principles, a specification, a plan, and a task list — and only then generate code, so the code is a *consequence* of a reviewed, self-consistent spec.

Spec Kit provides a sequence of slash-commands (run here inside Cursor) that each produce a durable artifact:

| # | Command | Question it answers | Primary output |
|---|---------|--------------------|----------------|
| 0 | `specify init` | "Set up the SDD workspace." | `.specify/`, `.cursor/` command + skill files |
| 1 | `/speckit.constitution` | "What principles are non-negotiable?" | [`constitution.md`](./.specify/memory/constitution.md) |
| 2 | `/speckit.specify` | "*What* must we build and *why*?" | [`spec.md`](./specs/001-pii-guardrails/spec.md) + quality checklist |
| 3 | `/speckit.clarify` | "Where is the spec ambiguous or conflicting?" | Clarifications recorded back into `spec.md` |
| 4 | `/speckit.plan` | "*How* will we build it?" | [`plan.md`](./specs/001-pii-guardrails/plan.md), [`research.md`](./specs/001-pii-guardrails/research.md), [`data-model.md`](./specs/001-pii-guardrails/data-model.md), [`contracts/`](./specs/001-pii-guardrails/contracts/), [`quickstart.md`](./specs/001-pii-guardrails/quickstart.md) |
| 5 | `/speckit.tasks` | "What are the concrete steps?" | [`tasks.md`](./specs/001-pii-guardrails/tasks.md) |
| 6 | `/speckit.implement` | "Build it." | `src/` + `tests/` (the MVP) |
| 7 | `/speckit.analyze` | "Are all the artifacts consistent?" | Cross-artifact consistency report (console) |

The **star of the demo is `/speckit.clarify`** — it caught three answers that *contradicted the constitution* and forced an explicit reconciliation. That is the moment SDD proves it is more than boilerplate generation.

---

# Part A — the Spec Kit walkthrough

## Step 0 — Environment & `specify init`

**Goal:** install the Spec Kit CLI and scaffold an SDD project wired for Cursor.

```powershell
# install the CLI (exposes the `specify` command)
pip install specify-cli        # or: uv tool install specify-cli
pip install uv                 # uv drives the Python env for the generated project

# scaffold this project (Cursor integration, shell scripts)
specify init . --ai cursor-agent --script sh
specify check                  # verifies prerequisites & lists valid integration IDs
```

**Output produced** — `specify init` created the SDD workspace:

```text
.specify/
├── memory/                # constitution lives here
├── scripts/bash/          # check-prerequisites.sh, create-new-feature.sh, ...
└── templates/             # spec/plan/tasks/checklist templates
.cursor/
├── commands/              # /speckit.* slash-commands
└── skills/                # speckit-* skills (constitution, specify, plan, ...)
```

> **Gotchas surfaced during the demo (and fixes):**
> - `uv` not found → `pip install uv`.
> - `bash` not on PATH (needed by the `sh` scripts) → added Git for Windows' `...\Git\bin` to PATH.
> - Wrong integration id `cursor` → the correct id is **`cursor-agent`** (confirmed by `specify check`).

---

## Step 1 — `/speckit.constitution`

**What it does:** establishes the project's *non-negotiable principles*. Every later command (and especially `/speckit.analyze`) treats the constitution as the supreme authority.

**Prompt given:** create a constitution for an enterprise PII Guardrails platform emphasizing privacy, defense-in-depth, fail-safe behavior, data minimization, auditability, configurability, performance, tenant isolation, leak-free observability, and testability.

**Output produced:** [`.specify/memory/constitution.md`](./.specify/memory/constitution.md) — **v1.0.0**, ratified with **10 core principles** (two marked NON-NEGOTIABLE). The command also emits a *Sync Impact Report* header recording the version bump and which templates were reviewed.

Ratification summary (from the generated file):

```text
Version: (none) → 1.0.0   (MAJOR — initial ratification)
Principles:
  I.  Privacy by Default
  II. Defense in Depth
  III.Fail-Safe Behavior (NON-NEGOTIABLE)
  IV. Data Minimization
  V.  Explainability & Auditability
  VI. Configurability
  VII.Predictable Performance
  VIII.Security & Tenant Isolation
  IX. Observability Without Leakage
  X.  Testability (NON-NEGOTIABLE)
Ratified: 2026-08-16 | Version: 1.0.0
```

<details>
<summary>▶ Full generated <code>constitution.md</code></summary>

The complete, ratified constitution is committed at **[`.specify/memory/constitution.md`](./.specify/memory/constitution.md)**. Its ten principles, in brief:

- **I. Privacy by Default** — PII is protected by default; weakening protection must be explicit, attributable, and audited.
- **II. Defense in Depth** — protection must not depend on a single detection/redaction mechanism; layer independent techniques.
- **III. Fail-Safe Behavior (NON-NEGOTIABLE)** — if detection/redaction can't complete reliably, fail *closed*; fail-open only as an explicit, audited, per-policy exception.
- **IV. Data Minimization** — never persist/log raw PII; originals live only in memory for the duration of the operation.
- **V. Explainability & Auditability** — every decision records policy, entity types, counts, positions, confidence, action — using non-reversible references, never raw PII.
- **VI. Configurability** — per-tenant/app entities, strategies, thresholds, policies; validated, versioned, with secure defaults.
- **VII. Predictable Performance** — defined & enforced p50/p95/p99 budgets; timeouts integrate with fail-safe.
- **VIII. Security & Tenant Isolation** — authN/Z on every call; one tenant can never read/apply another's data/policy/audit.
- **IX. Observability Without Leakage** — telemetry is aggregate/de-identified only; new telemetry reviewed for leak risk.
- **X. Testability (NON-NEGOTIABLE)** — detection/redaction/masking/blocking/policy/perf/failure paths must have automated tests, incl. fault injection and precision/recall tracking.

Plus sections: *Security & Compliance Requirements*, *Performance & Reliability Standards*, *Development Workflow & Quality Gates*, and *Governance* (semantic-versioned amendments).

</details>

---

## Step 2 — `/speckit.specify`

**What it does:** turns a plain-language feature request into a rigorous, testable specification — user journeys, functional & non-functional requirements, edge cases, and measurable success criteria — *without prescribing implementation*.

**Prompt given (abridged):** *"Create a specification for an enterprise PII Guardrails capability for an AI platform.* Detect common PII entities; support configurable detection policies by application/tenant/environment/use-case; support redact/mask/block/allow; apply to both inbound input and outbound responses; prevent raw PII in logs/traces/metrics/audit; return safe, actionable responses; configurable confidence thresholds; defined behavior when detection is unavailable/uncertain; tenant isolation & authorization; metrics without sensitive values; production-grade latency & scale. Cover 12 concrete scenarios (email in a prompt, multiple PII types, redact model response, block highly sensitive content, mask, false-positive tuning, detection service down, cross-tenant policy access, logging while processing PII, repeated PII, structured JSON + free text, large payloads). Define journeys, functional/non-functional/security/privacy/failure/observability requirements, measurable acceptance criteria, and edge cases. *Do not prescribe implementation.*"*

**Output produced:** [`specs/001-pii-guardrails/spec.md`](./specs/001-pii-guardrails/spec.md) plus a **spec-quality checklist**. At this stage the spec contained 8 prioritized user stories, ~26 functional requirements, 14 NFRs, and measurable success criteria — with ambiguous points parked in an *Assumptions* section rather than left as silent gaps.

The quality checklist ([`checklists/requirements.md`](./specs/001-pii-guardrails/checklists/requirements.md)) reported **PASS on all items**:

```text
Content Quality        : [x] no impl details  [x] user value  [x] non-technical  [x] all sections
Requirement Complete.  : [x] no [NEEDS CLARIFICATION]  [x] testable  [x] measurable  [x] tech-agnostic
                         [x] acceptance scenarios  [x] edge cases  [x] scope bounded  [x] deps/assumptions
Feature Readiness      : [x] FRs have acceptance criteria  [x] primary flows  [x] measurable outcomes
Result: PASS (iteration 1)
```

<details>
<summary>▶ What the generated <code>spec.md</code> contains (structure + highlights)</summary>

Full document: **[`specs/001-pii-guardrails/spec.md`](./specs/001-pii-guardrails/spec.md)**.

- **Overview** — a centralized, fail-safe, auditable guardrail that every AI app inherits; explicitly maps to the constitution.
- **User Stories (8, prioritized)** — inbound protection (P1), outbound protection (P1), block sensitive segments (P2), mask (P2), configurable policies/thresholds (P2), fail-safe when detection is down/uncertain (P1), tenant isolation & authorization (P1), observability without leakage (P2). Each has *why-this-priority*, an *independent test*, and *acceptance scenarios*.
- **Edge Cases** — repeated PII, mixed structured+unstructured, large payloads, overlapping spans, no PII, partial detection failure, uncertain/borderline confidence, malformed input, missing policy, streaming (v1), mixed actions in one request.
- **Requirements** — **FR-001…FR-039** functional requirements (incl. the API-surface block FR-027…FR-039 added during clarify) and **NFR-001…NFR-014** across performance, reliability, security/privacy, observability, testability.
- **Key Entities** — Evaluation Request, Policy, Detection, Enforcement Decision, Audit Record, Tenant, Metric/Telemetry Event, Detection Result, Redaction Options, Redaction Result.
- **Success Criteria** — **SC-001…SC-021**, all measurable (e.g., recall ≥ 95% in-scope; 100% raw-PII suppression in telemetry; 100% fail-safe under injected outage; 100% cross-tenant denials audited).
- **Assumptions / Dependencies** — privacy-by-default scope, abstracted detection engine, default fail-closed, the firm two-API architecture, raw-value exposure off-by-default, etc.

</details>

---

## Step 3 — `/speckit.clarify` (run twice) ⭐

**What it does:** critically reviews the spec, surfaces ambiguities/conflicts/risks, asks *only high-value* questions, and folds the answers back into `spec.md` — with a timestamped **Clarifications** log.

### Clarify — Session 1 (behavioral ambiguities)

**Prompt given (abridged):** *review critically — what happens when detection is uncertain? when the service is unavailable? can PII leak through logs/traces/metrics/errors? tenant isolation; policy precedence when multiple policies apply; confidence thresholds; false positives/negatives; structured vs unstructured; streaming; large payloads; latency; auditability without storing raw PII; differences between redact/mask/block/allow; consistency between input and output protection.*

**Output produced — resolutions written into the spec's *Clarifications* log:**

```text
Q: Streaming responses where PII spans chunk boundaries?
   → Streaming disabled in v1; full response evaluated before any content is returned.
Q: Multiple matching policies — how is the effective one chosen?
   → Most-specific-wins (use case > application > environment > tenant), bounded by a
     mandatory secure-default floor a policy may strengthen but never weaken.
Q: Different actions for different entities in one request?
   → Per-entity independent; "block" removes only the offending segment; the rest proceeds.
Q: Low-confidence = "allow" or "fail-safe"?
   → Configurable per policy (default allow-below-threshold). "Uncertain result" (FR-014)
     means detector error/indeterminate, NOT merely a low score.
Q: Detection unavailable/timeout — default behavior?
   → Fail-closed: block the whole request with a safe, actionable error; nothing forwarded.
```

### Clarify — Session 2 (firm two-API architecture) — where SDD earns its keep

**Prompt given (abridged):** *treat this as a firm requirement — expose exactly two APIs: (1) a **PII Detection API** (detection-only, returns entities + metadata, must not modify input, may optionally return the detected value) and (2) a **PII Redaction API** (takes options and returns a protected prompt). Clarify request/response contracts, thresholds, spans, whether the detection API returns raw values, redact vs mask, caller options, default behavior when no options are provided, behavior when an entity type isn't configured, repeated/overlapping entities, invalid input, large/Unicode text, timeouts, tenant isolation, idempotency, versioning, and measurable acceptance criteria.*

**Output produced — the pivotal moment:** three of the requested answers **conflicted with the ratified constitution**. Spec Kit flagged them instead of silently complying:

```text
CONFLICT DETECTED (spec ⟂ constitution):
  1) "Detection API always returns the raw PII value"
        ⟂ Principle I (Privacy by Default) & IV (Data Minimization)
  2) "Redaction API with no options is a no-op"
        ⟂ Principle I (Privacy by Default)
  3) "Unconfigured entity types are left unprotected"
        ⟂ Privacy-by-default secure-default floor

Options presented to the user:
  A) Keep the constitution's SAFE defaults, override the three conflicting answers   ← chosen
  B) Amend the constitution (separate, explicit governance change)
  C) Keep answers as documented exceptions
```

The user chose **(A)**. The reconciled resolutions were written into the spec:

```text
• Detection raw-value return  → OFF by default; allowed only via an authorization-gated,
                                audited opt-in; raw PII never in logs/traces/metrics/errors. (FR-029)
• Redaction with no options    → applies the resolved effective policy, else the secure-default
                                policy; MUST NOT be a no-op. (FR-030)
• Unconfigured entity types     → still protected per the non-weakenable secure-default floor. (FR-030)
• (non-conflicting, kept)       → both APIs support threshold filtering (FR-039);
                                Redaction API is NOT guaranteed idempotent (FR-037).
```

This session also added the firm **API Surface** section and requirements **FR-027…FR-039** and **SC-014…SC-021** to the spec.

> **Demo takeaway:** the clarify step is where SDD stops being "fancy autocomplete." It enforced governance, caught contradictions a human reviewer could easily miss, and forced an explicit, recorded decision.

The full clarification log is at the top of [`spec.md`](./specs/001-pii-guardrails/spec.md#clarifications); the reconciliation rationale is also recorded in the [quality checklist notes](./specs/001-pii-guardrails/checklists/requirements.md).

---

## Step 4 — `/speckit.plan`

**What it does:** produces a production-oriented technical plan from the spec + constitution, and generates the supporting design docs (research decisions, data model, API contracts, quickstart). It runs a **Constitution Check** gate before and after design.

**Prompt given (abridged):** *create a production technical plan — centralized guardrail service, policy evaluation layer, PII detection/classification, configurable thresholds, redaction/masking/blocking, inbound & outbound interception, structured JSON + unstructured text, streaming, tenant-aware config, authN/Z, secure PII handling, no PII leakage into telemetry, audit with metadata only, failure/timeout handling, fail-open vs fail-closed per policy, performance/scalability, observability, automated testing. Prefer clear interfaces & separation of concerns; avoid unnecessary infrastructure; make reuse of existing platform capabilities explicit.*

**Output produced:** five artifacts + a passing constitution gate.

**Constitution Check result (from the plan):**

```text
| Principle                         | Gate |
| I.  Privacy by Default            | PASS |
| II. Defense in Depth              | PASS |
| III.Fail-Safe (NON-NEGOTIABLE)    | PASS |
| IV. Data Minimization             | PASS |
| V.  Explainability & Auditability | PASS |
| VI. Configurability               | PASS |
| VII.Predictable Performance       | PASS |
| VIII.Security & Tenant Isolation  | PASS |
| IX. Observability Without Leakage | PASS |
| X.  Testability (NON-NEGOTIABLE)  | PASS |
Result: PASS (no violations)
```

<details>
<summary>▶ <code>plan.md</code> — architecture & key decisions</summary>

Full document: **[`plan.md`](./specs/001-pii-guardrails/plan.md)**.

- **Stack:** Python 3.11+, FastAPI + Pydantic, **Microsoft Presidio (Analyzer + Anonymizer) + spaCy** for layered detection (defense in depth), reused PostgreSQL (policy + de-identified audit) and Redis/in-process cache.
- **Resolved numbers (that the spec deferred):** p95 ≤ **50 ms** (≤ 4 KB) / ≤ **150 ms** (≤ 100 KB); detection timeout default **300 ms**; **max payload 256 KB**; ≥ 500 req/s per pod guide.
- **Components:** API layer → Policy evaluation layer → Detection engine (regex + NER + custom recognizers, span merge/resolve) → Transformer (redact/mask, per-entity block) → Security (authz, tenant isolation, telemetry scrubber) → Observability (OTel + de-identified audit) → optional thin client SDK.
- **Data flow** for inbound, outbound, detection-only, and failure paths; **security boundaries**; **data-handling lifecycle** (ingest → process → respond → discard → audit); **failure-mode table** (fail-closed vs. audited fail-open); **testing strategy** (unit/contract/integration/security/resilience/quality/perf); explicit **reuse of existing platform capabilities** to avoid new infra.

</details>

<details>
<summary>▶ <code>research.md</code> — 12 recorded decisions (D1…D12)</summary>

Full document: **[`research.md`](./specs/001-pii-guardrails/research.md)**. Each decision records rationale + alternatives considered:

- **D1** layered Presidio+spaCy+regex+custom (defense in depth) · **D2** Python/FastAPI/Pydantic · **D3** two URI-versioned APIs · **D4** most-specific-wins policy resolution with non-weakenable floor · **D5** threshold placement (Detection informational, Redaction enforcing) · **D6** fail-closed + 300 ms timeout · **D7** perf budgets & 256 KB max payload · **D8** centralized telemetry scrubber · **D9** reuse PostgreSQL/Redis, no raw PII stored · **D10** streaming disabled v1 · **D11** JSON + Unicode-codepoint spans · **D12** detection raw-value opt-in gated + audited.

</details>

<details>
<summary>▶ <code>data-model.md</code> — entities (no entity stores raw PII)</summary>

Full document: **[`data-model.md`](./specs/001-pii-guardrails/data-model.md)**.

- **Persisted:** `Policy` (versioned, tenant-scoped, with embedded `EntityRule`s), `SecureDefaultPolicy` (the non-weakenable floor), `AuditRecord` (de-identified: entity/action summaries, outcome, policy version, identity — never raw values/spans of content).
- **Transient (in-memory only):** `EvaluationRequest`, `Detection` (type/confidence/span/path/occurrenceId; `value` omitted by default), `DetectionResult`, `RedactionOptions`, `EnforcementDecision`/`RedactionResult`.
- **Relationships & state transitions:** Policy draft→active→retired; request received→validated→detected→{transformed|blocked|allowed|error}, where `error` (uncertain result) maps to fail-closed `blocked`.

</details>

<details>
<summary>▶ <code>contracts/</code> — OpenAPI 3 for both APIs</summary>

Full files: **[`contracts/detection-api.yaml`](./specs/001-pii-guardrails/contracts/detection-api.yaml)** and **[`contracts/redaction-api.yaml`](./specs/001-pii-guardrails/contracts/redaction-api.yaml)**.

- **Detection API** `POST /v1/detect` — bearer auth; request `{payload, format, threshold?, entityTypes?, returnValues?}`; response `{detections:[{type, confidence, start, end, path?, occurrenceId, value?}], policyVersion?, requestId}`; `value` present *only* when `returnValues=true` and caller is authorized. Errors: 400/401/403/413/**503** (fail-closed).
- **Redaction API** `POST /v1/redact` — request `{payload, format, options?{entities, strategyPerType(redact|mask), maskConfig{keepLast,maskChar}, threshold}}`; response `{transformedPayload?, outcome(transformed|allowed|blocked), actions:[{type, action, count, spans}], policyVersion, requestId}`. Errors: 400/401/403/413/**422** (blocked, fail-closed).

</details>

<details>
<summary>▶ <code>quickstart.md</code> — 7 runnable validation scenarios</summary>

Full document: **[`quickstart.md`](./specs/001-pii-guardrails/quickstart.md)**. `curl`-based scenarios that map to success criteria: (1) detect-without-modify (SC-014/015), (2) redact+mask with options (SC-009), (3) no-options secure-default is never a no-op (SC-016), (4) JSON + repeated + multilingual (SC-021), (5) fail-closed when detection is down → HTTP 422 (SC-003), (6) tenant isolation → HTTP 403 (SC-004), (7) grep telemetry for raw PII → `CLEAN` (SC-002/017); plus automated `pytest` suites.

</details>

---

## Step 5 — `/speckit.tasks`

**What it does:** decomposes the plan into an actionable, dependency-ordered, phase-based task list, tagging parallelizable tasks `[P]` and mapping each task to the user story / requirement it serves.

**Prompt given (abridged):** *generate a task breakdown organized into phases — (1) foundation, (2) PII detection, (3) policy management, (4) redaction/masking, (5) input guardrails, (6) output guardrails, (7) security & tenant isolation, (8) privacy-safe logging & observability, (9) failure handling & resilience, (10) performance & scalability, (11) testing, (12) docs & rollout. Each task independently actionable, referencing its requirement, with dependencies, distinguishing implementation vs test tasks, embedding security/privacy validation, and prioritizing an MVP that delivers strong privacy protection.*

**Output produced:** [`tasks.md`](./specs/001-pii-guardrails/tasks.md) — **72 tasks (T001–T072) across 12 phases**, with a story↔capability map, per-phase checkpoints, a dependency/execution-order section, and an MVP-first strategy.

```text
Phase 1  Foundation & setup ............ T001–T007
Phase 2  Detection engine (defense-in-depth) T008–T015
Phase 3  Policy management ............. T016–T023
Phase 4  Redaction & masking ........... T024–T028
Phase 5  Input APIs 🎯 MVP ............. T029–T034
Phase 6  Output guardrails ............. T035–T039
Phase 7  Security & tenant isolation ... T040–T044
Phase 8  Privacy-safe logging & obs. ... T045–T050
Phase 9  Failure handling & resilience . T051–T056
Phase 10 Performance & scalability ..... T057–T061
Phase 11 Testing (system/quality gates)  T062–T066
Phase 12 Documentation & rollout ....... T067–T072
```

---

## Step 6 — `/speckit.implement`

**What it does:** executes the tasks to produce working, tested code.

**Prompt given (abridged):** *implement the MVP **strictly around the two APIs**. Do NOT build extra APIs, UI, dashboards, policy-management services, or databases unless strictly required. (1) **Detection API** — use an OpenAI model behind a **detector interface** to return structured PII results (type, confidence, span); do not modify the prompt. (2) **Redaction API** — reuse the same detection, apply caller options (redact/mask), preserve non-PII, handle repeated/multiple entities. Keep detection & redaction separate; use structured model output; **validate/constrain model output before using it** (don't trust model spans/classifications); handle malformed responses safely; never log prompts/PII/keys; add timeouts & safe failure; add unit + integration tests (multiple PII, repeated PII, no PII, invalid input, model failures, options). Before implementing, resolve any spec conflict in favor of the two-API MVP.*

**Output produced:** a runnable, fully-tested MVP (**34 tests green**). Because the prompt deliberately scoped a *minimal* subset of the 72 tasks, `/speckit.implement` recorded an **MVP Implementation Status** banner at the top of [`tasks.md`](./specs/001-pii-guardrails/tasks.md) and checked off only the genuinely-completed tasks — leaving the rest explicitly deferred:

```text
MVP Implementation Status (2026-08-16)
Conflict with the broader plan (Presidio engine, PostgreSQL store, cache, outbound path,
full observability stack) was RESOLVED IN FAVOR OF the two-API MVP.

Substitution: OpenAI-backed detector behind a swappable PIIDetector interface
              (instead of Presidio/spaCy) — structured output + span re-computation
              + output validation + fail-closed.

Done (this MVP): T001,T002,T005,T006,T007,T008,T024,T025,T026,T028,T029,T030,T031,
                 T032,T034,T052,T056  (+ safe-logging-lite, detector-swappability)
Deferred:        PostgreSQL policy store, cache, secure-default-floor service, outbound/
                 streaming path, tenant DB isolation, Presidio recognizers, JSON/Unicode
                 spans, full OTel metrics/traces/audit, perf/load harness, precision-recall
                 corpus, SDK, deploy/rollout.
```

See **[Part B](#part-b--the-delivered-mvp)** for exactly what the code does and how to run it.

---

## Step 7 — `/speckit.analyze`

**What it does:** a **strictly read-only** cross-artifact consistency check across `spec.md`, `plan.md`, and `tasks.md`, with the constitution as the supreme authority. It reports duplications, ambiguities, underspecification, constitution conflicts, coverage gaps, and inconsistencies — and never modifies files.

**Output produced (full report — this output is console-only and is preserved here):**

### Specification Analysis Report

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F1 | Inconsistency / Constitution | **HIGH** | plan.md deps ↔ tasks.md (T009–T012 vs MVP banner) ↔ code | Plan + tasks specify **Presidio + regex + NER** layered detection; the delivered MVP + banner use a **single OpenAI detector**. | Pick the canonical v1 detector (record OpenAI in the plan, or treat it as one layer); note defense-in-depth must be restored before GA. |
| F2 | Constitution Alignment | **HIGH** | constitution Principle II ↔ MVP | MVP relies on a single detection mechanism; Principle II forbids depending on one. | Add a second layer (e.g., regex recognizers for CREDIT_CARD/EMAIL/IP) before production (deferred T009). |
| F3 | Coverage Gap | MEDIUM | spec FR-024 | "Policy version in effect per decision" has no dedicated task (only implied). | Add a task to surface `policyVersion` in decision metadata + audit. |
| F4 | Coverage Gap | MEDIUM | spec FR-038 / SC-020 | API versioning/backward-compat has no dedicated task (only property test T063). | Add a task documenting versioning policy + a compatibility conformance suite. |
| F5 | Duplication | LOW | spec SC-002 ↔ SC-017 | Near-duplicate "zero raw PII in logs/traces/metrics." | Keep SC-017 as the superset; cross-reference SC-002. |
| F6 | Underspecification | LOW | spec FR-037 | "Idempotency NOT guaranteed" is a negative requirement with no verifying task (correct). | Optional: add a test asserting no idempotency reliance. |
| F7 | Terminology | LOW | spec prose ↔ data-model enums | "names"/"government identifiers" vs `PERSON`/`GOV_ID`. | Add a glossary mapping prose names to canonical enums. |
| F8 | Consistency (status) | LOW | tasks.md MVP banner | Banner marks large scope deferred — accurate; read coverage % as "planned," not "built." | None — banner is transparent. |

**Constitution Alignment:** only one MUST-principle gap — **Principle II (Defense in Depth)** is partially met by the single-detector MVP (F1/F2). `spec`/`plan`/`tasks` remain compliant, so this is a deliberate MVP deferral, not an artifact defect. Principles I, III, IV, V, VIII are upheld in the MVP (privacy-preserving default, fail-closed, no raw PII persisted/logged, safe metadata, key never exposed).

**Metrics:**

```text
Total requirements : 39 FR + 21 SC + 14 NFR = 74 (+ 8 user stories)
Total tasks        : 72
Coverage (≥1 task) : ~99% (only FR-024 lacks a dedicated task)
MVP build coverage : ~15 of 72 tasks (two-API core + fail-safe + safe logging)
Ambiguity count    : 0 blocking
Duplication count  : 1 (LOW)
Critical issues    : 0    High: 2 (F1, F2)
```

**Next actions:** no CRITICAL issues — safe to proceed. The two HIGH items share one root cause (single-detector MVP vs. defense-in-depth) and are fine for a demo but should be reconciled before production by (a) recording OpenAI as the sanctioned v1 detector in `plan.md` and (b) adding a second detection layer.

---

## The SDD loop, visualized

```text
                 ┌──────────────────────────────────────────────────────────┐
                 │                     constitution (v1.0.0)                  │
                 │   supreme authority — checked by plan & analyze            │
                 └───────────────┬──────────────────────────────────────────┘
                                 ▼
  specify ──▶ clarify ⭐ ──▶ plan ──▶ tasks ──▶ implement ──▶ analyze
  (spec.md)  (resolve &     (plan +   (72       (MVP code    (read-only
             reconcile      design    tasks)     + tests)     consistency
             conflicts)     docs)                             report)
                 ▲                                                 │
                 └──────────────── findings feed back ─────────────┘
```

---

# Part B — the delivered MVP

The two APIs `/speckit.implement` produced, ready to run.

- **API 1 — PII Detection** (`POST /v1/detect`): *"Tell me what PII is in this prompt."*
  Detection-only; never modifies the input; does not return raw PII values by default.
- **API 2 — PII Redaction** (`POST /v1/redact`): *"Given this prompt and these options, protect the PII."*
  Returns the redacted/masked prompt plus safe metadata.

Both APIs share one reusable detection component. Detection is isolated behind a `PIIDetector` interface (OpenAI-backed in this MVP) so the mechanism can be swapped later without touching the APIs or the redaction engine.

## Design highlights (security & privacy)

- **Structured model output** (JSON-schema constrained), not free-form text.
- **Spans are never trusted from the model** — every detected value is located in the original text by the service, so redaction only ever acts on real substrings.
- **Output is validated**: unknown entity types → `OTHER`, confidence clamped to `[0,1]`, hallucinated values (not present in the text) are dropped.
- **Fail-closed**: if detection times out/fails, `/v1/detect` returns `503` and `/v1/redact` returns `422 blocked` — the unprotected prompt is never returned.
- **No sensitive data in logs/traces/errors**: only de-identified metadata (counts, types, request ids). API keys are read from the environment and never exposed.

## Setup

```bash
uv venv --python 3.12
uv pip install -e ".[dev]"
cp .env.example .env   # add your OPENAI_API_KEY
```

## Run

```bash
uv run uvicorn pii_guardrails.api.app:app --reload --port 8080
```

## Test

```bash
uv run pytest
```

## Configuration (env)

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPENAI_API_KEY` | — | OpenAI credential (never exposed via the API) |
| `PIIGUARD_OPENAI_MODEL` | `gpt-4o-mini` | model name |
| `PIIGUARD_OPENAI_TEMPERATURE` | `0` | sampling temperature |
| `PIIGUARD_OPENAI_TIMEOUT_SECONDS` | `15` | per-call timeout |
| `PIIGUARD_MAX_PAYLOAD_BYTES` | `262144` | max input size (256 KB) |
| `PIIGUARD_DEFAULT_REDACTION_STRATEGY` | `redact` | default strategy |

## MVP scope

This is a deliberately minimal MVP: **exactly two APIs**. No database, policy-management service, UI, dashboards, or unrelated platform functionality — those are intentionally out of scope (and documented as deferred in [`tasks.md`](./specs/001-pii-guardrails/tasks.md)).

---

## Repository map

```text
PII-GR-Spec-Kit-Demo/
├── README.md                         # ← you are here (the demo walkthrough)
├── .specify/memory/constitution.md   # Step 1 output
├── specs/001-pii-guardrails/
│   ├── spec.md                       # Step 2 + 3 output (spec + clarifications)
│   ├── checklists/requirements.md    # Step 2 quality checklist
│   ├── plan.md                       # Step 4 output
│   ├── research.md                   # Step 4 output (decisions D1–D12)
│   ├── data-model.md                 # Step 4 output (entities)
│   ├── contracts/                    # Step 4 output (OpenAPI for both APIs)
│   │   ├── detection-api.yaml
│   │   └── redaction-api.yaml
│   ├── quickstart.md                 # Step 4 output (validation scenarios)
│   └── tasks.md                      # Step 5 output (72 tasks) + MVP status banner
├── src/pii_guardrails/               # Step 6 output — the MVP code
│   ├── api/ (app, routes, schemas)   # the two FastAPI endpoints
│   ├── detectors/ (base, openai_*)   # PIIDetector interface + OpenAI impl
│   ├── redaction/ (engine)           # redact/mask engine
│   ├── core/ (config, logging, errors)
│   └── service.py                    # reusable GuardrailService (shared by both APIs)
└── tests/ (unit + integration)       # Step 6 output — 34 tests
```

## Key takeaways for the demo

1. **Governance is executable.** The constitution isn't a doc that rots — `/speckit.plan` and `/speckit.analyze` actively check against it.
2. **`/speckit.clarify` prevents silent contradictions.** It caught three requests that violated the constitution and forced an explicit, recorded decision — the single most convincing moment of the demo.
3. **Traceability end-to-end.** Every task cites the FR/SC/NFR it serves; `/speckit.analyze` maps requirements → tasks → code and quantifies coverage.
4. **Scope honesty.** When the MVP intentionally implemented a subset, the tooling recorded exactly what was built vs. deferred, and `/speckit.analyze` flagged the one resulting constitution gap (defense-in-depth) to fix before production.
