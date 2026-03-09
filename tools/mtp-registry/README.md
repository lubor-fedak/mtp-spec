# mtp-registry

Registry, signing, and approval workflow tooling for MTP.

## Install

```bash
cd tools/mtp-registry && pip install -e .
```

For development:

```bash
cd tools/mtp-registry && pip install -e ".[dev]"
```

## What It Does

`mtp-registry` introduces the `v0.6` trust layer:

- local registry initialization
- detached signature envelopes for packages and execution reports
- approval record generation
- registry publishing with copied artifacts and trust metadata
- entry verification against linked artifacts, signatures, and approvals

The reference signature profile is `hmac-sha256`. It is symmetric and intended
as the bootstrap implementation for reproducible signing in local and CI
workflows. Future registry profiles can add asymmetric signatures without
changing registry entry semantics.

Approved registry publication requires `--key-env` during `publish` so the
signature envelope is cryptographically verified before the entry is written.

## Commands

```bash
mtp-registry init registry/ --name "Internal MTP Registry"
mtp-registry sign examples/churn-risk-scoring-v0.2.yaml --key-env MTP_REGISTRY_SIGNING_KEY --key-id dev-key --signer release-bot
mtp-registry verify examples/churn-risk-scoring-v0.2.yaml --signature signature.yaml --key-env MTP_REGISTRY_SIGNING_KEY
mtp-registry approve examples/churn-risk-scoring-v0.2.yaml --signature signature.yaml --approver-id risk-committee --approver-name "Risk Committee" --role governance --status approved --policy enterprise-v1 --rationale "Approved for internal use."
mtp-registry publish examples/churn-risk-scoring-v0.2.yaml --registry-dir registry/ --signature signature.yaml --key-env MTP_REGISTRY_SIGNING_KEY --approval approval.yaml --status approved --channel internal
mtp-registry check-entry registry/entries/churn-risk-scoring-1.0.0.registry-entry.yaml --registry-dir registry/ --key-env MTP_REGISTRY_SIGNING_KEY
```

## Registry Layout

`mtp-registry init` creates:

- `registry.yaml`
- `artifacts/packages/`
- `artifacts/execution-reports/`
- `signatures/`
- `approvals/`
- `entries/`

Published entries use relative references so the registry stays portable.
