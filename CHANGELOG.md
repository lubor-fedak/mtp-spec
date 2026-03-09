# Changelog

All notable changes to the MTP specification are documented in this file.

## [1.0.0] — 2026-03-09

### Production release surface
- Added `tools/mtp-release/` for generating and validating provider matrices and compatibility contracts
- Added `spec/MTP-COMPATIBILITY-v1.0.md`
- Added `docs/enterprise-reference-architecture-v1.0.md`
- Added release examples under `examples/releases/`

### Trust hardening
- Added `mtp-key-provider-manifest-v1.0.json`
- Added `local-kms` key-provider manifest workflow to `mtp-registry`
- Added reference key-provider manifest under `examples/registry/`

### Release artifacts
- Added `mtp-provider-matrix-v1.0.json`
- Added `mtp-compatibility-contract-v1.0.json`
- Published reference `v1.0` provider matrix, compatibility contract, and conformance snapshot

### Toolchain stabilization
- Aligned all CLI tool package versions to `1.0.0`
- Normalized generated executor/checker metadata to the `1.0.0` toolchain
- CI now validates `mtp-release` and the `v1.0` release artifacts
- README roadmap now marks `v1.0` as the current production release

## [0.7.0] — 2026-03-09

### Extraction and benchmark layer
- Added `tools/mtp-extract/` with draft extraction, provenance mapping, merge workflow, and policy precheck
- Added reference conversation transcript and extracted draft under `examples/conversations/`
- Added `tools/mtp-benchmark/` with benchmark suites, benchmark results, and adapter certification artifacts
- Added reference benchmark suite/result/certification under `examples/benchmarks/`

### Schemas
- Added `mtp-benchmark-suite-v0.7.json`
- Added `mtp-benchmark-result-v0.7.json`
- Added `mtp-adapter-certification-v0.7.json`

### Trust hardening
- Extended `mtp-registry` signature envelopes to support `ed25519` in addition to `hmac-sha256`
- Added CLI support for `--key-file` verification/signing flows
- Added Ed25519 workflow and CLI tests

### Documentation and CI
- README now documents extraction-first quick start and benchmark tooling
- CI now runs `mtp-extract` and `mtp-benchmark` tests plus reference example validation
- Roadmap updated so `v0.7` is the current release layer before `v1.0`

## [0.6.0] — 2026-03-09

### Registry extension
- Added new registry extension spec at `spec/MTP-REGISTRY-v0.6.md`
- Added detached trust artifacts instead of mutating the stable `v0.2` package format
- Defined local registry manifest, signature envelope, approval record, and registry entry models

### New tooling: mtp-registry
- Added `tools/mtp-registry/` Python CLI
- Commands: `init`, `sign`, `verify`, `approve`, `publish`, `check-entry`
- Reference signature profile: `hmac-sha256` over canonical `json-sorted-v1` artifact content

### Schemas
- Added `mtp-registry-manifest-v0.6.json`
- Added `mtp-signature-envelope-v0.6.json`
- Added `mtp-approval-record-v0.6.json`
- Added `mtp-registry-entry-v0.6.json`

### Examples and workflow
- Added reference registry example under `examples/registry/`
- Local publication flow now supports: validate → sign → approve → publish → verify

### Tests and CI
- Added `mtp-registry` CLI tests
- CI now runs `mtp-registry` tests and example verification

## [0.5.0] — 2026-03-09

### Formal conformance suite
- Added new `tools/mtp-conformance/` Python CLI with `mtp-conformance run --level l1|l2|l3|all`
- Added cumulative conformance execution model with stable summary hashing for release-gate use
- Added direct orchestration of `mtp-lint` and `mtp-run` capabilities from a single conformance entrypoint

### Fixture packs
- Added repository-level `conformance/fixtures/` corpus
- L1 fixtures: schema-valid and schema-invalid package cases
- L2 fixtures: deterministic execution coverage for all six states (`success`, `partial`, `deviation`, `failure`, `skipped`, `escalated`)
- L3 fixtures: redaction leak corpus, provenance presence checks, self-score drift references, cross-report drift comparison

### Tests and CI
- Added `mtp-conformance` CLI tests
- CI now runs `mtp-conformance` unit tests and release-gate conformance levels `l1`, `l2`, and `l3`

### Documentation
- README now documents `mtp-conformance` as the `v0.5` deliverable
- Conformance fixtures documentation updated from planned scaffold to implemented corpus
- Spec roadmap updated so `v0.5` reflects the shipped conformance suite

## [0.4.1] — 2026-03-09

### Drift engine completion
- `drift.py` now implements full weighted drift scoring per spec §8.3: 7 components, polarity normalization (inverted metrics use 1.0 - raw), missing data redistribution, composite weighted average
- New `mtp-run score` command: compute drift score for a single execution report with per-component breakdown
- CLI drift command now shows weighted drift scores alongside step-state agreement

### Runtime hardening
- Adapter registry now reports real runtime readiness for `mock`, `anthropic`, `openai`, and `azure-openai`
- Runtime exceptions are captured as step failures so execution semantics still apply
- End-to-end runtime paths now produce schema-valid execution reports for mock and real-adapter flows

### Verified
- `mtp-run exec` with mock → all SUCCESS, drift 1.0, report schema-valid
- `mtp-run score` on hand-written report → 0.92 (step 3 deviation correctly scored)
- `mtp-run score` on mock report → 1.0 (edge_case_coverage excluded, weights redistributed)
- `mtp-run drift` mock vs azure → 80% state agreement, self-scores 1.0 vs 0.92, cross-report drift 0.9111
- `mtp-run adapters` → mock READY, configured adapters surfaced with real availability states

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
- Weighted cross-report drift scoring based on spec §8.3 component deltas
- Baseline self-score + candidate self-score + cross-report methodology preservation score
- Step agreement metric and per-step difference reporting

### Adapter/runtime hardening
- Real Anthropic and OpenAI adapters are surfaced as configured runtime adapters, not planned placeholders.
- Dynamic adapter status reporting distinguishes `ready`, `not_configured`, and `missing_dependency`.
- Runtime exceptions from adapters are captured as step failures so execution semantics and retries can still apply.
- Edge cases, novel situations, and consciously avoided dead ends are now aggregated into execution reports.

### End-to-end harness
- Added `mtp-run e2e` to execute the same package via `mock` and one configured real adapter, store both reports, and emit comparison JSON.

### Schema fix
- Execution report schema: allow null for validation_pass_rate, output_quality, edge_case_coverage (components that may be uncomputable)

### Test data
- Added examples/test-data-churn.csv: sample data for the churn scoring package
- Added examples/churn-risk-scoring-mock-execution-report-v0.2.yaml: static mock execution report for drift demos and schema validation examples.

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
  - v0.5: formal conformance suite + fixture runner
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
