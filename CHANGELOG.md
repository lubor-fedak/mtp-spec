# Changelog

All notable changes to the MTP specification are documented in this file.

## [0.4] — 2026-03-09

### First runtime deliverable: mtp-run
- New Python CLI tool in `tools/mtp-run/`, installable via `pip install -e .`
- Three commands: `exec` (execute package), `adapters` (list adapters), `drift` (compare reports)

### Execution engine
- Step-by-step execution with dependency chain resolution
- Full execution semantics: on_failure (halt/skip_with_flag/retry/escalate), on_deviation (flag_and_proceed/halt/ask_human)
- Retry support with configurable max_retries
- Pipeline halt propagation: downstream steps auto-skipped on halt
- Unmet dependency detection and skip with reason
- Progress callbacks for CLI output

### LLM adapters
- Mock adapter: deterministic responses for testing/CI, controllable via FORCE_FAIL/FORCE_DEVIATE/FORCE_ESCALATE/FORCE_PARTIAL markers
- Anthropic adapter: Claude API (Messages API), configurable model
- OpenAI adapter: OpenAI + Azure OpenAI (Chat Completions API), configurable model and endpoint
- All adapters: structured YAML response parsing with heuristic fallback

### Execution report generation
- Automated overall_status derivation per spec §7.2
- Drift score computation per spec §8.3 with polarity normalization and missing component redistribution
- Report hash for integrity verification
- Output as YAML or JSON

### Drift comparison
- Cross-report step-by-step state comparison
- State agreement metric
- Platform and temporal comparison support

### Schema fix
- Execution report schema: allow null for validation_pass_rate, output_quality, edge_case_coverage (components that may be uncomputable)

### Test data
- Added examples/test-data-churn.csv: sample data for the churn scoring package

## [0.3.2] — 2026-03-09

### mtp-lint hardening
- Replaced string-based version checks with numeric version comparison, preventing future bugs such as `"0.10"` being treated as older than `"0.2"`.
- Added explicit top-level type validation for loaded artifacts. Non-object YAML/JSON inputs now fail cleanly with input error instead of falling through unpredictably.
- Aligned tool package metadata and generated reports to `mtp-lint` version `0.3.2`.

## [0.3] — 2026-03-09

### First tooling deliverable: mtp-lint
- New Python CLI tool in `tools/mtp-lint/`, installable via `pip install -e .`
- Four commands: `check` (full pipeline), `validate` (schema only), `redact` (scan only), `score` (completeness only)
- Machine-readable JSON output with report hash, or human-readable text

### Schema validation
- Validates MTP packages against v0.1 or v0.2 JSON Schemas (auto-detected)
- Validates execution reports against v0.2 execution report schema
- Reports all errors with JSON paths

### Redaction scanner
- PII detection: email, phone, IP address, Czech birth number, national ID, credit card, IBAN, URL parameters
- Secret detection: API keys, bearer tokens, passwords, connection strings, AWS keys, GitHub tokens, private keys, JWTs, Slack tokens
- High-entropy string detection via Shannon entropy analysis
- Client identifier scanning via user-provided dictionary (`--client-dict`)
- Regulated content keyword scanning: health data, financial accounts, biometric data, minor data indicators
- Literal data detection: CSV rows, JSON fragments, SQL VALUES in methodology text
- Scans ALL content-bearing fields including package.author and provenance.source_ref (not skipped — these are common leak vectors)

### Completeness scoring
- 72-check scoring engine across 11 areas: intent, input, methodology, steps, edge_cases, dead_ends, output, adaptation, policy
- v0.2-aware: checks provenance, execution_semantics, policy scan status
- Composite 0–100% score with rating (excellent/good/fair/poor)
- Correct area aggregation for steps, edge_cases, dead_ends

### Policy gate
- Enterprise execution gate: all 5 scan categories must be run and passed
- data_classification is required for gate pass
- Approval requirement enforcement when approval.required is true
- Policy gate failure = overall FAIL (exit code 1), not warning

### Artifact type safety
- `score` and `check` commands validate artifact type before processing
- Execution reports are correctly rejected by score command (exit 2)

## [0.2.1] — 2026-03-09

### Schema/spec alignment fixes
- Standardized `on_failure` semantics on `retry` across the spec, examples, and package schema. Removed stale `retry_once` references from normative guidance.
- Added strict conditional validation for `max_retries`: when `on_failure` is `retry`, `max_retries` is required and must be >= 1.
- Tightened provenance requirements in the package schema: `source_ref` and `confidence` are now required inside provenance blocks; `edge_cases` and `dead_ends` now require provenance.

### Execution report hardening
- Added `failure_blocking` to step reports so overall execution status can be derived from report data rather than external package context.
- Added conditional validation in the execution report schema:
  - `failure` steps require `failure_reason` and `failure_blocking`
  - `skipped` steps require `skip_reason`
  - `deviation` steps require structured deviation details
- Added report-level derivation checks for `overall_status` based on escalations, blocking failures, blocking quality check failures, deviations, and partial/skipped outcomes.

### Release metadata
- Marked the repository state as patch release **0.2.1** of the normative **v0.2** specification.
- Added a reference v0.2 execution report example to complement the v0.2 package example.

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
- Per-step execution policies: `on_failure` (halt/skip_with_flag/retry/escalate), `on_deviation` (flag_and_proceed/halt/ask_human).
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
