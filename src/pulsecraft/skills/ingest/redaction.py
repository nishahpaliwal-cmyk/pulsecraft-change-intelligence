"""Redaction helper — regex-based scrub of sensitive data markers.

This module provides belt-and-suspenders redaction for ingest adapters.
It applies a fixed set of patterns to catch common PII, PHI, and credential
patterns in source text before it is stored in a ChangeArtifact.

NOTE: This is intentionally lightweight. Comprehensive, context-aware redaction
is implemented in prompt 12 (guardrail hooks). This module exists so that even
without the guardrail layer, the most obvious patterns are scrubbed at ingest time.
"""

from __future__ import annotations

import re

# Compiled patterns: (pattern, replacement)
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # SSN: "SSN: 123-45-6789" or "SSN:123456789"
    (re.compile(r"SSN:\s*\d{3}-?\d{2}-?\d{4}", re.IGNORECASE), "[REDACTED]"),
    # DOB: "DOB: 1/15/2000" or "DOB:01/15/00"
    (re.compile(r"DOB:\s*\d{1,2}/\d{1,2}/\d{2,4}", re.IGNORECASE), "[REDACTED]"),
    # MRN: "MRN: 1234567"
    (re.compile(r"MRN:\s*\d+", re.IGNORECASE), "[REDACTED]"),
    # Password: "password=secret" or "password = hunter2"
    (re.compile(r"password\s*=\s*\S+", re.IGNORECASE), "[REDACTED]"),
    # API key: "API_KEY: abc123" or "APIKEY=abc" or "API-KEY: xyz"
    (re.compile(r"API[_-]?KEY\s*[:=]\s*\S+", re.IGNORECASE), "[REDACTED]"),
    # Email addresses
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+", re.IGNORECASE), "[REDACTED]"),
    # US phone numbers: 555-555-5555 / 555.555.5555 / 555 555 5555
    (re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[REDACTED]"),
]


def redact(text: str) -> str:
    """Scrub known sensitive data patterns from *text* and return the result.

    Each pattern is applied in order; earlier substitutions may affect later
    pattern matching (e.g., a redacted phone number won't re-match).  The
    function always returns a ``str``; an empty input returns an empty string.
    """
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text
