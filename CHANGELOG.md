# Changelog

All notable changes to the MTP specification are documented in this file.

## [0.2] — 2026-03-09

### Positioning shift
- MTP is no longer described as a "structured YAML format" but as a **methodology control plane** — the missing layer between methodology authoring and methodology execution across AI boundaries.
- New positioning line: "MCP connects models to tools. MTP connects methodology authoring to methodology execution."
- Added stack diagram showing MTP's position between the application layer and protocol layer (MCP, A2A).

### Lifecycle (NEW)
- Defined the six-phase MTP lifecycle: **Extract → Validate → Execute → Report → Compare → Version**.
- MTP is no longer a file format with prompt templates — it is a controlled execution loop.

### Provenance (NEW)
- Every step, edge case, and dead end now carries a `provenance` block with `source_type`, `source_ref`, `confidence`, and `notes`.
- Five source types defined: conversation, session, document, manual, composite.
- Three confidence levels: high, medium, low — based on directness of mapping from source.
- Provenance model for incremental extraction across multiple sessions.

### Execution Semantics (NEW)
- Defined six strict execution states: `success`, `partial`, `deviation`, `failure`, `skipped`, `escalated`.
- Each state has a precise definition and mandatory reporting requirements.
- Per-step execution policies: `on_failure` (halt/skip_with_flag/retry_once/escalate), `on_deviation` (flag_and_proceed/halt/ask_human).
- Pipeline-level execution rules: dependency handling, blocking quality checks, dead end pre-loading, novel situation escalation.

### Redaction Discipline (NEW)
- "Data-free" is no longer a declaration — it is an auditable property.
- Defined five redaction check categories: literal data, PII, secrets, client identifiers, regulated fragments.
- MTP Package now includes a `policy` section with machine-readable scan results for each category.
- Packages with failed or unrun policy checks must not be executed in enterprise contexts.
- Clarified distinction: redaction (data never included) vs. anonymization (data modified).

### Drift Measurement (NEW)
- Defined methodology drift as a composite metric with seven components: step fidelity, deviation rate, validation pass rate, output quality, edge case coverage, novel situation rate, dead end avoidance.
- Composite drift score: weighted average, range 0.0–1.0, configurable weights.
- Three baseline types: reference run, self-comparison (cross-platform), temporal comparison.

### Execution Report (EXPANDED)
- Report now includes: overall status, per-step states with deviation details, edge cases encountered, novel situations, dead ends prevented, quality check results, policy compliance.
- Report signing recommended for tamper prevention.

### Conformance (NEW)
- Three conformance levels: L1 (package), L2 (execution), L3 (full — includes redaction + drift + provenance).
- Conformance test fixture types defined: reference packages, execution scenarios, redaction test cases, drift test cases.

### Benchmark Framework (NEW)
- Five benchmark dimensions: transfer fidelity, temporal stability, transfer efficiency, redaction reliability, cross-platform coverage.
- Benchmark protocol requirements: reproducibility, multi-platform, baseline inclusion, full drift component reporting.

### Roadmap (REVISED)
- Reordered from feature-based to capability-based progression:
  - v0.3: validator + linter
  - v0.4: runtime CLI + adapters
  - v0.5: drift scoring + conformance suite
  - v0.6: registry + signatures
  - v1.0: production adapters + benchmarks

### Format Changes
- `mtp_version` updated from "0.1" to "0.2".
- Steps now include `provenance` and `execution_semantics` blocks.
- New top-level `policy` section for redaction/PII/secrets/regulated content scans.
- Output quality checks now include `is_blocking` flag.
- Dead ends and edge cases now include `provenance` blocks.

## [0.1] — 2026-03-09

### Initial release
- Problem statement: methodology gap, compliance-driven fragmentation, methodology drift.
- Comparison with existing solutions (CTP, Plurality, Copilot Skills).
- YAML-based MTP Package format with 7 sections: intent, input, methodology, edge cases, output, dead ends, adaptation.
- Manual extraction process with 5-phase prompt template.
- Manual application process with prompt template.
- Execution report structure.
- JSON Schema for package validation.
- Example: Financial Data Classification.
- Example: Valuation Report Extraction.
- Apache 2.0 license.
