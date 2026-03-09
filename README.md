# MTP — Methodology Transfer Protocol

**An open specification for transferring AI-developed methodologies between platforms, agents, and models — without transferring data.**

---

## The Problem

You develop a sophisticated analytical methodology in Claude, ChatGPT, or any capable AI system. Now you need to apply it in a different system — an enterprise Copilot, Azure OpenAI, or another AI tool that has access to the actual data.

Today, you re-explain everything from scratch. Intent, decisions, constraints, edge cases, dead ends — all lost in translation. MTP fixes this.

## What MTP Is

MTP is a structured YAML format that captures **the recipe without the ingredients**:

- **Intent** — why the methodology exists and what it achieves
- **Decision logic** — what was chosen, what was rejected, and why
- **Transformation steps** — reproducible, ordered, with dependencies
- **Edge cases** — unusual situations and their handling
- **Dead ends** — approaches that were tried and failed (so the target system doesn't repeat them)
- **Validation rules** — how to verify each step produced correct results

An MTP Package is platform-agnostic, data-free, human-readable, and executable by any sufficiently capable LLM.

## Why MTP Matters

**Today:** Thousands of enterprise workers manually re-explain AI-developed methodologies across platforms daily. Security policies prohibit sending sensitive data to commercial AI, so workers develop methods in capable commercial AI and transfer them by hand to restricted enterprise AI. Methodology degrades in every transfer.

**Tomorrow:** As AI agents operate autonomously across systems, they will need to transfer not just data or context, but working methodology. MTP is designed for both human-to-AI and AI-to-AI methodology transfer.

## Quick Start

1. Develop your methodology in any AI system
2. Use the [extraction prompt template](spec/MTP-SPEC-v0.1.md#42-extraction-prompt-template) to generate an MTP Package
3. Pass the MTP Package to your target AI system with the [application prompt template](spec/MTP-SPEC-v0.1.md#51-target-system-prompt-template)
4. Review the execution report for deviations and validation results

## Specification

📄 **[MTP Specification v0.1](spec/MTP-SPEC-v0.1.md)** — Full specification with format definition, extraction process, application process, and examples.

## Project Status

MTP is in early draft stage (v0.1). The specification is open for feedback, real-world validation, and contributions.

| Version | Status | Focus |
|---------|--------|-------|
| v0.1 | ✅ Current | YAML format, manual extraction/application |
| v0.2 | Planned | JSON Schema validation, extraction CLI tool |
| v0.3 | Future | Automated extraction from conversation exports |
| v1.0 | Vision | Native platform integration, agent-to-agent transfer |

## Contributing

MTP is an open specification. We welcome:

- **Feedback** on the format and process — open an issue
- **Real-world examples** — share your MTP Packages via pull request
- **Tooling** — extraction tools, validators, IDE integrations

## License

Apache 2.0 — see [LICENSE](LICENSE).

---

*MTP was created by [Lubor Fedák](https://github.com/lubor-fedak) to solve a real problem: the invisible cost of re-explaining AI-developed methodologies across platforms and security boundaries.*
