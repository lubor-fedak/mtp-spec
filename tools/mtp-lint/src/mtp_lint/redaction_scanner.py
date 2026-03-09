"""Redaction scanner for MTP packages.

Scans all string values in an MTP package for potential data leakage:
PII, secrets, client identifiers, and literal data patterns.
"""

from __future__ import annotations

import math
import re
from typing import Any


# --- PII Patterns ---

PII_PATTERNS = {
    "email": re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    ),
    "phone_international": re.compile(
        r"(?<!\w)\+\d{1,4}[\s.-]?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{2,4}(?!\w)"
    ),
    "ip_address": re.compile(
        r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
    ),
    "czech_birth_number": re.compile(
        r"\b\d{6}/?\d{3,4}\b"
    ),
    "national_id_generic": re.compile(
        r"\b[A-Z]{2}\d{6,9}\b"
    ),
    "credit_card": re.compile(
        r"\b(?:\d{4}[\s-]?){3}\d{4}\b"
    ),
    "iban": re.compile(
        r"\b[A-Z]{2}\d{2}[\s]?\d{4}[\s]?\d{4}[\s]?\d{4}[\s]?\d{0,4}\b"
    ),
    "url_with_params": re.compile(
        r"https?://[^\s]+[?&][^\s]*=[^\s]+"
    ),
}

# --- Secret Patterns ---

SECRET_PATTERNS = {
    "api_key_generic": re.compile(
        r"(?i)(?:api[_-]?key|apikey|api_secret)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}['\"]?"
    ),
    "bearer_token": re.compile(
        r"(?i)bearer\s+[A-Za-z0-9_\-\.]{20,}"
    ),
    "password_assignment": re.compile(
        r"(?i)(?:password|passwd|pwd)\s*[:=]\s*['\"]?[^\s'\"]{4,}['\"]?"
    ),
    "connection_string": re.compile(
        r"(?i)(?:server|host|data source)\s*=\s*[^;]+;\s*(?:user|uid)\s*=\s*[^;]+;\s*(?:password|pwd)\s*="
    ),
    "aws_key": re.compile(
        r"(?:AKIA|ASIA)[A-Z0-9]{16}"
    ),
    "github_token": re.compile(
        r"gh[ps]_[A-Za-z0-9_]{36,}"
    ),
    "private_key_header": re.compile(
        r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----"
    ),
    "jwt_token": re.compile(
        r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"
    ),
    "slack_token": re.compile(
        r"xox[bpras]-[A-Za-z0-9-]{10,}"
    ),
}


def _shannon_entropy(text: str) -> float:
    """Calculate Shannon entropy of a string."""
    if not text:
        return 0.0
    freq: dict[str, int] = {}
    for c in text:
        freq[c] = freq.get(c, 0) + 1
    length = len(text)
    return -sum(
        (count / length) * math.log2(count / length)
        for count in freq.values()
    )


def _extract_strings(data: Any, path: str = "$") -> list[tuple[str, str]]:
    """Recursively extract all string values from a nested structure.

    Returns list of (path, value) tuples.
    """
    results = []
    if isinstance(data, str):
        results.append((path, data))
    elif isinstance(data, dict):
        for key, val in data.items():
            results.extend(_extract_strings(val, f"{path}.{key}"))
    elif isinstance(data, list):
        for i, item in enumerate(data):
            results.extend(_extract_strings(item, f"{path}[{i}]"))
    return results


def _skip_path(path: str) -> bool:
    """Skip paths that are purely structural, not content-bearing.

    IMPORTANT: We intentionally do NOT skip package.author, provenance.source_ref,
    or provenance.notes — these are common data leak vectors in enterprise contexts.
    Only truly structural/enum fields are skipped.
    """
    skip_segments = {
        "mtp_version",
        "package.id",
        "package.created",
        "package.updated",
        "package.source_platform",
        "package.version",
        "package.tags",
        "provenance.source_type",
        "provenance.confidence",
        "execution_semantics.on_success",
        "execution_semantics.on_failure",
        "execution_semantics.on_deviation",
        "execution_semantics.timeout",
        "execution_semantics.max_retries",
        "policy.redaction.status",
        "policy.redaction.checker",
        "policy.redaction.checker_version",
        "policy.redaction.report_hash",
        "policy.redaction.evidence_ref",
        "policy.pii_scan.status",
        "policy.pii_scan.method",
        "policy.pii_scan.checker",
        "policy.secrets_scan.status",
        "policy.secrets_scan.checker",
        "policy.client_identifier_scan.status",
        "policy.client_identifier_scan.method",
        "policy.client_identifier_scan.checker",
        "policy.regulated_content.status",
        "policy.regulated_content.checker",
        "policy.data_classification",
        "policy.approval.approver",
        "policy.approval.approved_at",
        "policy.approval.signature",
    }
    for seg in skip_segments:
        if seg in path:
            return True
    return False


def scan_pii(data: dict) -> list[dict]:
    """Scan all string fields for PII patterns."""
    findings = []
    for path, value in _extract_strings(data):
        if _skip_path(path):
            continue
        for name, pattern in PII_PATTERNS.items():
            matches = pattern.findall(value)
            if matches:
                findings.append({
                    "category": "pii",
                    "pattern": name,
                    "path": path,
                    "match_count": len(matches),
                    "sample": matches[0][:40] + "..." if len(matches[0]) > 40 else matches[0],
                    "severity": "high",
                })
    return findings


def scan_secrets(data: dict) -> list[dict]:
    """Scan all string fields for secret/credential patterns."""
    findings = []
    for path, value in _extract_strings(data):
        if _skip_path(path):
            continue
        for name, pattern in SECRET_PATTERNS.items():
            matches = pattern.findall(value)
            if matches:
                findings.append({
                    "category": "secret",
                    "pattern": name,
                    "path": path,
                    "match_count": len(matches),
                    "sample": "[REDACTED]",
                    "severity": "critical",
                })
    return findings


def scan_high_entropy(data: dict, threshold: float = 4.5, min_length: int = 20) -> list[dict]:
    """Scan for high-entropy strings that may be tokens or encoded data."""
    findings = []
    for path, value in _extract_strings(data):
        if _skip_path(path):
            continue
        words = value.split()
        for word in words:
            if len(word) >= min_length:
                entropy = _shannon_entropy(word)
                if entropy >= threshold:
                    findings.append({
                        "category": "entropy",
                        "pattern": "high_entropy_string",
                        "path": path,
                        "entropy": round(entropy, 2),
                        "sample": word[:20] + "...",
                        "severity": "warning",
                    })
    return findings


def scan_client_identifiers(data: dict, dictionary: list[str] | None = None) -> list[dict]:
    """Scan for client-specific identifiers using a provided dictionary.

    If no dictionary is provided, returns an empty list (cannot scan without context).
    """
    if not dictionary:
        return []

    findings = []
    patterns = {
        term: re.compile(re.escape(term), re.IGNORECASE)
        for term in dictionary
        if len(term) >= 3  # skip very short terms to avoid false positives
    }

    for path, value in _extract_strings(data):
        if _skip_path(path):
            continue
        for term, pattern in patterns.items():
            matches = pattern.findall(value)
            if matches:
                findings.append({
                    "category": "client_identifier",
                    "pattern": f"dictionary_match:{term}",
                    "path": path,
                    "match_count": len(matches),
                    "sample": term,
                    "severity": "high",
                })

    return findings


def scan_regulated_content(data: dict) -> list[dict]:
    """Scan for regulated content indicators.

    This is a keyword-based heuristic scan, not a legal compliance tool.
    It flags strings that reference specific regulated data categories
    (health records, financial accounts, biometric data, etc.) in
    methodology content where such references may indicate data leakage.

    Limitation: This scanner detects references to regulated data categories,
    not the regulated data itself. A methodology that says "handle health
    records carefully" is different from one that contains actual health
    records. Findings should be reviewed by a human.
    """
    REGULATED_INDICATORS = {
        "health_data": re.compile(
            r"(?i)\b(?:patient\s+(?:id|name|record|data|diagnosis)|"
            r"medical\s+record|health\s+insurance|"
            r"ICD[\s-]?\d{1,2}|diagnosis\s+code|"
            r"prescription|blood\s+type|HIV|"
            r"mental\s+health\s+(?:record|status|history))\b"
        ),
        "financial_account": re.compile(
            r"(?i)\b(?:account\s+number\s*[:=]\s*\d|"
            r"routing\s+number|swift\s+code\s*[:=]|"
            r"sort\s+code\s*[:=]|"
            r"tax\s+(?:id|identification)\s+number)\b"
        ),
        "biometric": re.compile(
            r"(?i)\b(?:fingerprint|retina\s+scan|facial\s+recognition\s+(?:data|template)|"
            r"biometric\s+(?:data|template|hash)|voice\s+print)\b"
        ),
        "minor_data": re.compile(
            r"(?i)\b(?:child(?:'s|s)?\s+(?:name|age|school|record)|"
            r"minor\s+(?:data|record|information)|"
            r"parental\s+consent|student\s+record)\b"
        ),
    }

    findings = []
    for path, value in _extract_strings(data):
        if _skip_path(path):
            continue
        for name, pattern in REGULATED_INDICATORS.items():
            matches = pattern.findall(value)
            if matches:
                findings.append({
                    "category": "regulated_content",
                    "pattern": name,
                    "path": path,
                    "match_count": len(matches),
                    "sample": matches[0][:40],
                    "severity": "warning",
                    "note": "Keyword indicator — review whether this is a reference to data categories or actual data leakage.",
                })
    return findings


def scan_literal_data(data: dict) -> list[dict]:
    """Scan for patterns that suggest literal data values leaked into the methodology.

    Detects: CSV-like rows, JSON fragments with realistic values,
    SQL-like data literals, and suspiciously specific numeric values
    that look like real records rather than methodology thresholds.
    """
    LITERAL_PATTERNS = {
        "csv_row": re.compile(
            r'(?:^|\n)\s*(?:"[^"]*"|[^,\n"]{1,30})\s*(?:,\s*(?:"[^"]*"|\d[\d.]*)\s*){3,}'
        ),
        "json_fragment": re.compile(
            r'\{"[a-z_]+"\s*:\s*"[^"]{5,}"(?:\s*,\s*"[a-z_]+"\s*:\s*"[^"]{5,}"){2,}\}'
        ),
        "sql_values": re.compile(
            r"(?i)VALUES\s*\([^)]+\)"
        ),
    }

    findings = []
    for path, value in _extract_strings(data):
        if _skip_path(path):
            continue
        for name, pattern in LITERAL_PATTERNS.items():
            matches = pattern.findall(value)
            if matches:
                findings.append({
                    "category": "literal_data",
                    "pattern": name,
                    "path": path,
                    "match_count": len(matches),
                    "sample": matches[0][:40] + "..." if len(matches[0]) > 40 else matches[0],
                    "severity": "warning",
                })
    return findings


def scan_all(data: dict, client_dictionary: list[str] | None = None) -> dict:
    """Run all redaction scans and return consolidated results."""
    pii = scan_pii(data)
    secrets = scan_secrets(data)
    entropy = scan_high_entropy(data)
    client_ids = scan_client_identifiers(data, client_dictionary)
    regulated = scan_regulated_content(data)
    literal = scan_literal_data(data)

    all_findings = pii + secrets + entropy + client_ids + regulated + literal

    return {
        "total_findings": len(all_findings),
        "by_category": {
            "pii": len(pii),
            "secret": len(secrets),
            "entropy": len(entropy),
            "client_identifier": len(client_ids),
            "regulated_content": len(regulated),
            "literal_data": len(literal),
        },
        "passed": len(all_findings) == 0,
        "findings": all_findings,
    }
