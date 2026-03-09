# MTP — Methodology Transfer Protocol

**The missing control plane between methodology authoring and methodology execution across AI boundaries.**

MCP connects models to tools. MTP connects methodology authoring to methodology execution.

---

## The Problem

You develop a sophisticated analytical methodology in Claude, ChatGPT, or any capable AI system. Now you need to apply it in a different system — an enterprise Copilot, Azure OpenAI, or another AI tool that has access to the actual data.

Today, you re-explain everything from scratch. Intent, decisions, constraints, edge cases, dead ends — all lost in translation. The receiving system produces subtly different results with no way to detect or measure the divergence.

This isn't a tooling inconvenience. It's a structural gap in the AI stack.

## What MTP Is

MTP is a controlled execution loop for methodology portability:

```
Extract → Validate → Execute → Report → Compare → Version
```

An MTP Package captures **the recipe without the ingredients** — intent, decision logic, steps, edge cases, dead ends, and validation rules. But MTP is not just a file format. It defines:

- **Provenance** — every step traces back to where it was authored
- **Execution semantics** — precise definitions of success, failure, deviation, partial completion, and escalation
- **Redaction discipline** — auditable proof that no data, PII, or secrets leaked into the methodology
- **Drift measurement** — quantifiable scoring of how much a methodology degrades in transfer
- **Conformance levels** — testable criteria for platform compatibility

## Where MTP Sits in the Stack

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

## Why MTP Matters

**Today:** Thousands of enterprise workers manually re-explain AI-developed methodologies across platforms daily. Security policies prohibit sending sensitive data to commercial AI, so workers develop methods in capable commercial AI and transfer them by hand to restricted enterprise AI. Methodology degrades in every transfer. Nobody measures the drift.

**Tomorrow:** As AI agents operate autonomously across systems, they will need to transfer not just data or context, but working methodology — with verifiable provenance, auditable redaction, and measurable fidelity. MTP is designed for both human-to-AI and AI-to-AI methodology transfer.

## Quick Start

### 1. Extract a methodology

Develop your methodology in any AI system, then extract an MTP Package using the [extraction prompt template](spec/MTP-SPEC-v0.2.md#102-extraction-prompt-template).

### 2. Validate with mtp-lint

```bash
cd tools/mtp-lint && pip install -e .
mtp-lint check your-package.yaml
```

This runs schema validation, redaction scanning, completeness scoring, and the policy gate in one pass.

### 3. Execute with mtp-run

```bash
cd tools/mtp-run && pip install -e .
mtp-run exec your-package.yaml --data your-data.csv --adapter mock      # test locally
mtp-run exec your-package.yaml --data your-data.csv --adapter anthropic  # run via Claude
```

This executes each step through the selected LLM, respects execution semantics, and produces a standardized report.

### 4. Review the execution report

Check step states, deviations, and drift. Compare across platforms:

```bash
mtp-run drift report-claude.yaml report-azure.yaml
```

### 5. Run the conformance suite

```bash
cd tools/mtp-conformance && pip install -e .
mtp-conformance run --level l3
```

This runs the fixture-driven L1/L2/L3 conformance corpus across schema validation, execution semantics, redaction detection, provenance presence, and drift reference cases.

### 6. Publish into a registry

```bash
cd tools/mtp-registry && pip install -e .
mtp-registry init registry/ --name "Internal MTP Registry"
mtp-registry sign your-package.yaml --key-env MTP_REGISTRY_SIGNING_KEY --key-id dev-key --signer release-bot
```

This adds detached trust artifacts on top of validated MTP packages and reports: signatures, approvals, and publishable registry entries.

## Specification

📄 **[MTP Specification v0.2](spec/MTP-SPEC-v0.2.md)** — Full specification: lifecycle, package format, provenance, execution semantics, redaction discipline, drift measurement, conformance levels, and benchmark framework. Current patch: **0.2.1**.

📄 **[MTP Registry Extension v0.6](spec/MTP-REGISTRY-v0.6.md)** — Registry layout, detached signature envelopes, approval records, registry entries, and local trust workflow.

📄 **[MTP Specification v0.1](spec/MTP-SPEC-v0.1.md)** — Original draft (superseded by v0.2).

## Schemas

MTP provides JSON Schemas (Draft 2020-12) for machine validation of all artifacts:

| Schema | Validates | Strictness |
|--------|-----------|------------|
| [mtp-package-v0.2.json](schema/mtp-package-v0.2.json) | MTP Packages | Strict: `mtp_version` must be `"0.2"`, `policy` required, `provenance` and `execution_semantics` required on steps |
| [mtp-execution-report-v0.2.json](schema/mtp-execution-report-v0.2.json) | Execution Reports | Includes conditional validation for `overall_status` derivation, state-dependent required fields |
| [mtp-registry-manifest-v0.6.json](schema/mtp-registry-manifest-v0.6.json) | Registry manifests | Local registry identity and channel layout |
| [mtp-signature-envelope-v0.6.json](schema/mtp-signature-envelope-v0.6.json) | Signature envelopes | Detached trust metadata for packages and execution reports |
| [mtp-approval-record-v0.6.json](schema/mtp-approval-record-v0.6.json) | Approval records | Governance decisions tied to artifact hashes |
| [mtp-registry-entry-v0.6.json](schema/mtp-registry-entry-v0.6.json) | Registry entries | Published registry assets with trust refs and lifecycle state |
| [mtp-package-v0.1.json](schema/mtp-package-v0.1.json) | Legacy v0.1 packages | Permissive: backward compatibility |

v0.1 packages are correctly rejected by the v0.2 schema. Use the v0.1 schema for legacy packages.

## Tooling

### mtp-lint (v0.3)

Validator, redaction checker, completeness scorer, and enterprise policy gate. See [tools/mtp-lint/README.md](tools/mtp-lint/README.md) for full usage.

```bash
cd tools/mtp-lint && pip install -e .
```

| Command | What it does |
|---------|-------------|
| `mtp-lint check <file>` | Full pipeline: schema + redaction + completeness + policy gate |
| `mtp-lint validate <file>` | Schema validation only (packages and execution reports) |
| `mtp-lint redact <file>` | Redaction scan: PII, secrets, entropy, client identifiers, regulated content, literal data |
| `mtp-lint score <file>` | Completeness scoring: provenance, rationale, validation rules, execution semantics |

All commands support `--format json` for machine-readable output with report hash. `check` exits with code 1 on schema errors, redaction findings, or policy gate failure.

### mtp-run (v0.4)

Reference runtime for executing MTP packages through LLM adapters. See [tools/mtp-run/README.md](tools/mtp-run/README.md) for full usage.

```bash
cd tools/mtp-run && pip install -e .           # mock adapter only
cd tools/mtp-run && pip install -e ".[all]"    # all adapters (Claude, OpenAI, Azure)
```

| Command | What it does |
|---------|-------------|
| `mtp-run exec <package> --data <file>` | Execute a package against data via LLM adapter |
| `mtp-run score <report>` | Compute weighted drift score for a single report (spec §8.3) |
| `mtp-run adapters` | List available adapters and their configuration status |
| `mtp-run drift <report1> <report2>` | Compute weighted cross-report drift plus step agreement and per-step differences |
| `mtp-run e2e <package> --data <file> --output-dir <dir>` | Run mock plus one configured real adapter and store both reports with comparison JSON |

Supported adapters: `mock` (deterministic, no API keys), `anthropic` (Claude), `openai` (GPT-4o), `openai --azure` (Azure OpenAI).

### mtp-conformance (v0.5)

Reference conformance suite and release-gate runner. See [tools/mtp-conformance/README.md](tools/mtp-conformance/README.md) for full usage.

```bash
cd tools/mtp-conformance && pip install -e .
```

| Command | What it does |
|---------|-------------|
| `mtp-conformance run --level l1` | Run package-schema conformance fixtures |
| `mtp-conformance run --level l2` | Run cumulative L1 + execution-state fixtures |
| `mtp-conformance run --level l3` | Run cumulative L1 + L2 + redaction + drift + provenance fixtures |
| `mtp-conformance run --level all --format json` | Emit full machine-readable release-gate summary with stable summary hash |

Fixture corpus lives in [conformance/fixtures/README.md](conformance/fixtures/README.md). CI runs the conformance suite automatically as a release gate.

### mtp-registry (v0.6)

Registry, signing, and approval workflow tooling. See [tools/mtp-registry/README.md](tools/mtp-registry/README.md) for full usage.

```bash
cd tools/mtp-registry && pip install -e .
```

| Command | What it does |
|---------|-------------|
| `mtp-registry init <dir>` | Initialize a local MTP registry layout |
| `mtp-registry sign <artifact>` | Generate a detached signature envelope using the reference `hmac-sha256` profile |
| `mtp-registry verify <artifact>` | Verify artifact hash, identity, and signature envelope |
| `mtp-registry approve <artifact>` | Create a detached approval record tied to the artifact hash |
| `mtp-registry publish <artifact>` | Copy artifact and trust sidecars into a registry and generate a registry entry |
| `mtp-registry check-entry <entry>` | Verify a published registry entry plus all referenced trust artifacts |

## Examples

| File | Type | Description |
|------|------|-------------|
| [churn-risk-scoring-v0.2.yaml](examples/churn-risk-scoring-v0.2.yaml) | Package (v0.2) | Golden v0.2 package — customer churn scoring with full provenance, execution semantics, and policy envelope |
| [churn-risk-scoring-mock-execution-report-v0.2.yaml](examples/churn-risk-scoring-mock-execution-report-v0.2.yaml) | Exec Report (v0.2) | Deterministic mock runtime report from `mtp-run exec` — 5 steps success, drift 1.0 |
| [churn-risk-scoring-execution-report-v0.2.yaml](examples/churn-risk-scoring-execution-report-v0.2.yaml) | Exec Report (v0.2) | Example real-platform-style execution report with deviation handling and corrected weighted drift score |
| [registry.yaml](examples/registry/registry.yaml) | Registry Manifest (v0.6) | Reference local registry initialized by `mtp-registry` |
| [customer-churn-risk-scoring-1.0.0.registry-entry.yaml](examples/registry/entries/customer-churn-risk-scoring-1.0.0.registry-entry.yaml) | Registry Entry (v0.6) | Published registry entry for the churn scoring package with signature and approval refs |
| [test-data-churn.csv](examples/test-data-churn.csv) | Test Data | Sample data for running the churn scoring package |
| [valuation-report-extraction.yaml](examples/valuation-report-extraction.yaml) | Package (v0.1) | Document processing methodology (v0.1 format) |

Try it yourself:
```bash
mtp-lint check examples/churn-risk-scoring-v0.2.yaml
mtp-run exec examples/churn-risk-scoring-v0.2.yaml --data examples/test-data-churn.csv --adapter mock
MTP_REGISTRY_SIGNING_KEY=mtp-example-registry-key-v0.6 mtp-registry check-entry examples/registry/entries/customer-churn-risk-scoring-1.0.0.registry-entry.yaml --registry-dir examples/registry --key-env MTP_REGISTRY_SIGNING_KEY
```

## Roadmap

| Version | Status | Focus |
|---------|--------|-------|
| v0.1 | ✅ Released | YAML format, manual extraction/application, JSON Schema |
| v0.2.x | ✅ Released | Lifecycle, provenance, execution semantics, redaction, drift, conformance. Patch: 0.2.1 |
| v0.3.x | ✅ Released | `mtp-lint` CLI: schema validator, redaction scanner (6 categories), completeness scorer, policy gate. Patch: 0.3.2 |
| v0.4 | ✅ Released | `mtp-run` reference runtime CLI: execution engine, adapters (mock, Anthropic, OpenAI, Azure), drift comparison |
| v0.5 | ✅ Released | `mtp-conformance` fixture runner, L1/L2/L3 fixture packs, release-gate summaries, CI conformance reporting |
| v0.6 | ✅ Current | `mtp-registry` CLI, registry schemas, detached signature envelopes, approval records, local registry publication workflow |
| v1.0 | Target | Production adapters, community benchmarks, enterprise reference architecture |

## Contributing

MTP is an open specification shaped by community feedback. We especially welcome:

- **Critical review** of execution semantics and drift measurement
- **Real-world extraction attempts** — try it on your workflow, report what's missing
- **Platform-specific insights** — how does MTP map to your AI stack?
- **Enterprise perspective** — does the policy envelope cover your compliance needs?
- **Tooling contributions** — extraction tools, IDE integrations, CI/CD plugins

Open an issue, submit a PR, or start a discussion.

## License

Apache 2.0 — see [LICENSE](LICENSE).

---

*MTP was created by [Lubor Fedák](https://github.com/lubor-fedak) and shaped by feedback from the AI community. It solves a real and growing problem: the invisible cost of transferring AI-developed methodologies across platforms, security boundaries, and time.*
