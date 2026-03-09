# mtp-registry

Registry, signing, approval, and key-provider workflow tooling for MTP `1.0`.

## Install

```bash
pip install -e tools/mtp-registry
```

For development:

```bash
pip install -e "tools/mtp-registry[dev]"
```

## What It Does

`mtp-registry` implements the stable `v0.6` trust layer plus the `v1.0`
key-provider indirection surface on top of validated MTP `v0.2` packages and
execution reports. The trust model uses detached sidecar artifacts — existing
packages and reports are never mutated.

Three sidecar artifact types:

- **Signature Envelope** — detached `hmac-sha256` or `ed25519` signature over the canonical JSON representation of a package or execution report
- **Approval Record** — governance decision (approved/rejected) tied to the signed artifact hash, with approver identity, policy, and rationale
- **Registry Entry** — publishable asset record binding artifact, signatures, approvals, release status, and optional conformance/provenance metadata

## Trust Model

### Artifact Lifecycle

```
Validate → Sign → Approve → Publish → Verify
```

1. Package or execution report validated under MTP v0.2 schemas
2. Detached signature envelope created for canonical artifact content
3. One or more approval records reference the signed artifact hash
4. Registry entry publishes the artifact into a local registry
5. Consumers verify the entry plus all linked trust artifacts

### Reference Signature Profiles

- Profile: `hmac-sha256`
- Profile: `ed25519`
- Canonicalization: `json-sorted-v1` (sorted keys, compact separators, UTF-8)

These are bootstrap profiles for local and CI workflows. Future profiles can add KMS-backed signatures without changing registry entry semantics.

### Registry Status

| Status | Description |
|--------|-------------|
| `draft` | Signed and stored, not yet approved |
| `review` | Under governance review |
| `approved` | Published for use; requires cryptographic verification + at least one approved approval |
| `deprecated` | Retained for traceability, no longer promoted |

## Commands

| Command | Description |
|---------|-------------|
| `mtp-registry init <dir>` | Initialize a local registry directory structure |
| `mtp-registry init-key-provider <file>` | Initialize an empty local-kms key provider manifest |
| `mtp-registry validate-key-provider <file>` | Validate a local-kms key provider manifest |
| `mtp-registry sign <artifact>` | Create a detached signature envelope |
| `mtp-registry verify <artifact>` | Verify artifact against a signature envelope |
| `mtp-registry approve <artifact>` | Create an approval record for a signed artifact |
| `mtp-registry publish <artifact>` | Copy artifact + trust sidecars into registry, create entry |
| `mtp-registry list <registry-dir>` | List registry entries (filter by `--status`, `--channel`) |
| `mtp-registry check-entry <entry>` | Verify a published entry and all referenced trust artifacts |

### Example workflow

```bash
# 1. Initialize registry
mtp-registry init registry/ --name "Internal MTP Registry"

# 2. Sign a package
export MTP_REGISTRY_SIGNING_KEY=your-shared-secret
mtp-registry sign package.yaml \
  --profile hmac-sha256 \
  --key-env MTP_REGISTRY_SIGNING_KEY \
  --key-id dev-key \
  --signer release-bot

# 2b. Or use Ed25519
mtp-registry sign package.yaml \
  --profile ed25519 \
  --key-file signer.pem \
  --key-id dev-key \
  --signer release-bot

# 2c. Or route key lookup through a local-kms manifest
mtp-registry init-key-provider registry/key-provider.yaml
# populate key ids and env refs, then:
mtp-registry sign package.yaml \
  --provider local-kms \
  --key-provider-manifest registry/key-provider.yaml \
  --key-id release-key \
  --signer release-bot

# 3. Verify the signature
mtp-registry verify package.yaml \
  --signature package.signature.v0.6.yaml \
  --key-env MTP_REGISTRY_SIGNING_KEY

mtp-registry verify package.yaml \
  --signature package.signature.v0.6.yaml \
  --key-file signer.pub.pem

# 4. Create approval record
mtp-registry approve package.yaml \
  --signature package.signature.v0.6.yaml \
  --approver-id risk-committee \
  --approver-name "Risk Committee" \
  --role governance \
  --status approved \
  --policy enterprise-v1 \
  --rationale "Approved for internal use."

# 5. Publish to registry
mtp-registry publish package.yaml \
  --registry-dir registry/ \
  --signature package.signature.v0.6.yaml \
  --key-env MTP_REGISTRY_SIGNING_KEY \
  --approval package.approval.v0.6.yaml \
  --status approved \
  --channel internal \
  --conformance-level l3

# 6. List entries
mtp-registry list registry/ --status approved

# 7. Verify entry
mtp-registry check-entry registry/entries/example.registry-entry.yaml \
  --registry-dir registry/ \
  --key-env MTP_REGISTRY_SIGNING_KEY
```

## Registry Layout

`mtp-registry init` creates:

```
registry/
├── registry.yaml                    # Manifest (id, name, channels)
├── artifacts/
│   ├── packages/{id}/{ver}/         # Published packages
│   └── execution-reports/{id}/{ver}/ # Published execution reports
├── signatures/{id}/{ver}/           # Detached signature envelopes
├── approvals/{id}/{ver}/            # Detached approval records
└── entries/                         # Registry entries
```

All references within the registry use relative paths so the entire directory remains portable.

## Schemas

v0.6 adds four JSON schemas (under `schema/`):

| Schema | Validates |
|--------|-----------|
| `mtp-registry-manifest-v0.6.json` | Registry manifests |
| `mtp-signature-envelope-v0.6.json` | Signature envelopes |
| `mtp-approval-record-v0.6.json` | Approval records |
| `mtp-registry-entry-v0.6.json` | Registry entries |

These validate the trust layer only. They do not replace `mtp-package-v0.2.json` or `mtp-execution-report-v0.2.json`.

## Design Limits

The registry artifact model is stable, but intentionally conservative:

- Local filesystem registry only
- HMAC-SHA256 and Ed25519 reference profiles only
- local-kms indirection only (no cloud KMS adapters yet)
- Detached approvals only
- No multi-party quorum logic
- No certificate chain or hardware-backed attestation

`v1.0` makes the trust layer production-usable through stable release artifacts
and key-provider manifests, but deliberately avoids over-prescribing enterprise
KMS integration details.
