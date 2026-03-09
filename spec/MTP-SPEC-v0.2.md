# MTP — Methodology Transfer Protocol

## Specification v0.2

**Author:** Lubor Fedák  
**Date:** 2026-03-09  
**Status:** Draft  
**Patch Release:** 0.2.1  
**License:** Apache 2.0  
**Supersedes:** v0.1

---

## 1. Problem Statement

### 1.1 The Methodology Gap

MCP connects models to tools. **MTP connects methodology authoring to methodology execution.**

Organizations and individuals increasingly use multiple AI platforms in their workflows. A sophisticated analytical methodology developed in one AI system (e.g., Claude, ChatGPT Pro) cannot be transferred to another system (e.g., enterprise Copilot, Azure OpenAI) without manual re-explanation of the entire context, intent, decision logic, and constraints.

This creates three compounding problems:

**Productivity Loss.** Knowledge workers spend significant time re-explaining methodologies across AI platforms. In enterprise settings with thousands of employees, this translates to tens of thousands of lost hours annually.

**Compliance-Driven Fragmentation.** Enterprise security policies prohibit sending sensitive data to commercial AI platforms. Workers develop sophisticated methodologies using commercial AI (which is more capable), then must manually transfer those methodologies to restricted enterprise AI (which has data access but less capability). The methodology degrades in transfer.

**Methodology Drift.** When a methodology is manually re-explained, critical nuances — edge case handling, decision rationale, validation rules, intent behind specific choices — are lost. The receiving AI system produces different results than the originating system would have, with no way to detect or measure the drift.

### 1.2 What Exists Today (and Why It's Not Enough)

| Solution | What it transfers | What it misses |
|----------|------------------|----------------|
| CTP (Context Transfer Protocol) | Role, instructions, metadata | Decision logic, validation rules, learned constraints |
| Plurality / AI Context Flow | Conversation history, preferences | Structured methodology, reproducibility |
| Copilot Skills / Ailloy | Pre-authored workflow templates | Cannot extract from organic conversations |
| Copy-paste prompts | Raw text | Structure, intent hierarchy, edge cases |
| A2A / ACP / MCP | Agent communication, tool access | Methodology portability, execution semantics |

None of these solutions extract a structured, reproducible methodology from an organic AI-human collaboration session, validate it for data leakage, execute it with deterministic semantics, and measure drift against a baseline.

### 1.3 Why This Problem Will Grow

As AI agents become autonomous and operate across systems, the need to transfer not just data or context, but **working methodology** — the logic of how to approach a problem — will scale from thousands of human workers to millions of AI agents. MTP is designed for both human-to-AI and future AI-to-AI methodology transfer.

### 1.4 Where MTP Sits in the Stack

```
┌─────────────────────────────────────────────────┐
│  Application Layer (user workflows, agents)      │
├─────────────────────────────────────────────────┤
│  MTP — Methodology Transfer Protocol             │
│  (authoring → validation → execution → drift)    │
├─────────────────────────────────────────────────┤
│  MCP — Model Context Protocol (tool access)      │
│  A2A — Agent-to-Agent (agent communication)      │
├─────────────────────────────────────────────────┤
│  LLM Layer (Claude, GPT, Gemini, Copilot, etc.) │
└─────────────────────────────────────────────────┘
```

MTP is not a communication protocol. It is not a tool access protocol. It is a **methodology control plane** — the missing layer between how methodology is authored and how it is executed across AI boundaries.

---

## 2. Core Concepts

### 2.1 Definitions

**Methodology.** A structured approach to solving a specific type of problem, consisting of intent, decision logic, transformation steps, validation rules, and constraints. A methodology is independent of specific data.

**MTP Package.** A self-contained, portable file that encodes a methodology in a structured format. It is both human-reviewable and machine-executable.

**Source System.** The AI platform where the methodology was originally developed through human-AI collaboration.

**Target System.** The AI platform where the methodology will be executed on actual data.

**Provenance.** A traceable link from each element of an MTP Package back to the source conversation segment, session, or decision event that produced it.

**Methodology Drift.** The measurable divergence between expected methodology outcomes and actual outcomes when a methodology is transferred to a different system, session, or point in time.

**Redaction.** The verifiable process of ensuring an MTP Package contains zero data, PII, client secrets, regulated fragments, or any content that ties the methodology to specific entities.

**Execution Semantics.** The precise definition of what constitutes success, failure, deviation, and partial completion when a target system executes an MTP Package.

### 2.2 Design Principles

1. **Data-free and verifiably so.** An MTP Package never contains actual data. This is not a declaration — it is enforced by policy checks and auditable by third parties.
2. **Platform-agnostic.** The format must be interpretable by any LLM-based system without platform-specific dependencies.
3. **Intent-preserving.** The package captures not just *what* to do, but *why* — the reasoning behind methodological choices.
4. **Provenance-tracked.** Every step, decision, and constraint in the package traces back to a source event.
5. **Human-readable.** An MTP Package is reviewable by a human before execution, serving as both documentation and executable specification.
6. **Execution-deterministic.** The package defines precise semantics for success, failure, deviation, and escalation — not suggestions, but rules.
7. **Drift-measurable.** Methodology transfer quality is quantifiable. Without measurement, portability is philosophy. With measurement, it is infrastructure.
8. **Incrementally buildable.** A methodology can be extracted from a single conversation or assembled from multiple sessions over time.
9. **Versionable and diffable.** Methodologies evolve. Changes are tracked, compared, and approved as first-class operations.

---

## 3. MTP Lifecycle

MTP is not a file format. It is a controlled execution loop with six phases:

```
┌──────────┐    ┌──────────┐    ┌──────────┐
│ EXTRACT  │───>│ VALIDATE │───>│ EXECUTE  │
└──────────┘    └──────────┘    └──────────┘
                                     │
┌──────────┐    ┌──────────┐         │
│ VERSION  │<───│ COMPARE  │<───┌────┴────┐
└──────────┘    └──────────┘    │ REPORT  │
                                └─────────┘
```

### 3.1 Extract

A conversation, workflow, or session is transformed into an MTP Package. Extraction captures intent, decision logic, steps, edge cases, dead ends, and provenance. Extraction can be performed by the source AI, by a dedicated extractor tool, or by a human author.

### 3.2 Validate

The package passes through a validation pipeline before it is eligible for execution:

**Schema validation.** The package conforms to the MTP JSON Schema.

**Policy check.** The package passes the policy envelope — no data, no PII, no secrets, no regulated fragments. This check is auditable and produces a signed validation report.

**Completeness score.** The package is scored for completeness: are all steps present? Do all steps have rationale? Are edge cases documented? Are dead ends captured? Is provenance populated? A completeness score below threshold triggers a warning or blocks execution.

**Redaction audit.** An automated scan verifies that no data from the source conversation leaked into the package. This is not a checkbox — it produces a machine-readable redaction report that lists every field checked and the result.

### 3.3 Execute

A target system receives the validated MTP Package and executes it against provided data. Execution follows strict semantics (see Section 6) — the target system does not improvise, does not skip steps, and reports every deviation.

### 3.4 Report

Execution produces a standardized Execution Report (see Section 7) that documents what happened at each step: status, validation results, deviations, edge cases encountered, and any novel situations not covered by the package.

### 3.5 Compare

The Execution Report is compared against a baseline — either a reference run, a previous execution of the same package, or expected outcomes defined in the package. Comparison produces a **Drift Score** (see Section 8) that quantifies how much the methodology degraded in transfer.

### 3.6 Version

The methodology is stored as an asset — versioned, diffable, signable, and publishable. Changes between versions are tracked as structured diffs, not text diffs. Approval workflows can gate version promotion.

---

## 4. MTP Package Format

An MTP Package is a structured YAML document. All sections from v0.1 are preserved. New in v0.2: `provenance`, `policy`, and stricter `execution_semantics`.

```yaml
mtp_version: "0.2"
package:
  id: <uuid>
  name: "Human-readable methodology name"
  version: "1.0.0"
  created: "2026-03-09T10:00:00Z"
  updated: "2026-03-09T10:00:00Z"
  author: "Name or identifier"
  source_platform: "claude-4.6"  # informational only
  tags: ["data-analysis", "financial", "compliance"]

# --- SECTION 1: INTENT ---
intent:
  goal: |
    High-level description of what this methodology achieves.
    This is the "why" — the business or analytical objective.
  context: |
    Background knowledge needed to understand why specific
    decisions were made. Domain assumptions, regulatory context,
    business rules that shaped the approach.
  success_criteria:
    - "Criterion 1: What constitutes a successful application"
    - "Criterion 2: Measurable outcome or quality threshold"
  non_goals:
    - "What this methodology explicitly does NOT attempt to do"

# --- SECTION 2: INPUT SPECIFICATION ---
input:
  description: |
    Description of expected input data characteristics.
  schema:
    - field: "field_name"
      type: "string | number | date | boolean | array | object"
      description: "What this field represents"
      required: true
      constraints: "Any validation rules for this field"
  assumptions:
    - "Assumption about data quality, completeness, format"
  preprocessing:
    - step: 1
      action: "Description of preprocessing step"
      rationale: "Why this preprocessing is necessary"

# --- SECTION 3: METHODOLOGY ---
methodology:
  approach: |
    High-level description of the analytical/processing approach.
    Why this approach was chosen over alternatives.

  steps:
    - step: 1
      name: "Step name"
      action: |
        Detailed description of what to do.
        Specific enough for an LLM to execute without ambiguity.
      rationale: |
        Why this step exists and why it's done this way.
        What would go wrong if skipped or done differently.
      provenance:
        source_type: "conversation | session | document | manual"
        source_ref: "conversation-id:message-range or session timestamp"
        confidence: "high | medium | low"
        notes: "How this step was derived from the source"
      decision_points:
        - condition: "If [condition]"
          then: "Do [action]"
          else: "Do [alternative action]"
          rationale: "Why this branch exists"
      execution_semantics:
        on_success: "proceed"
        on_failure: "halt | skip_with_flag | retry | escalate"
        on_deviation: "flag_and_proceed | halt | ask_human"
        timeout: "optional — max duration for this step"
        max_retries: 1  # required when on_failure is "retry"
      validation: |
        How to verify this step was executed correctly.
        Must produce a boolean pass/fail, not a subjective assessment.

    - step: 2
      name: "Next step name"
      action: |
        ...
      depends_on: [1]  # explicit dependency chain

# --- SECTION 4: EDGE CASES AND CONSTRAINTS ---
edge_cases:
  - scenario: "Description of edge case"
    handling: "How to handle it"
    rationale: "Why this handling was chosen"
    severity: "critical | warning | info"
    provenance:
      source_type: "conversation"
      source_ref: "Where this edge case was discovered"
      confidence: "high"

constraints:
  - type: "performance | accuracy | compliance | security"
    description: "Constraint description"
    enforcement: "How the target system should enforce this"

# --- SECTION 5: OUTPUT SPECIFICATION ---
output:
  description: |
    What the methodology produces.
  schema:
    - field: "field_name"
      type: "type"
      description: "What this output represents"
  quality_checks:
    - check: "Validation rule for output"
      failure_action: "What to do if check fails"
      is_blocking: true  # if true, failed check = failed execution

# --- SECTION 6: DEAD ENDS ---
dead_ends:
  - approach: "Description of an approach that was tried and abandoned"
    reason: "Why it didn't work"
    lesson: "What was learned"
    provenance:
      source_type: "conversation"
      source_ref: "Where this was tried and rejected"
      confidence: "high"

# --- SECTION 7: ADAPTATION NOTES ---
adaptation:
  flexibility: |
    Which parts of this methodology can be adjusted.
  fixed_elements: |
    Which parts must NOT be changed.
  target_requirements: |
    Minimum capabilities required of the target system.

# --- SECTION 8: POLICY ENVELOPE (NEW in v0.2) ---
policy:
  data_classification: "public | internal | confidential | restricted"
  redaction:
    status: "passed | failed | not_run"
    last_checked: "2026-03-09T10:00:00Z"
    checker: "mtp-lint"
    checker_version: "0.2.0"
    findings: []  # list of any flagged content, empty = clean
    report_hash: ""  # SHA-256 of full scan report
    evidence_ref: ""  # URI to full scan report artifact
  pii_scan:
    status: "passed | failed | not_run"
    method: "regex | ner | manual"
    findings: []
  secrets_scan:
    status: "passed | failed | not_run"
    patterns_checked: ["api_key", "token", "password", "connection_string", "bearer"]
    findings: []
  client_identifier_scan:
    status: "passed | failed | not_run"
    method: "dictionary | manual"
    findings: []
  regulated_content:
    status: "passed | failed | not_run"
    frameworks: ["GDPR", "HIPAA", "SOX"]  # which frameworks were checked
    findings: []
  approval:
    required: false
    approver: ""
    approved_at: ""
    signature: ""  # optional cryptographic signature
```

---

## 5. Provenance Model

### 5.1 Why Provenance Matters

Without provenance, an MTP Package is an assertion — "trust that this methodology is correct." With provenance, it is an auditable artifact — "here is where every element came from and why."

Provenance enables trust, reproducibility, and continuous improvement. When a step produces unexpected results, provenance allows tracing back to the original decision event. When a methodology needs updating, provenance identifies which source insights have changed.

### 5.2 Provenance Structure

Every step, edge case, and dead end in an MTP Package carries a `provenance` block. At minimum, `source_type`, `source_ref`, and `confidence` are required. `notes` is optional but recommended:

```yaml
provenance:
  source_type: "conversation | session | document | manual | composite"
  source_ref: "unique reference to source material"
  confidence: "high | medium | low"
  notes: "free-text explanation of derivation"
```

**source_type** identifies the kind of source:

| Type | Meaning |
|------|---------|
| `conversation` | Extracted from a specific AI conversation |
| `session` | Derived from a working session (may span multiple conversations) |
| `document` | Based on existing documentation, standard, or reference |
| `manual` | Authored directly by a human without AI assistance |
| `composite` | Synthesized from multiple sources |

**source_ref** is an opaque string whose format depends on `source_type`. For conversations, it should reference the conversation ID and message range. For documents, a URI or document hash. The format is intentionally not prescribed — different platforms have different referencing schemes.

**confidence** indicates how directly the element maps to its source:

| Level | Meaning |
|-------|---------|
| `high` | Direct extraction — the source explicitly contains this logic |
| `medium` | Interpreted — the logic was inferred from source material |
| `low` | Reconstructed — the source was ambiguous, this is best-effort |

### 5.3 Provenance for Incremental Extraction

When a methodology is built across multiple conversations or sessions, provenance tracks the assembly:

```yaml
provenance:
  source_type: "composite"
  source_ref: "session-2026-03-07, session-2026-03-08, session-2026-03-09"
  confidence: "medium"
  notes: "Step logic from session 03-07, edge case from 03-08, validation rule refined in 03-09"
```

---

## 6. Execution Semantics

### 6.1 Why Strict Semantics Matter

v0.1 relied on prompt-level instructions ("follow the steps, don't improvise"). This is insufficient for a control plane. MTP v0.2 defines precise execution states that a target system must report.

### 6.2 Step Execution States

Every step in an executed MTP Package must resolve to exactly one of these states:

| State | Code | Definition |
|-------|------|------------|
| **Success** | `success` | Step completed as specified. Validation passed. No deviations. |
| **Partial** | `partial` | Step completed but with reduced scope or quality. Validation passed on completed portion. The execution report MUST specify what was partial and why. |
| **Deviation** | `deviation` | Step completed but with a modification to the prescribed action. The execution report MUST specify the deviation, the reason, and whether validation still passed. |
| **Failure** | `failure` | Step could not be completed. The execution report MUST specify the failure reason and whether it is blocking (halts pipeline) or non-blocking. |
| **Skipped** | `skipped` | Step was not executed. Only permitted if: (a) `on_failure` of a dependency is `skip_with_flag`, or (b) adaptation notes explicitly allow it. The execution report MUST specify the reason. |
| **Escalated** | `escalated` | Step encountered a situation not covered by the methodology and requires human decision. Execution pauses at this step. |

### 6.3 Per-Step Execution Policy

Each step declares its `execution_semantics`:

```yaml
execution_semantics:
  on_success: "proceed"                    # always proceed
  on_failure: "halt | skip_with_flag | retry | escalate"
  on_deviation: "flag_and_proceed | halt | ask_human"
  timeout: "30s | 5m | none"              # optional time bound
  max_retries: 1                           # used when on_failure is "retry"
```

**on_failure** defines what happens when the step fails:
- `halt` — Stop execution. Report final state. This is the default.
- `skip_with_flag` — Skip this step. Downstream steps that depend on it are also skipped. Flag prominently in report.
- `retry` — Retry the step up to `max_retries` times. If all retries fail, apply `halt`. The `max_retries` field is required when `on_failure` is `retry` and must be >= 1.
- `escalate` — Pause execution and request human decision.

**on_deviation** defines what happens when the step completes but deviates from the prescribed action:
- `flag_and_proceed` — Continue execution. Record deviation in report. This is the default.
- `halt` — Treat deviation as failure. Stop execution.
- `ask_human` — Pause execution and present the deviation to a human for approval.

### 6.4 Pipeline-Level Execution Rules

Beyond per-step semantics, the execution pipeline follows these rules:

1. Steps are executed in order of `step` number, respecting `depends_on` constraints.
2. A step with unmet dependencies (because a dependency was `skipped` or `failure`) cannot execute and is marked `skipped` with reason "unmet_dependency".
3. If any step with a blocking `quality_check` fails validation, the entire execution is marked `failure` regardless of subsequent steps.
4. Dead ends are loaded into the target system's context BEFORE execution begins. The target system must not propose approaches listed in `dead_ends`.
5. Novel situations (not covered by `edge_cases`) trigger `escalated` state, not improvisation.

---

## 7. Execution Report

### 7.1 Report Structure

Every execution produces a standardized report:

```yaml
execution_report:
  mtp_package_id: <uuid>
  mtp_package_version: "1.0.0"
  mtp_spec_version: "0.2"
  target_platform: "azure-openai-gpt4o"
  executor: "mtp-run v1.0 | manual | custom"
  timestamp: "2026-03-09T14:00:00Z"
  duration_seconds: 42

  overall_status: "success | partial | deviation | failure | escalated"
  overall_confidence: "high | medium | low | manual_review"

  steps:
    - step: 1
      state: "success | partial | deviation | failure | skipped | escalated"
      validation_result: "pass | fail | not_applicable"
      duration_seconds: 5
      deviation:
        description: ""     # empty if no deviation
        reason: ""
        approved_by: ""     # human approver if escalated
      failure_reason: ""    # required when state = failure
      failure_blocking: true # required when state = failure
      skip_reason: ""       # required when state = skipped
      notes: ""

  edge_cases_encountered:
    - step: 3
      scenario: "Description of what happened"
      matched_edge_case: "edge_case_index or 'novel'"
      handling_applied: "Description of how it was handled"

  novel_situations:
    - step: 5
      description: "Situation not covered by the methodology"
      action_taken: "escalated | skipped"
      notes: ""

  dead_ends_prevented:
    - step: 2
      dead_end_ref: "dead_end_index"
      notes: "Target system considered this approach and was redirected by dead_end documentation"

  quality_checks:
    - check: "Description"
      result: "pass | fail"
      is_blocking: true
      notes: ""

  policy_compliance:
    data_leaked: false
    pii_detected: false
    notes: ""
```

Note: `improvised` is not a valid `action_taken` for novel situations. Per pipeline rule §6.4.5, novel situations MUST trigger `escalated` state. If a target system cannot escalate (no human-in-the-loop), the step is `skipped` with the novel situation documented. A target system that improvises on a novel situation is non-conformant.

### 7.2 Deriving overall_status

The `overall_status` field is deterministic, not subjective. It is derived from step states using these rules, applied in priority order:

1. If any step is `escalated` → overall_status is `escalated`.
2. If any step is `failure` and `failure_blocking: true` → overall_status is `failure`.
3. If any blocking `quality_check` failed → overall_status is `failure`.
4. If any step is `deviation` → overall_status is `deviation`.
5. If any step is `partial`, `skipped`, or `failure` with `failure_blocking: false` → overall_status is `partial`.
6. If all steps are `success` → overall_status is `success`.

### 7.3 Report Signing

Execution reports SHOULD be signed (hash or cryptographic signature) to prevent tampering. The signature covers the entire report content. This enables third-party verification that a reported execution actually occurred as described.

---

## 8. Drift Measurement

### 8.1 What Is Drift

Methodology drift is the measurable divergence between expected and actual outcomes when a methodology is transferred. MTP defines drift as a composite metric, not a single number.

### 8.2 Drift Score Components

All components are normalized to a 0.0–1.0 scale where **1.0 = perfect (no drift)** and **0.0 = total drift**. Components where a higher raw value indicates worse performance are inverted.

| Component | Raw Metric | Normalization | Polarity |
|-----------|-----------|---------------|----------|
| **Step Fidelity** | `success` states / total steps | Direct (higher is better) | Natural |
| **Deviation Rate** | `deviation` states / total steps | Inverted: `1.0 - raw` | Inverted |
| **Validation Pass Rate** | `pass` validations / total validations | Direct (higher is better) | Natural |
| **Output Quality** | passed quality checks / total checks | Direct (higher is better) | Natural |
| **Edge Case Coverage** | correctly handled / total encountered | Direct (higher is better) | Natural |
| **Novel Situation Rate** | `novel_situations` / total steps | Inverted: `1.0 - raw` | Inverted |
| **Dead End Avoidance** | 1.0 if no dead ends repeated, 0.0 if any repeated | Direct (binary) | Natural |

### 8.3 Composite Drift Score

The composite drift score is computed as follows:

**Step 1: Compute raw metrics** from the execution report.

**Step 2: Normalize** each metric to 0.0–1.0. For inverted-polarity metrics, apply `normalized = 1.0 - raw`.

**Step 3: Handle missing data.** If a component cannot be computed (e.g., zero edge cases encountered, so edge case coverage is undefined), exclude it from the weighted average and redistribute its weight proportionally among remaining components.

**Step 4: Compute weighted average.**

```
drift_score = Σ(weight_i × normalized_i) / Σ(weight_i)
```

where the sum is over all computable components.

Default weights:

```yaml
drift_weights:
  step_fidelity: 0.25
  deviation_rate: 0.15
  validation_pass_rate: 0.25
  output_quality: 0.20
  edge_case_coverage: 0.10
  novel_situation_rate: 0.03
  dead_end_avoidance: 0.02
```

Score range: 0.0 (total drift) to 1.0 (perfect transfer). Weights are configurable per methodology — a compliance-critical methodology may weight `validation_pass_rate` higher, while a creative methodology may weight `deviation_rate` lower. Weights MUST sum to 1.0 before redistribution.

**Example computation:**

An execution with 10 steps: 8 success, 1 deviation, 1 partial. 9/10 validations pass. All 3 quality checks pass. 2 edge cases encountered, both handled. No novel situations. No dead ends repeated.

```
step_fidelity     = 8/10           = 0.80
deviation_rate    = 1.0 - (1/10)   = 0.90  (inverted)
validation_pass   = 9/10           = 0.90
output_quality    = 3/3            = 1.00
edge_case_cov     = 2/2            = 1.00
novel_sit_rate    = 1.0 - (0/10)   = 1.00  (inverted)
dead_end_avoid    = 1.0            = 1.00

drift_score = (0.25×0.80 + 0.15×0.90 + 0.25×0.90 + 0.20×1.00
             + 0.10×1.00 + 0.03×1.00 + 0.02×1.00) / 1.0
            = 0.91
```

### 8.4 Drift Baselines

Drift is always relative. A drift score requires a baseline to compare against. MTP supports three baseline types:

**Reference run.** A known-good execution (the "golden run") stored alongside the MTP Package. Subsequent executions are compared to this baseline.

**Self-comparison.** Two executions of the same package on different platforms. The drift score measures platform-to-platform divergence.

**Temporal comparison.** The same package executed on the same platform at different times. Measures whether the platform's behavior has changed (e.g., model updates).

---

## 9. Redaction Discipline

### 9.1 Why "Data-Free" Must Be Auditable

A package that merely declares itself data-free provides no assurance. Enterprise adoption requires verifiable redaction — proof that no data, PII, client identifiers, or regulated content leaked from the source conversation into the methodology.

### 9.2 Redaction Checks

MTP defines five categories of redaction checks:

| Category | What It Catches | Method |
|----------|----------------|--------|
| **Literal data** | Specific values, records, identifiers from source data | Pattern matching against known data schemas |
| **PII** | Names, emails, phone numbers, addresses, national IDs | NER + regex patterns |
| **Secrets** | API keys, tokens, passwords, connection strings | Entropy analysis + known patterns |
| **Client identifiers** | Company names, project names, internal terminology | Dictionary matching against known client terms |
| **Regulated fragments** | Content subject to GDPR, HIPAA, SOX, or other frameworks | Framework-specific pattern libraries |

### 9.3 Redaction Report

Every validated MTP Package carries a `policy` section with machine-readable scan results:

```yaml
policy:
  redaction:
    status: "passed"
    last_checked: "2026-03-09T10:00:00Z"
    checker: "mtp-lint"
    checker_version: "0.2.0"
    findings: []
    report_hash: "sha256:a1b2c3..."
    evidence_ref: "reports/redaction-2026-03-09.json"
  pii_scan:
    status: "passed"
    method: "ner"
    findings: []
  secrets_scan:
    status: "passed"
    patterns_checked: ["api_key", "token", "password", "connection_string", "bearer"]
    findings: []
  client_identifier_scan:
    status: "passed"
    method: "dictionary"
    findings: []
  regulated_content:
    status: "passed"
    frameworks: ["GDPR"]
    findings: []
```

A package with `status: "failed"` or `status: "not_run"` in any policy category MUST NOT be executed in an enterprise context. Tooling SHOULD enforce this gate.

### 9.4 Redaction Is Not Anonymization

Redaction means the data was never included. Anonymization means the data was modified. MTP packages should be redacted, not anonymized — a methodology should never need specific data values to function. If it does, the extraction was incorrect.

---

## 10. Extraction Process

### 10.1 From Conversation to MTP Package

Extraction transforms an organic AI-human collaboration into a structured MTP Package. It follows five phases:

**Phase 1 — Intent Recovery.** Analyze the conversation and identify: What was the human trying to achieve? What domain knowledge shaped the approach? What constraints (business, regulatory, technical) influenced decisions?

**Phase 2 — Decision Archaeology.** For each methodological choice made during the conversation: What alternatives were considered? Why was this approach chosen? What would break if this decision were changed? Record provenance for each decision.

**Phase 3 — Step Formalization.** Convert the organic, iterative conversation into a linear sequence of reproducible steps. Identify dependencies between steps. Separate the methodology from the specific data that was used. Assign execution semantics to each step.

**Phase 4 — Edge Case and Dead End Capture.** Identify all edge cases that were discovered, discussed, or handled during the conversation. Capture approaches that were tried and abandoned. Record provenance for each.

**Phase 5 — Redaction Verification.** Scan the assembled package for any data, PII, secrets, or regulated content that leaked from the source conversation. Remove any findings. Produce a redaction report.

### 10.2 Extraction Prompt Template

```
You are an MTP (Methodology Transfer Protocol) extractor. Your task is
to analyze the following conversation and extract a structured,
reproducible methodology that can be executed by a different AI system
on different data.

MTP v0.2 requirements:

1. INTENT: Capture the goal, context, success criteria, and non-goals.

2. PROVENANCE: For each step, edge case, and dead end, record:
   - source_type: conversation
   - source_ref: message numbers or ranges that produced this element
   - confidence: high/medium/low based on how directly it maps
   - notes: optional explanation when derivation needs clarification

3. EXECUTION SEMANTICS: For each step, define:
   - on_failure: halt | skip_with_flag | retry | escalate
   - on_deviation: flag_and_proceed | halt | ask_human
   - if on_failure is retry, include max_retries >= 1
   Include these based on the criticality evident in the conversation.

4. DECISION POINTS: Every if/then/else with rationale.

5. VALIDATION: Every step must have a boolean-testable validation rule.

6. DEAD ENDS: Every approach that was tried and abandoned, with reason.

7. REDACTION: The package MUST contain ZERO data from the conversation.
   No specific values, no names, no identifiers, no example records.
   Only the abstract methodology.

Output the methodology as a valid MTP v0.2 YAML package.

<conversation>
{paste conversation here}
</conversation>
```

### 10.3 Incremental Extraction

For long-running projects across multiple sessions:

1. Extract an MTP Package from each session with provenance tracking.
2. Merge packages using the `package.version` field for ordering.
3. Resolve conflicts by preferring the most recent decision rationale.
4. Mark superseded steps as dead_ends with reason "superseded by v{x}" and provenance pointing to the decision that superseded them.
5. Re-run redaction verification on the merged package.

---

## 11. Application Process

### 11.1 Target System Prompt Template

```
You are executing a methodology defined in the attached MTP Package
(v0.2). This is a controlled execution — not a creative task.

EXECUTION RULES:

1. Follow steps in order, respecting depends_on constraints.
2. For each step, report one of these states:
   - success: completed as specified, validation passed
   - partial: completed with reduced scope (explain what and why)
   - deviation: completed with modification (explain what and why)
   - failure: could not complete (explain why)
   - skipped: not executed (only if dependency failed or adaptation allows)
   - escalated: situation not covered, needs human decision

3. On failure, follow the step's execution_semantics.on_failure policy.
4. On deviation, follow the step's execution_semantics.on_deviation policy.
5. Do NOT improvise. If a situation is not covered by edge_cases, STOP
   and report it as a novel situation.
6. Read the dead_ends section BEFORE starting. Do not repeat any
   approach listed there.
7. Validate each step using the specified validation rule.
   Report pass or fail.
8. Produce a complete execution report in MTP report format.

Apply this methodology to the following data:
{data}

MTP Package:
{mtp_yaml}
```

---

## 12. Conformance

### 12.1 What Is MTP Conformance

MTP conformance means a platform or tool correctly implements the MTP lifecycle for its role (extractor, validator, executor, or reporter). Conformance is testable — not self-declared.

### 12.2 Conformance Levels

| Level | Name | Requirements |
|-------|------|-------------|
| **L1** | Package Conformance | Produces valid MTP v0.2 YAML that passes schema validation |
| **L2** | Execution Conformance | Executes MTP packages with correct state reporting (all 6 states), respects execution_semantics, produces valid execution reports |
| **L3** | Full Conformance | L1 + L2 + redaction validation + drift measurement + provenance tracking |

### 12.3 Conformance Test Fixtures

MTP provides a conformance test suite consisting of:

**Reference packages.** A set of MTP packages with known-correct structure, covering all sections, edge cases, and execution semantics variations.

**Execution scenarios.** A set of input data + MTP package combinations with expected execution report outcomes. A conformant executor must produce reports matching the expected states.

**Redaction test cases.** Packages intentionally containing data leaks. A conformant validator must detect and flag them.

**Drift test cases.** Two execution reports from the same package with known divergence. A conformant drift engine must compute the correct drift score.

The reference conformance runner lives in `tools/mtp-conformance/` and executes fixture manifests stored under `conformance/fixtures/`.

---

## 13. Benchmark Framework

### 13.1 Purpose

Benchmarks demonstrate that MTP delivers measurable value. They are not part of the spec — they are evaluation criteria that the community and adopters use to validate MTP's claims.

### 13.2 Benchmark Dimensions

**Transfer fidelity.** Same methodology, two platforms. Measure drift score. Compare with manual transfer (no MTP) as baseline.

**Temporal stability.** Same methodology, same platform, 30/60/90 days apart. Measure drift score over time.

**Transfer efficiency.** Time to transfer methodology with MTP vs. manual re-explanation. Measure human time spent.

**Redaction reliability.** Percentage of data leaks caught by MTP validation vs. unstructured transfer.

**Cross-platform coverage.** Number of platforms on which a single MTP package executes with drift score > 0.8.

### 13.3 Benchmark Protocol

A valid benchmark must:

1. Use a publicly available or reproducible methodology (not proprietary).
2. Test on at least two distinct platforms.
3. Include a baseline (manual transfer without MTP).
4. Report all drift score components, not just the composite.
5. Be reproducible — publish the MTP package, test data (synthetic), and execution reports.

---

## 14. Roadmap

| Version | Focus | Key Deliverables |
|---------|-------|-----------------|
| v0.1 | ✅ Foundation | YAML format, manual extraction/application, JSON Schema |
| v0.2 | ✅ Control Plane | Lifecycle (Extract→Validate→Execute→Report→Compare→Version), provenance, execution semantics, redaction discipline, drift measurement, conformance levels, benchmark framework |
| v0.3 | ✅ Tooling | `mtp-lint` CLI: schema validator, redaction scanner (PII, secrets, entropy, client IDs, regulated content, literal data), completeness scorer, enterprise policy gate |
| v0.4 | ✅ Runtime | `mtp-run` reference runtime CLI: step-by-step execution engine, LLM adapters (mock, Anthropic, OpenAI, Azure OpenAI), execution report generation with drift scoring, cross-report drift comparison |
| v0.5 | ✅ Released | Formal conformance suite, fixture packs, release-gate runner, CI conformance reporting |
| v0.6 | ✅ Released | Registry specification, package signatures, approval workflows |
| v0.7 | ✅ Released | Extraction tooling, benchmark suites/results, adapter certification artifacts, stronger signing profiles |
| v1.0 | ✅ Current | Production toolchain `1.0.0`, compatibility contract, provider-certified benchmark matrix, local-KMS manifest, enterprise reference architecture |

The `v0.6` trust layer is specified separately in [MTP-REGISTRY-v0.6.md](MTP-REGISTRY-v0.6.md) so that registry artifacts evolve independently from the stable `v0.2` package and execution-report schemas. `v1.0` adds release-level governance artifacts in [MTP-COMPATIBILITY-v1.0.md](MTP-COMPATIBILITY-v1.0.md) without changing the core package/report contract.

---

## 15. Contributing

MTP is an open specification. Contributions, feedback, and real-world validation are welcome.

**GitHub:** https://github.com/lubor-fedak/mtp-spec

We especially welcome:

- **Critical feedback** on execution semantics and drift measurement — are the definitions precise enough?
- **Real-world extraction attempts** — try extracting an MTP package from your workflow and report what's missing
- **Platform-specific insights** — how does execution semantics map to your AI platform's behavior?
- **Enterprise perspective** — does the policy envelope cover your compliance requirements?

---

## 16. License

Apache 2.0 — see [LICENSE](../LICENSE).

---

## Appendix A: Changes from v0.1

| Area | v0.1 | v0.2 |
|------|------|------|
| Identity | "Structured YAML format" | "Methodology control plane" |
| Lifecycle | Extract + Apply | Extract → Validate → Execute → Report → Compare → Version |
| Provenance | Not present | Per-step source tracking with confidence levels |
| Execution | Prompt-based instructions | Strict state machine (6 states, per-step policies) |
| Redaction | "Data-free" declaration | Auditable policy envelope with scan reports |
| Drift | Not measured | Composite drift score with 7 components |
| Conformance | Not defined | Three conformance levels with test fixtures |
| Benchmarks | Not defined | Framework for measuring transfer fidelity, efficiency, stability |
