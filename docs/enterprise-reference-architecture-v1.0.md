# Enterprise Reference Architecture v1.0

This document describes the reference production deployment shape for MTP `1.0`.

## Topology

```text
┌──────────────────────────────┐
│ Authoring Zone               │
│ Claude / ChatGPT / analyst   │
│ mtp-extract                  │
└──────────────┬───────────────┘
               │ draft package
               v
┌──────────────────────────────┐
│ Validation and Release Zone  │
│ mtp-lint                     │
│ mtp-conformance              │
│ mtp-benchmark                │
│ mtp-release                  │
│ mtp-registry                 │
└──────────────┬───────────────┘
               │ approved package + trust sidecars
               v
┌──────────────────────────────┐
│ Enterprise Execution Zone    │
│ mtp-run                      │
│ enterprise AI adapters       │
│ client data stays local      │
└──────────────┬───────────────┘
               │ execution report
               v
┌──────────────────────────────┐
│ Evidence and Governance      │
│ registry entries             │
│ approvals                    │
│ benchmark matrix             │
│ compatibility contract       │
└──────────────────────────────┘
```

## Control Points

1. Authoring happens without client data.
2. Draft packages pass `mtp-lint` before promotion.
3. Production claims require conformance and benchmark evidence.
4. Registry publication adds detached trust artifacts instead of mutating the package.
5. Execution happens inside the data boundary with `mtp-run`.
6. Reports can be compared back to baseline methodology using weighted drift.

## Trust Layer

`mtp-registry` in `1.0` supports two trust patterns:

- direct key material via env vars or files
- `local-kms` indirection via `mtp-key-provider-manifest-v1.0`

The reference architecture intentionally keeps this simple so enterprises can
plug in their own secret manager or KMS wrapper without changing release
artifacts.

## Reference Release Flow

1. Extract conversation into draft package.
2. Validate package and redaction envelope.
3. Execute a baseline report.
4. Run conformance.
5. Run benchmark suite across adapters.
6. Generate provider matrix and compatibility contract.
7. Sign, approve, and publish artifacts into the registry.
8. Execute approved packages inside the enterprise boundary.

## Operational Guidance

- Treat the registry as the system of record for approved methodologies.
- Keep package/data separation strict.
- Publish benchmark evidence with every production support claim.
- Use compatibility contracts to freeze what “supported” means for each release.
