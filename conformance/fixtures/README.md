# Conformance Fixtures

This directory contains the fixture packs executed by `mtp-conformance`.

Implemented structure:

- `l1-packages/valid/` and `l1-packages/invalid/` for schema-valid and schema-invalid packages
- `l2-execution/` covering all six execution states: `success`, `partial`, `deviation`, `failure`, `skipped`, `escalated`
- `l3-redaction/` covering `pii`, `secrets`, `client-identifiers`, `regulated`, and `clean`
- `l3-provenance/` for provenance and execution semantics presence checks
- `drift/self-score/` for reference self-score fixtures
- `drift/cross-report/` for baseline vs candidate drift comparison fixtures

Each fixture leaf contains a `fixture.yaml` manifest plus one or more referenced artifacts. Paths are resolved relative to the manifest location.
