# MTP — Methodology Transfer Protocol

## Specification Draft v0.1

**Author:** Lubor Fedák  
**Date:** 2026-03-09  
**Status:** Draft  
**License:** TBD (recommended: Apache 2.0 or MIT)

---

## 1. Problem Statement

### 1.1 The Methodology Gap

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

None of these solutions extract a **structured, reproducible methodology** from an organic AI-human collaboration session and package it for execution in a different AI system.

### 1.3 Why This Problem Will Grow

As AI agents become autonomous and operate across systems, the need to transfer not just data or context, but **working methodology** — the logic of how to approach a problem — will scale from thousands of human workers to millions of AI agents. MTP is designed for both human-to-AI and future AI-to-AI methodology transfer.

---

## 2. Core Concepts

### 2.1 Definitions

**Methodology.** A structured approach to solving a specific type of problem, consisting of intent, decision logic, transformation steps, validation rules, and constraints. A methodology is independent of specific data.

**MTP Package.** A self-contained, portable file that encodes a methodology in a structured format that any sufficiently capable LLM can interpret and execute.

**Source System.** The AI platform where the methodology was originally developed through human-AI collaboration.

**Target System.** The AI platform where the methodology will be applied to new data.

**Extraction.** The process of distilling a methodology from a conversation or session into an MTP Package.

**Application.** The process of a target system interpreting an MTP Package and executing the encoded methodology on provided data.

### 2.2 Design Principles

1. **Data-free.** An MTP Package never contains actual data. It contains only the methodology — the "recipe without ingredients."
2. **Platform-agnostic.** The format must be interpretable by any LLM-based system without platform-specific dependencies.
3. **Intent-preserving.** The package must capture not just *what* to do, but *why* — the reasoning behind methodological choices.
4. **Human-readable.** An MTP Package must be reviewable by a human before application, serving as both documentation and executable specification.
5. **Incrementally buildable.** A methodology can be extracted from a single conversation or assembled from multiple sessions over time.
6. **Versionable.** Methodologies evolve. The format must support versioning and change tracking.

---

## 3. MTP Package Format

An MTP Package is a structured YAML document with the following sections:

```yaml
mtp_version: "0.1"
package:
  id: <uuid>
  name: "Human-readable methodology name"
  version: "1.0.0"
  created: "2026-03-09T10:00:00Z"
  updated: "2026-03-09T10:00:00Z"
  author: "Name or identifier"
  source_platform: "claude-4.6"  # informational only, not a dependency
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
      decision_points:
        - condition: "If [condition]"
          then: "Do [action]"
          rationale: "Why this branch exists"
      validation: |
        How to verify this step was executed correctly.
      
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

# --- SECTION 6: DEAD ENDS (OPTIONAL) ---
dead_ends:
  - approach: "Description of an approach that was tried and abandoned"
    reason: "Why it didn't work"
    lesson: "What was learned — prevents target system from repeating mistakes"

# --- SECTION 7: ADAPTATION NOTES ---
adaptation:
  flexibility: |
    Which parts of this methodology can be adjusted by the target
    system based on its capabilities and data specifics.
  fixed_elements: |
    Which parts must NOT be changed — they encode critical
    decisions that were made for specific reasons.
  target_requirements: |
    Minimum capabilities required of the target system
    (e.g., "must support structured output", "must handle CSV parsing").
```

---

## 4. Extraction Process

### 4.1 From Conversation to MTP Package

Extraction can be performed by the source AI system or by a dedicated extraction tool. The extraction prompt follows this structure:

**Phase 1 — Intent Recovery**
Analyze the conversation and identify: What was the human trying to achieve? What domain knowledge shaped the approach? What constraints (business, regulatory, technical) influenced decisions?

**Phase 2 — Decision Archaeology**
For each methodological choice made during the conversation: What alternatives were considered? Why was this approach chosen? What would break if this decision were changed?

**Phase 3 — Step Formalization**
Convert the organic, iterative conversation into a linear sequence of reproducible steps. Identify dependencies between steps. Separate the methodology from the specific data that was used.

**Phase 4 — Edge Case Capture**
Identify all edge cases that were discovered, discussed, or handled during the conversation. Capture the handling logic and the reasoning behind it.

**Phase 5 — Dead End Preservation**
Capture approaches that were tried and abandoned. This is critical — it prevents the target system from repeating failed approaches.

### 4.2 Extraction Prompt Template

```
You are an MTP (Methodology Transfer Protocol) extractor. Your task is
to analyze the following conversation and extract a structured,
reproducible methodology that can be applied by a different AI system
to different data.

Focus on:
1. The INTENT behind the work — not just what was done, but why
2. Every DECISION POINT — what was chosen and what was rejected
3. VALIDATION RULES — how to verify each step produced correct results
4. EDGE CASES — unusual situations that were handled
5. DEAD ENDS — approaches that were tried and abandoned, and why
6. DATA INDEPENDENCE — separate the method from the specific data used

Do NOT include any actual data from the conversation.
Output the methodology as a valid MTP YAML package.

<conversation>
{paste conversation here}
</conversation>
```

### 4.3 Incremental Extraction

For long-running projects across multiple sessions:

1. Extract an MTP Package from each session
2. Merge packages using the `package.version` field for ordering
3. Resolve conflicts by preferring the most recent decision rationale
4. Mark superseded steps as dead_ends with reason "superseded by v{x}"

---

## 5. Application Process

### 5.1 Target System Prompt Template

```
You are executing a methodology defined in the attached MTP Package.

Rules:
1. Follow the methodology steps in order, respecting dependencies
2. Do NOT skip steps or reorder them unless the adaptation section
   explicitly permits it
3. If you encounter a situation not covered by the edge cases,
   STOP and report it — do not improvise
4. Validate each step using the specified validation rules
5. If a validation fails, report it before proceeding
6. Refer to the dead_ends section before suggesting alternatives —
   do not repeat approaches that were already tried and failed

Apply this methodology to the following data:
{data}

MTP Package:
{mtp_yaml}
```

### 5.2 Execution Report

After application, the target system should produce an execution report:

```yaml
execution:
  mtp_package_id: <uuid>
  mtp_version: "1.0.0"
  target_platform: "azure-openai-gpt4"
  timestamp: "2026-03-09T14:00:00Z"
  
  steps_executed:
    - step: 1
      status: "success | partial | failed | skipped"
      validation_result: "pass | fail"
      notes: "Any deviations or observations"
      
  edge_cases_encountered:
    - scenario: "Description"
      handled_by: "Reference to edge_case in MTP or 'novel'"
      
  deviations:
    - step: 2
      deviation: "What was done differently"
      reason: "Why"
      
  output_quality:
    checks_passed: 5
    checks_failed: 0
    overall: "pass | partial | fail"
```

---

## 6. Example: Financial Data Classification

### 6.1 Scenario

A data analyst uses Claude to develop a methodology for classifying expense transactions into budget categories. The methodology involves fuzzy matching on vendor names, amount-based heuristics, and exception handling for ambiguous entries. The analyst then needs to apply this same methodology in enterprise Azure OpenAI, which has access to the actual financial data.

### 6.2 Abbreviated MTP Package

```yaml
mtp_version: "0.1"
package:
  id: "f47ac10b-58cc-4372-a567-0e02b2c3d479"
  name: "Expense Transaction Budget Classification"
  version: "1.0.0"
  created: "2026-03-09"
  author: "analyst@company.com"
  tags: ["finance", "classification", "expense-management"]

intent:
  goal: |
    Classify raw expense transactions into standardized budget
    categories with >95% accuracy, flagging ambiguous cases
    for human review rather than guessing.
  context: |
    Company uses 12 budget categories defined in the FY2026
    budget framework. Vendor names in raw data are inconsistent
    (abbreviations, typos, multiple formats for same vendor).
  success_criteria:
    - "95%+ transactions classified without human intervention"
    - "0% misclassification of transactions >10,000 EUR"
    - "All ambiguous cases flagged, never silently classified"
  non_goals:
    - "This methodology does not handle currency conversion"
    - "This methodology does not validate transaction amounts"

methodology:
  approach: |
    Three-pass classification: (1) exact vendor match against
    known vendor-category mapping, (2) fuzzy match for unknown
    vendors using Levenshtein distance, (3) amount-based
    heuristics for remaining unmatched transactions.
    
    This three-pass approach was chosen over ML classification
    because the dataset is too small for reliable training
    and the client requires explainable decisions.

  steps:
    - step: 1
      name: "Vendor Name Normalization"
      action: |
        Normalize all vendor names: uppercase, remove special
        characters, collapse whitespace, strip common suffixes
        (GmbH, s.r.o., SAS, Ltd, Inc).
      rationale: |
        Raw vendor names contain inconsistencies that prevent
        exact matching. Normalization before matching improves
        hit rate from ~60% to ~85%.
      validation: |
        Verify no empty vendor names after normalization.
        Verify character set is alphanumeric + space only.

    - step: 2
      name: "Exact Match Classification"
      action: |
        Match normalized vendor names against the known
        vendor-category mapping table. Mark matched
        transactions as "classified:exact".
      depends_on: [1]
      validation: |
        Count of classified:exact should be 60-85% of total.
        If below 50%, normalization may have issues.

    - step: 3
      name: "Fuzzy Match Classification"
      action: |
        For unmatched transactions, compute Levenshtein distance
        against all known vendors. Accept matches with
        distance <= 2 AND similarity ratio >= 0.85.
        Mark as "classified:fuzzy".
      depends_on: [2]
      decision_points:
        - condition: "Multiple fuzzy matches with equal scores"
          then: "Flag as ambiguous, do not classify"
          rationale: "False positive classification is worse than no classification"
      validation: |
        Fuzzy matches should add 10-20% coverage.
        Review a sample of fuzzy matches for false positives.

edge_cases:
  - scenario: "Vendor name is a single character or number after normalization"
    handling: "Flag as ambiguous, do not attempt matching"
    severity: "warning"
  - scenario: "Transaction amount is negative (refund/credit)"
    handling: "Classify using same methodology but mark output with refund flag"
    severity: "info"

dead_ends:
  - approach: "Attempted keyword-based classification using transaction description field"
    reason: "Description field is empty in 40% of transactions and unreliable in remaining 60%"
    lesson: "Do not use description field as primary classifier"
```

---

## 7. Roadmap

### v0.1 (Current)
- YAML-based package format specification
- Manual extraction process with prompt templates
- Manual application with prompt templates

### v0.2 (Planned)
- JSON Schema for MTP Package validation
- Extraction CLI tool (Python)
- Package diff/merge tooling for multi-session methodologies

### v0.3 (Future)
- Automated extraction from conversation exports (Claude, ChatGPT)
- MTP registry for sharing methodologies within organizations
- Execution report aggregation and methodology drift detection

### v1.0 (Vision)
- Native integration with AI platforms
- Real-time extraction during conversation
- Agent-to-agent methodology transfer via MTP over A2A/MCP

---

## 8. Contributing

MTP is an open specification. Contributions, feedback, and real-world validation are welcome.

- **GitHub:** [TBD — github.com/codemoravia/mtp-spec]
- **Issues:** Report problems or suggest improvements
- **Examples:** Share your MTP Packages to build a community library

---

## 9. License

TBD — Recommended: Apache 2.0 for specification, MIT for reference implementations.
