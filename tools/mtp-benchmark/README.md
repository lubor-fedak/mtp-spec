# mtp-benchmark

Benchmark runner and adapter certification tooling for MTP.

`mtp-benchmark` turns `v1.0` claims such as "production adapters" and
"community benchmarks" into concrete suite/result artifacts.

## Install

```bash
pip install -e tools/mtp-run
pip install -e tools/mtp-benchmark
```

## Commands

| Command | What it does |
|---------|--------------|
| `mtp-benchmark validate <artifact>` | Validate a benchmark suite, benchmark result, or adapter certification artifact |
| `mtp-benchmark run <suite>` | Execute benchmark adapters, compare reports against baseline, and emit a result artifact |
| `mtp-benchmark certify <result> --adapter <name>` | Generate an adapter certification artifact from a benchmark result |

## Example

```bash
mtp-benchmark run examples/benchmarks/churn-risk-benchmark-suite-v0.7.yaml \
  --output-dir /tmp/mtp-benchmark

mtp-benchmark certify /tmp/mtp-benchmark/churn-risk-benchmark-result-v0.7.yaml \
  --adapter mock
```
