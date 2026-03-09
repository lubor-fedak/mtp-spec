# mtp-extract

Conversation-to-package draft extraction for MTP.

`mtp-extract` closes the current gap in the MTP lifecycle before `1.0`: it
turns raw conversations into schema-valid draft `v0.2` packages with
provenance, default execution semantics, and a policy precheck.

## Install

```bash
pip install -e tools/mtp-lint
pip install -e tools/mtp-extract
```

For development:

```bash
pip install -e "tools/mtp-extract[dev]"
```

## Commands

| Command | What it does |
|---------|--------------|
| `mtp-extract draft <conversation>` | Generate a schema-valid draft MTP package from a conversation transcript or export |
| `mtp-extract precheck <package>` | Populate the package policy envelope using the redaction scanner |
| `mtp-extract map <package>` | Emit a provenance map for steps, edge cases, and dead ends |
| `mtp-extract merge <base> <overlay>` | Merge two MTP packages into one updated draft |

## Examples

```bash
mtp-extract draft examples/conversations/churn-risk-scoring-session.md \
  --name "Customer Churn Risk Scoring" \
  --author analytics-team \
  --source-platform claude-sonnet-4 \
  --precheck \
  -o /tmp/churn-draft.yaml

mtp-extract map /tmp/churn-draft.yaml --format json

mtp-extract precheck /tmp/churn-draft.yaml --client-identifier "Acme Corp"
```

## Supported input formats

- plaintext / markdown transcripts with `User:` / `Assistant:` style turns
- JSON/YAML lists of message objects with `role` + `content`
- nested exports with `messages`, `conversation`, or `chat_messages`

The extractor is intentionally heuristic. It is designed to produce a
reviewable draft package, not to replace human review.
