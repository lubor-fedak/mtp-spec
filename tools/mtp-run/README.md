# mtp-run

Reference runtime CLI for executing [MTP (Methodology Transfer Protocol)](https://github.com/lubor-fedak/mtp-spec) packages.

Takes a validated MTP package, connects to an LLM, executes each step with strict execution semantics, and produces a standardized execution report with drift scoring.

## Install

```bash
cd tools/mtp-run
pip install -e .                    # mock adapter only (no API keys needed)
pip install -e ".[anthropic]"       # + Claude API support
pip install -e ".[openai]"          # + OpenAI / Azure OpenAI support
pip install -e ".[all]"             # all adapters
```

## Usage

### Execute with mock adapter (no API keys)

```bash
mtp-run exec examples/churn-risk-scoring-v0.2.yaml --data test-data.csv --adapter mock
mtp-run exec examples/churn-risk-scoring-v0.2.yaml --data test-data.csv --adapter mock -o report.yaml
```

### Execute with Claude

```bash
export ANTHROPIC_API_KEY=sk-ant-...
mtp-run exec package.yaml --data input.csv --adapter anthropic
mtp-run exec package.yaml --data input.csv --adapter anthropic --model claude-opus-4-20250514
```

### Execute with OpenAI

```bash
export OPENAI_API_KEY=sk-...
mtp-run exec package.yaml --data input.csv --adapter openai --model gpt-4o
```

### Execute with Azure OpenAI

```bash
export AZURE_OPENAI_API_KEY=...
export AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
mtp-run exec package.yaml --data input.csv --adapter openai --azure --model gpt-4o
```

### Compare execution reports (drift)

```bash
mtp-run drift report-claude.yaml report-azure.yaml
mtp-run drift report-march.yaml report-june.yaml --format json
```

### List available adapters

```bash
mtp-run adapters
```

## Commands

| Command | What it does |
|---------|-------------|
| `mtp-run exec` | Execute an MTP package against data through an LLM adapter |
| `mtp-run score` | Compute weighted drift score for a single execution report (spec §8.3) |
| `mtp-run adapters` | List available adapters and their configuration status |
| `mtp-run drift` | Compare two execution reports — state agreement and divergence |

## Execution Flow

```
1. Load MTP package
2. Load data file
3. Build system context (intent, approach, dead ends, constraints)
4. For each step (respecting depends_on):
   a. Check dependency states
   b. Build step prompt (action, validation, edge cases, prior outputs)
   c. Send to LLM via adapter
   d. Parse structured response
   e. Apply execution_semantics (on_failure, on_deviation)
   f. Record step result
5. Derive overall_status (spec §7.2)
6. Compute drift score (spec §8.3)
7. Produce execution report
```

## Adapters

| Adapter | Requires | Platforms |
|---------|----------|-----------|
| `mock` | Nothing | Deterministic simulation — CI/CD, demos, conformance testing |
| `anthropic` | `ANTHROPIC_API_KEY` | Claude (Sonnet, Opus, Haiku) |
| `openai` | `OPENAI_API_KEY` | GPT-4o, GPT-4, o1, o3 |
| `openai --azure` | `AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_ENDPOINT` | Azure OpenAI deployments |

### Mock Adapter

The mock adapter produces deterministic results for testing. Control step outcomes via markers in step actions:

| Marker in action text | Resulting state |
|----------------------|-----------------|
| `FORCE_FAIL` | failure |
| `FORCE_DEVIATE` | deviation |
| `FORCE_ESCALATE` | escalated |
| `FORCE_PARTIAL` | partial |
| (none) | success |

## Output

Execution reports follow the MTP execution report schema (`schema/mtp-execution-report-v0.2.json`) and include step states, deviations, drift score, and report hash.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Execution completed (success, partial, or deviation) |
| 1 | Execution failed or escalated |
| 2 | Input error (file not found, invalid package, adapter not available) |
