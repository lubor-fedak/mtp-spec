"""Tests for policy gate."""

from mtp_lint.policy_gate import check_policy


class TestCheckPolicy:
    def test_no_policy_fails(self):
        data = {"mtp_version": "0.2"}
        result = check_policy(data)
        assert result["gate_passed"] is False

    def test_complete_policy_passes(self):
        data = {
            "mtp_version": "0.2",
            "policy": {
                "data_classification": "internal",
                "redaction": {"status": "pass", "scanner": "mtp-lint"},
                "pii_scan": {"status": "pass", "scanner": "mtp-lint"},
                "secrets_scan": {"status": "pass", "scanner": "mtp-lint"},
                "client_identifier_scan": {"status": "pass", "scanner": "mtp-lint"},
                "regulated_content": {"status": "pass", "scanner": "mtp-lint"},
            },
        }
        result = check_policy(data)
        assert result["gate_passed"] is True

    def test_missing_scan_fails_gate(self):
        data = {
            "mtp_version": "0.2",
            "policy": {
                "data_classification": "internal",
                "redaction": {"status": "pass", "scanner": "mtp-lint"},
                # pii_scan missing
                "secrets_scan": {"status": "pass", "scanner": "mtp-lint"},
                "client_identifier_scan": {"status": "pass", "scanner": "mtp-lint"},
                "regulated_content": {"status": "pass", "scanner": "mtp-lint"},
            },
        }
        result = check_policy(data)
        assert result["gate_passed"] is False

    def test_missing_classification_fails(self):
        data = {
            "mtp_version": "0.2",
            "policy": {
                "redaction": {"status": "pass", "scanner": "mtp-lint"},
                "pii_scan": {"status": "pass", "scanner": "mtp-lint"},
                "secrets_scan": {"status": "pass", "scanner": "mtp-lint"},
                "client_identifier_scan": {"status": "pass", "scanner": "mtp-lint"},
                "regulated_content": {"status": "pass", "scanner": "mtp-lint"},
            },
        }
        result = check_policy(data)
        assert result["gate_passed"] is False

    def test_approval_required_but_missing(self):
        data = {
            "mtp_version": "0.2",
            "policy": {
                "data_classification": "internal",
                "redaction": {"status": "pass", "scanner": "mtp-lint"},
                "pii_scan": {"status": "pass", "scanner": "mtp-lint"},
                "secrets_scan": {"status": "pass", "scanner": "mtp-lint"},
                "client_identifier_scan": {"status": "pass", "scanner": "mtp-lint"},
                "regulated_content": {"status": "pass", "scanner": "mtp-lint"},
                "approval": {"required": True},
            },
        }
        result = check_policy(data)
        assert result["gate_passed"] is False
