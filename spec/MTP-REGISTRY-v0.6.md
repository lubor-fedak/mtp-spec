# MTP Registry Extension v0.6

**Author:** Lubor Fedák  
**Date:** 2026-03-09  
**Status:** Draft  
**Applies to:** MTP packages and execution reports already validated under MTP v0.2

---

## 1. Purpose

`v0.5` made MTP executable and testable. `v0.6` adds the trust layer needed to
store, sign, approve, and promote MTP artifacts as governed assets.

The registry extension introduces three portable sidecar artifacts:

- **Signature Envelope** — detached cryptographic integrity metadata for a package or execution report
- **Approval Record** — a human governance decision tied to a signed artifact hash
- **Registry Entry** — the publishable asset record that binds artifact, signatures, approvals, and release status

These are intentionally detached from the `v0.2` package format. Existing
packages and execution reports stay valid without schema changes.

---

## 2. Trust Model

### 2.1 Artifact Lifecycle

The reference workflow is:

```text
Validate → Sign → Approve → Publish → Verify
```

1. A package or execution report is validated under existing MTP schemas.
2. A detached signature envelope is created for the canonical artifact content.
3. One or more approval records reference the signed artifact hash.
4. A registry entry publishes the artifact into a local or enterprise registry.
5. Consumers verify the registry entry plus all linked trust artifacts.

For `approved` registry entries, the reference workflow requires a successful
cryptographic signature verification at publish time.

### 2.2 Reference Signature Profiles

The reference `v0.6` implementation supports two profiles:

- `profile`: `hmac-sha256` — pragmatic bootstrap for local and CI workflows
- `profile`: `ed25519` — detached asymmetric signing for stronger distribution and verification workflows
- `canonicalization`: `json-sorted-v1`

These profiles remain intentionally simple. `v1.0` adds a stable key-provider
manifest so signing workflows can resolve keys through a local-KMS abstraction
without changing registry entry semantics.

### 2.3 Approval Semantics

Approval is detached from the package itself.

An approval record answers:

- what artifact hash was reviewed
- who reviewed it
- what policy was applied
- whether the decision was `approved` or `rejected`
- which supporting evidence was used

### 2.4 Registry Status

Registry entries use four reference states:

- `draft` — signed and stored, not yet approved for use
- `review` — under governance review
- `approved` — published for intended channel, must have at least one approved approval record
- `deprecated` — retained for traceability but no longer promoted

---

## 3. Registry Layout

The reference local layout created by `mtp-registry init` is:

```text
registry/
  registry.yaml
  artifacts/
    packages/
    execution-reports/
  signatures/
  approvals/
  entries/
```

Registry entries use relative references so the whole registry remains portable.

---

## 4. Artifact Types

### 4.1 Registry Manifest

Describes the registry identity and layout:

- registry id
- registry name
- layout version
- default channel
- supported channels

### 4.2 Signature Envelope

Detached integrity and signer metadata for a primary MTP artifact:

- artifact type
- artifact identity
- artifact hash
- signature profile
- signer id
- signature value

### 4.3 Approval Record

Detached governance decision for a signed artifact:

- artifact type and hash
- approver identity
- policy name
- decision
- rationale
- evidence refs

### 4.4 Registry Entry

Publishable asset record that binds:

- artifact ref and hash
- registry status and channel
- signature refs
- approval refs
- optional conformance summary hash
- source provenance such as repo and commit

---

## 5. Reference CLI

The reference implementation lives in `tools/mtp-registry/` and provides:

```bash
mtp-registry init registry/ --name "Internal MTP Registry"
mtp-registry sign package.yaml --profile hmac-sha256 --key-env MTP_REGISTRY_SIGNING_KEY --key-id dev-key --signer release-bot
mtp-registry verify package.yaml --signature package.signature.v0.6.yaml --key-env MTP_REGISTRY_SIGNING_KEY
mtp-registry sign package.yaml --profile ed25519 --key-file signer.pem --key-id dev-key --signer release-bot
mtp-registry verify package.yaml --signature package.signature.v0.6.yaml --key-file signer.pub.pem
mtp-registry approve package.yaml --signature package.signature.v0.6.yaml --approver-id risk-committee --approver-name "Risk Committee" --role governance --status approved --policy enterprise-v1 --rationale "Approved for internal use."
mtp-registry publish package.yaml --registry-dir registry/ --signature package.signature.v0.6.yaml --key-env MTP_REGISTRY_SIGNING_KEY --approval package.approval.v0.6.yaml --status approved --channel internal
mtp-registry check-entry registry/entries/example.registry-entry.yaml --registry-dir registry/ --key-env MTP_REGISTRY_SIGNING_KEY
```

---

## 6. Schemas

`v0.6` adds the following schemas:

- `schema/mtp-registry-manifest-v0.6.json`
- `schema/mtp-signature-envelope-v0.6.json`
- `schema/mtp-approval-record-v0.6.json`
- `schema/mtp-registry-entry-v0.6.json`

These validate the trust layer only. They do not replace `mtp-package-v0.2.json`
or `mtp-execution-report-v0.2.json`.

---

## 7. Design Limits

The reference `v0.6` implementation is intentionally conservative:

- local filesystem registry only
- HMAC and Ed25519 reference profiles only
- detached approvals only
- no multi-party quorum logic
- no external KMS or certificate chain

Those remain `v1.0` concerns. `v0.6` exists to define the asset model and make
registry publication reproducible today. Production release semantics are
specified separately in [MTP-COMPATIBILITY-v1.0.md](MTP-COMPATIBILITY-v1.0.md).
