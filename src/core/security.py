"""Security, Privacy, and In-Flight PII Redaction Controls.

Compliance Note:
    Under DPDP Act 2023 and SchemeSaathi's Zero-Aadhaar policy, the platform NEVER stores,
    indexes, or persists 12-digit Aadhaar identifiers. The Verhoeff algorithm implemented
    below validates the dihedral-group (D5) mathematical checksum used in the 12th check digit.

    IMPORTANT SECURITY DISTINCTION:
    Passing Verhoeff validation DOES NOT prove Aadhaar authenticity or government issuance
    (which requires statutory UIDAI biometric/OTP authentication protocols). Rather, Verhoeff
    acts as a defensive heuristic filter to identify prospective Aadhaar sequences in-flight
    and aggressively redact them from logs, exceptions, telemetry, and persistence.
"""

import re
from typing import Any

# Multiplication table for Verhoeff algorithm
_VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]

# Permutation table for Verhoeff algorithm
_VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]

# Regex to match 12-digit number sequences (with optional spaces or dashes)
AADHAAR_PATTERN = re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b")


def validate_verhoeff(num_str: str) -> bool:
    """Validate 12-digit number using Verhoeff algorithm (Aadhaar checksum)."""
    clean_num = re.sub(r"\D", "", num_str)
    if len(clean_num) != 12:
        return False

    c = 0
    reversed_digits = [int(d) for d in reversed(clean_num)]
    for i, digit in enumerate(reversed_digits):
        c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][digit]]

    return c == 0


def redact_aadhaar_pii(text: str) -> str:
    """Detect and unconditionally redact any prospective 12-digit number sequence.

    Under SchemeSaathi's Zero-Aadhaar policy and DPDP Act 2023 alignment, redaction is
    unconditional: any 12-digit sequence (with or without spaces/hyphens) is aggressively
    redacted to [REDACTED_AADHAAR] regardless of whether it satisfies the Verhoeff check digit.
    This guarantees that malformed numbers or typographical errors cannot leak into logs,
    telemetry, exceptions, or error responses.
    """
    if not text:
        return text

    return AADHAAR_PATTERN.sub("[REDACTED_AADHAAR]", text)


# Public alias for text redaction
redact_pii_text = redact_aadhaar_pii


def sanitize_sensitive_data(val: Any) -> Any:
    """Recursively scrub prospective Aadhaar sequences from strings, dicts, lists, and tuples."""
    if isinstance(val, Exception):
        return redact_aadhaar_pii(str(val))
    if isinstance(val, str):
        return redact_aadhaar_pii(val)
    if isinstance(val, dict):
        return {k: sanitize_sensitive_data(v) for k, v in val.items()}
    if isinstance(val, list):
        return [sanitize_sensitive_data(item) for item in val]
    if isinstance(val, tuple):
        return tuple(sanitize_sensitive_data(item) for item in val)
    return val
