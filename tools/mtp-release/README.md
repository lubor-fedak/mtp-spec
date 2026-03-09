# mtp-release

Release-contract tooling for MTP `1.0`.

This tool turns conformance, benchmark, and documentation evidence into
machine-readable `1.0` release artifacts:

- provider certification matrix
- compatibility contract

## Install

```bash
pip install -e tools/mtp-release
```

## Commands

| Command | What it does |
|---------|--------------|
| `mtp-release validate <artifact>` | Validate a provider matrix or compatibility contract artifact |
| `mtp-release matrix --benchmark-result <file>` | Build a provider certification matrix from benchmark output and certifications |
| `mtp-release contract --provider-matrix <file>` | Build a compatibility contract for a production release |

## Example

```bash
mtp-release matrix \
  --benchmark-result examples/benchmarks/churn-risk-benchmark-result-v0.7.yaml \
  --certification examples/benchmarks/mock-adapter-certification-v0.7.yaml \
  -o /tmp/mtp-provider-matrix-v1.0.yaml

mtp-release contract \
  --release-version 1.0.0 \
  --provider-matrix /tmp/mtp-provider-matrix-v1.0.yaml \
  --conformance-level all \
  --architecture-ref docs/enterprise-reference-architecture-v1.0.md \
  -o /tmp/mtp-compatibility-contract-v1.0.yaml
```
