# Conformance Fixtures

This directory contains the fixture packs executed by `mtp-conformance`.

## Directory structure

```
conformance/fixtures/
├── l1-packages/
│   ├── valid/golden-package/          # Schema-valid v0.2 package
│   └── invalid/missing-policy/        # Schema-invalid package (missing policy)
├── l2-execution/
│   ├── success/                       # Both steps succeed
│   ├── partial/                       # Partial execution outcome
│   ├── deviation/                     # Step deviation with flag_and_proceed
│   ├── failure/                       # Step failure with halt semantics
│   ├── skipped/                       # Step skipped due to unmet dependency
│   └── escalated/                     # Step escalated to human review
├── l3-redaction/
│   ├── pii/email-leak/                # Email address in methodology text
│   ├── secrets/api-key-leak/          # API key in methodology text
│   ├── client-identifiers/client-name-leak/  # Client name leak
│   ├── regulated/health-record-leak/  # Health data in methodology text
│   └── clean/reference-package/       # Clean package (no leaks)
├── l3-provenance/
│   └── full-package/                  # Provenance + execution_semantics present
└── drift/
    ├── self-score/
    │   ├── mock-reference/            # Self-score = 1.0 (all success)
    │   └── deviation-reference/       # Self-score < 1.0 (deviation present)
    └── cross-report/
        └── mock-vs-real/              # Cross-report drift comparison
```

## Manifest format

Each fixture leaf directory contains a `fixture.yaml` manifest:

```yaml
id: l2-execution-success          # Unique fixture identifier
level: l1 | l2 | l3               # Conformance level (required)
kind: package_validation           # Fixture kind (see below)
description: Human-readable text   # What this fixture tests
# ... kind-specific fields below
```

### Required fields

| Field         | Type   | Description                          |
|---------------|--------|--------------------------------------|
| `id`          | string | Unique identifier across all fixtures |
| `level`       | string | One of `l1`, `l2`, `l3`             |
| `kind`        | string | Fixture kind (see below)             |
| `description` | string | Human-readable description           |

## Fixture kinds

### `package_validation` (L1)

Validates an MTP package against the JSON Schema.

```yaml
kind: package_validation
artifact: relative/path/to/package.yaml
expect:
  valid: true | false
```

### `execution` (L2)

Executes an MTP package with the mock adapter and checks execution states.

```yaml
kind: execution
package: package.yaml
data: relative/path/to/data.csv
adapter: mock
expect:
  overall_status: success | partial | deviation | failure | skipped | escalated
  step_states:
    1: success
    2: deviation
```

### `redaction` (L3)

Scans a package for redaction leaks (PII, secrets, client identifiers, regulated content).

```yaml
kind: redaction
artifact: package.yaml
client_dictionary:          # optional
  - "Acme Corp"
expect:
  passed: true | false
  categories:               # expected leak categories
    - pii
    - secrets
  policy_gate_passed: true  # optional: also check policy gate
```

### `drift_self` (L3)

Computes a self-drift score for a single execution report and compares to expected values.

```yaml
kind: drift_self
report: relative/path/to/report.yaml
expect:
  composite: 1.0
  tolerance: 0.0001
  components:
    step_fidelity: 1.0
    deviation_rate: 1.0
```

### `drift_compare` (L3)

Compares two execution reports and checks cross-report drift metrics.

```yaml
kind: drift_compare
baseline_report: relative/path/to/baseline.yaml
candidate_report: relative/path/to/candidate.yaml
expect:
  composite: 0.9111
  state_agreement: 0.8
  difference_steps: [3]
  tolerance: 0.0001
```

### `provenance` (L3)

Checks that provenance and execution_semantics blocks are present in all steps, edge cases, and dead ends.

```yaml
kind: provenance
artifact: relative/path/to/package.yaml
expect:
  steps: true
  edge_cases: true
  dead_ends: true
  execution_semantics: true
```

## Adding a new fixture

1. Create a new directory under the appropriate level/category
2. Add a `fixture.yaml` manifest with the required fields
3. Add any referenced artifacts (packages, reports, data files)
4. Paths in the manifest are resolved relative to the manifest location
5. Run `mtp-conformance run --level all --format json` to verify
6. The fixture ID must be unique across the entire fixture corpus

## Conformance levels (cumulative)

- **L1**: Package schema validation only
- **L2**: L1 + execution state coverage (all 6 states)
- **L3**: L2 + redaction scanning + provenance checks + drift scoring
