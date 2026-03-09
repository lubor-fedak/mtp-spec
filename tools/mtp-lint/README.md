# mtp-lint

Validator, redaction checker, and linter for [MTP (Methodology Transfer Protocol)](https://github.com/lubor-fedak/mtp-spec) packages.

## Install

```bash
cd tools/mtp-lint
pip install -e .
```

## Usage

### Full check (schema + redaction + completeness + policy gate)

```bash
mtp-lint check examples/churn-risk-scoring-v0.2.yaml
mtp-lint check examples/churn-risk-scoring-v0.2.yaml --format json
mtp-lint check examples/churn-risk-scoring-v0.2.yaml --strict  # exit 1 on warnings too
```

### Schema validation only

```bash
mtp-lint validate examples/churn-risk-scoring-v0.2.yaml
mtp-lint validate examples/churn-risk-scoring-execution-report-v0.2.yaml
```

### Redaction scan only

```bash
mtp-lint redact examples/churn-risk-scoring-v0.2.yaml
mtp-lint redact package.yaml --client-dict client-terms.txt  # with client ID dictionary
```

### Completeness scoring only

```bash
mtp-lint score examples/churn-risk-scoring-v0.2.yaml
```

## What it checks

| Check | Command | Description |
|-------|---------|-------------|
| Schema | `validate` | JSON Schema validation against MTP v0.1 or v0.2 |
| Redaction | `redact` | PII, secrets, high-entropy strings, client identifiers |
| Completeness | `score` | Provenance, rationale, validation rules, execution semantics |
| Policy gate | `check` | All policy scans run and passed, classification present |

## Output formats

- `--format text` — human-readable (default)
- `--format json` — machine-readable, includes report hash

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | All checks passed (or warnings only) |
| 1 | Errors found: schema invalid, redaction findings, or policy gate failed |
| 2 | Input error (file not found, invalid format, wrong artifact type) |

Note: Policy gate failure is an error (exit 1), not a warning. Use `--strict` to also exit 1 on warnings (e.g., low completeness).
