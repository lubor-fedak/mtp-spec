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

1. Develop your methodology in any AI system
2. Extract an MTP Package using the [extraction prompt template](spec/MTP-SPEC-v0.2.md#102-extraction-prompt-template)
3. Validate the package for schema conformance and redaction
4. Execute in your target AI system using the [application prompt template](spec/MTP-SPEC-v0.2.md#111-target-system-prompt-template)
5. Review the execution report — states, deviations, drift

## Specification

📄 **[MTP Specification v0.2](spec/MTP-SPEC-v0.2.md)** — Full specification: lifecycle, package format, provenance, execution semantics, redaction discipline, drift measurement, conformance levels, and benchmark framework. Current repository patch release: **0.2.1**.

📄 **[MTP Specification v0.1](spec/MTP-SPEC-v0.1.md)** — Original draft (superseded).

## Roadmap

| Version | Status | Focus |
|---------|--------|-------|
| v0.1 | ✅ Released | YAML format, manual extraction/application, JSON Schema |
| v0.2.x | ✅ Current | Lifecycle, provenance, execution semantics, redaction, drift, conformance. Latest patch: 0.2.1 |
| v0.3 | Planned | `mtp-lint` validator, redaction checker, canonical examples |
| v0.4 | Planned | `mtp-run` reference runtime CLI, platform adapters |
| v0.5 | Planned | Drift scoring engine, conformance test suite |
| v0.6 | Planned | Registry specification, signatures, approval workflows |
| v1.0 | Target | Production adapters, community benchmarks, enterprise reference architecture |

## Contributing

MTP is an open specification shaped by community feedback. We especially welcome:

- **Critical review** of execution semantics and drift measurement
- **Real-world extraction attempts** — try it on your workflow, report what's missing
- **Platform-specific insights** — how does MTP map to your AI stack?
- **Enterprise perspective** — does the policy envelope cover your compliance needs?

Open an issue, submit a PR, or start a discussion.

## License

Apache 2.0 — see [LICENSE](LICENSE).

---

*MTP was created by [Lubor Fedák](https://github.com/lubor-fedak) and shaped by feedback from the AI community. It solves a real and growing problem: the invisible cost of transferring AI-developed methodologies across platforms, security boundaries, and time.*
