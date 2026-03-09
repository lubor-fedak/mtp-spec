# MTP Compatibility Contract v1.0

**Author:** Lubor Fedák  
**Date:** 2026-03-09  
**Status:** Production  
**Applies to:** MTP production releases built on the stable `v0.2` package and execution-report schemas

---

## 1. Purpose

`v1.0` defines the release-level contract for production MTP deployments.

The core wire format remains stable on:

- `mtp-package-v0.2.json`
- `mtp-execution-report-v0.2.json`
- `mtp-registry-* v0.6`
- `mtp-benchmark-* v0.7`

What `v1.0` adds is the production governance layer around those stable
artifacts:

- provider certification matrix
- compatibility contract
- key provider manifest for local-KMS style trust indirection
- enterprise reference architecture

---

## 2. Stable Compatibility Promise

An MTP `1.0` release makes the following promises:

1. Newly emitted methodology packages remain `mtp_version: "0.2"`.
2. Newly emitted execution reports remain `mtp_spec_version: "0.2"`.
3. Registry trust artifacts remain detached sidecars and do not mutate package or report payloads.
4. Production evidence always includes both conformance results and a provider certification matrix.
5. Consumers can validate release claims mechanically from published artifacts.

---

## 3. Provider Matrix

The provider matrix is the machine-readable statement of adapter support for a
specific benchmark suite.

Each entry records:

- provider
- variant
- model
- certification status
- whether the adapter was available
- whether the adapter executed
- whether benchmark thresholds passed
- measured drift and state agreement when available

Reference statuses:

- `certified` — benchmark executed and passed, with a published certification artifact
- `not_certified` — benchmark executed but did not earn certification
- `skipped` — adapter was available but not executed for the published run
- `not_evaluated` — adapter was not available or no benchmark evidence exists

The provider matrix is descriptive, not marketing. Production support claims
must match the matrix exactly.

---

## 4. Compatibility Contract

The compatibility contract is the top-level release declaration for `1.0`.

It binds together:

- release version and status
- stable normative layer versions
- toolchain versions used to produce release evidence
- backward compatibility policy
- conformance level
- provider matrix reference
- documentation references

The compatibility contract is valid only if all referenced artifacts remain
available and schema-valid.

---

## 5. Key Provider Manifest

`v1.0` introduces a key provider manifest for `mtp-registry`.

Its purpose is not to standardize enterprise KMS APIs. Its purpose is to define
a stable indirection layer between signing workflows and concrete key storage.

The reference provider is:

- `local-kms`

This provider resolves signing and verification material from environment
variables or local file references via stable `key_id` entries. It is suitable
for:

- local release workflows
- CI/CD pipelines
- secret-manager-backed wrapper scripts

Cloud KMS adapters can be added later without changing registry entry semantics.

---

## 6. Release Criteria

A production `1.0` release should publish at minimum:

1. A stable `v0.2` package example.
2. A stable `v0.2` execution report example.
3. A successful `mtp-conformance` summary at `l3` or `all`.
4. A `v1.0` provider matrix derived from benchmark evidence.
5. A `v1.0` compatibility contract referencing the matrix and architecture.
6. A registry publication example with detached trust artifacts.

---

## 7. Backward Compatibility

`1.0` keeps backward readability for legacy `v0.1` packages through validation
and migration tooling, but production generation targets only the stable `v0.2`
contract.

This means:

- validate: `v0.1` and `v0.2` packages
- emit: `v0.2` packages only
- validate: `v0.2` execution reports only
- sign/publish: detached `v0.6` trust artifacts

---

## 8. Enterprise Interpretation

In production, “MTP-compatible” should mean all of the following:

- packages and reports validate
- redaction and policy gates pass
- runtime execution is benchmarked and measured
- trust artifacts are verifiable
- release claims are backed by a provider matrix and compatibility contract

That is the operational meaning of `1.0`.
