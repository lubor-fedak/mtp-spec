# Contributing to MTP

Thank you for your interest in MTP (Methodology Transfer Protocol). This project is an open specification and we welcome contributions from the community.

## How to Contribute

### Reporting Issues

- Use [GitHub Issues](https://github.com/lubor-fedak/mtp-spec/issues) to report bugs, suggest features, or ask questions.
- For spec issues, prefix the title with `[spec]`.
- For tooling issues, prefix with `[mtp-lint]` or `[mtp-run]`.

### Pull Requests

1. Fork the repository and create a feature branch from `main`.
2. Make your changes. Follow the existing code style.
3. Add or update tests for any new functionality.
4. Ensure all tests pass before submitting:
   ```bash
   cd tools/mtp-lint && pip install -e ".[dev]" && pytest tests/ -v
   cd tools/mtp-run && pip install -e ".[dev]" && pytest tests/ -v
   ```
5. Submit a pull request with a clear description of the change.

### What We Welcome

- **Critical review** of execution semantics and drift measurement
- **Real-world extraction attempts** — try MTP on your workflow, report what works and what's missing
- **Platform-specific insights** — how does MTP map to your AI stack?
- **Enterprise perspective** — does the policy envelope cover your compliance needs?
- **Tooling contributions** — new adapters, extraction tools, IDE integrations, CI/CD plugins
- **Test coverage** — additional test cases for edge cases and failure modes

### Specification Changes

Changes to the normative specification (`spec/MTP-SPEC-v0.2.md`) require discussion before implementation. Open an issue first to discuss the proposed change.

Non-normative changes (examples, tooling, documentation) can be submitted directly as pull requests.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/lubor-fedak/mtp-spec.git
cd mtp-spec

# Install mtp-lint with dev dependencies
cd tools/mtp-lint && pip install -e ".[dev]"

# Install mtp-run with dev dependencies
cd ../mtp-run && pip install -e ".[dev]"

# Run all tests
cd tools/mtp-lint && pytest tests/ -v
cd ../mtp-run && pytest tests/ -v
```

## Code Style

- Python 3.10+ with type annotations
- Follow existing patterns in the codebase
- Keep modules focused and small
- Use `click` for CLI commands
- Use `pytest` for tests

## License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 License.
