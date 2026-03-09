# mtp-conformance

Fixture-driven conformance runner for MTP.

## Install

Install all three tools in the same environment:

```bash
cd tools/mtp-lint && pip install -e .
cd ../mtp-run && pip install -e .
cd ../mtp-conformance && pip install -e .
```

For development:

```bash
cd tools/mtp-conformance && pip install -e ".[dev]"
```

## Usage

Run level-specific conformance:

```bash
mtp-conformance run --level l1
mtp-conformance run --level l2
mtp-conformance run --level l3
mtp-conformance run --level l3 --format json
mtp-conformance run --level all --format json
```

Levels are cumulative:

- `l1` runs package validation fixtures
- `l2` runs `l1` + execution fixtures
- `l3` runs `l1` + `l2` + redaction + drift + provenance fixtures
- `all` runs the full fixture corpus without filtering

## Output

The runner reports:

- total fixtures
- passed / failed
- per-fixture results
- summary hash for reproducible release checks

Exit codes:

- `0` all selected fixtures passed
- `1` one or more fixtures failed
- `2` input/configuration error

## Fixture Root

By default, `mtp-conformance` reads fixtures from the repository-level
`conformance/fixtures/` tree. Use `--fixtures-root` to point at an
alternate fixture corpus.

## CI Usage

The repository CI runs:

- unit tests for `mtp-conformance`
- `mtp-conformance run --level l1`
- `mtp-conformance run --level l2`
- `mtp-conformance run --level l3`
